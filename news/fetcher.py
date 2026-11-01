"""Phase 6: RSS fetching engine - legally permitted feeds only, metadata only."""
import logging, socket, feedparser
socket.setdefaulttimeout(15)
from datetime import datetime
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import time
from sources.models import NewsSource, FetchingLog
from news.models import NewsArticle, NewsCategory, NewsTag, NewsEntity
from news.services import normalize_text, normalize_title, detect_language, extract_keywords, extract_entities, classify_category, fingerprint, is_duplicate_candidate, detect_social_origin
from moderation.services import detect_sensitive
from moderation.models import SensitiveContentFinding

log=logging.getLogger(__name__)

def _parse_date(entry):
    for attr in ("published_parsed","updated_parsed"):
        v=getattr(entry,attr,None)
        if v:
            try: return timezone.make_aware(datetime.fromtimestamp(time.mktime(v)))
            except Exception: pass
    for attr in ("published","updated"):
        v=getattr(entry,attr,None)
        if v:
            dt=parse_datetime(v)
            if dt: return dt if timezone.is_aware(dt) else timezone.make_aware(dt)
    return timezone.now()

def _image(entry):
    for m in getattr(entry,"media_content",[]) or []:
        if m.get("url"): return m["url"][:1000]
    for l in getattr(entry,"links",[]) or []:
        if l.get("type","").startswith("image") and l.get("href"): return l["href"][:1000]
    return ""

def fetch_source(source: NewsSource):
    flog=FetchingLog.objects.create(source=source,status="running")
    fetched=created=dup=0; errors=[]; new_articles=[]
    try:
        parsed=feedparser.parse(source.feed_url)
        if getattr(parsed,"bozo",False) and not parsed.entries:
            raise ValueError(f"Feed parse failed: {getattr(parsed,'bozo_exception','unknown')}")
        recent_titles=list(NewsArticle.objects.filter(source=source).order_by("-published_at").values_list("title",flat=True)[:100])
        for entry in parsed.entries[:30]:
            fetched+=1
            url=getattr(entry,"link","") or ""
            title=normalize_text(getattr(entry,"title",""))
            if not url.startswith("http") or not title: continue
            if NewsArticle.objects.filter(source_url=url).exists(): dup+=1; continue
            is_dup,match=is_duplicate_candidate(title,recent_titles)
            if is_dup: dup+=1; log.info("Duplicate candidate skipped: %s ~ %s",title,match); continue
            summary=normalize_text(getattr(entry,"summary","") or getattr(entry,"description",""))[:1200]
            cat_name=classify_category(title,summary)
            category,_=NewsCategory.objects.get_or_create(name=cat_name,defaults={"slug":cat_name.lower().replace(" ","-")})
            article=NewsArticle.objects.create(
                title=title,summary=summary,source=source,source_url=url,
                author=normalize_text(getattr(entry,"author",""))[:200],
                category=category,image_url=_image(entry),language=detect_language(title+" "+summary),
                published_at=_parse_date(entry),normalized_title=normalize_title(title),
                fingerprint=fingerprint(title,url),is_breaking=(cat_name=="Breaking News"))
            for kw in extract_keywords(title+" "+summary,6):
                tag,_=NewsTag.objects.get_or_create(name=kw,defaults={"slug":kw.lower().replace(" ","-")})
                article.tags.add(tag)
            for name,typ in extract_entities(title+" "+summary):
                NewsEntity.objects.get_or_create(article=article,name=name,entity_type=typ)
            desc,note=detect_social_origin(title,summary)
            if desc:
                article.origin_type="social_claim"; article.is_unconfirmed=True; article.source_note=note
                article.save(update_fields=["origin_type","is_unconfirmed","source_note"])
            findings=detect_sensitive(title+" "+summary)
            for f in findings:
                SensitiveContentFinding.objects.create(article=article,finding_type=f["type"],matched_text_masked=f["masked"],severity=f["severity"],needs_human_review=f["needs_review"])
            if findings:
                article.has_sensitive_content=True; article.save(update_fields=["has_sensitive_content"])
            from news.ai_content import generate_brief
            brief,_prov=generate_brief(article); article.ai_brief=brief; article.save(update_fields=["ai_brief"])
            recent_titles.append(title); created+=1
            new_articles.append(article)
        # Auto-verify a bounded batch of new stories (Google Fact Check when a
        # key is configured, otherwise the cross-source evidence engine).
        from django.conf import settings as djsettings
        limit=getattr(djsettings,"AUTO_VERIFY_PER_SOURCE",8)
        for art in new_articles[:limit]:
            try:
                from verification.engine import verify_article
                verify_article(art)
            except Exception as ve:
                log.warning("Auto-verify failed for %s: %s", art.id, ve)
        # AI cover photos for a bounded batch of new stories (Pollinations/FLUX,
        # free, no key). Failure is non-fatal: the SVG illustration is the fallback.
        from django.conf import settings as _s2
        cover_limit=getattr(_s2,"AUTO_COVERS_PER_SOURCE",3)
        for art in new_articles[:cover_limit]:
            try:
                from news.ai_image import fetch_ai_cover
                data=fetch_ai_cover(art)
                if data: art.cover_jpeg=data; art.save(update_fields=["cover_jpeg"])
            except Exception as ce:
                log.warning("AI cover generation failed for %s: %s", art.id, ce)
        source.last_status="success"
    except Exception as e:
        errors.append(str(e)[:500]); source.last_status=f"failed: {str(e)[:40]}"; log.warning("Fetch failed %s: %s",source.name,e)
    # last_status column is varchar(50) - PostgreSQL enforces it, SQLite did not.
    source.last_status=(source.last_status or "")[:50]
    source.last_fetched_at=timezone.now(); source.save(update_fields=["last_fetched_at","last_status"])
    flog.finished_at=timezone.now(); flog.fetched=fetched; flog.created=created; flog.duplicates=dup
    flog.errors="\n".join(errors); flog.status="failed" if errors and created==0 else ("partial" if errors else "success")
    flog.save()
    return {"source":source.name,"fetched":fetched,"created":created,"duplicates":dup,"status":flog.status,"errors":errors}

def fetch_all_sources():
    return [fetch_source(s) for s in NewsSource.objects.filter(is_active=True)]
