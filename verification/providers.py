"""Pluggable search providers for the verification engine.

Verification gathers evidence through interchangeable SearchProvider
implementations (see settings.SEARCH_PROVIDERS). The Google Fact Check Tools
API is the default provider: it finds *existing* fact-checks - evidence, not
proof. Google CSE is a legacy/optional provider only: it is closed to new
customers and is discontinued on 2027-01-01, so it must never become a hard
dependency. It runs only when explicitly enabled (SEARCH_GOOGLE_CSE_ENABLED)
with both keys configured.

Every provider returns (list[EvidenceItem], status_str) where status_str uses
the same vocabulary as verification.services.google_factcheck:
"ok", "disabled", "no_api_key", "api_<code>", "error:<Type>".
"""
from dataclasses import dataclass

import requests
from django.conf import settings

from verification import services


@dataclass
class EvidenceItem:
    title: str = ""
    url: str = ""
    publisher: str = ""
    snippet: str = ""
    rating: str = ""
    # Matches VerificationEvidence.KIND: factcheck | neutral | supporting | contradicting
    kind: str = "neutral"


class SearchProvider:
    """Base class. Subclasses set `name` and implement search()."""
    name = "base"
    legacy = False

    def is_enabled(self):
        return True

    def search(self, query):
        raise NotImplementedError


class FactCheckProvider(SearchProvider):
    """Default provider: Google Fact Check Tools API via services.google_factcheck.

    Finds already-published fact-checks. It is an evidence finder, never a
    truth engine - final status is decided by the multi-signal scoring rule
    in verification.services.score_verification.
    """
    name = "factcheck"

    def search(self, query):
        results, status = services.google_factcheck(query)
        items = [
            EvidenceItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                publisher=r.get("publisher", ""),
                snippet=r.get("snippet", ""),
                rating=r.get("rating", ""),
                kind="factcheck",
            )
            for r in results
        ]
        return items, status


class GoogleCSEProvider(SearchProvider):
    """LEGACY / optional: Google Programmable Search (Custom Search JSON API).

    Discontinued for new customers; service ends 2027-01-01. Enabled only when
    settings.SEARCH_GOOGLE_CSE_ENABLED is True AND both GOOGLE_CSE_API_KEY and
    GOOGLE_CSE_ID are set. Its results are neutral web evidence - they carry no
    rating and never verify a claim on their own.
    """
    name = "google_cse"
    legacy = True

    def is_enabled(self):
        return bool(
            getattr(settings, "SEARCH_GOOGLE_CSE_ENABLED", False)
            and getattr(settings, "GOOGLE_CSE_API_KEY", "")
            and getattr(settings, "GOOGLE_CSE_ID", "")
        )

    def search(self, query):
        if not getattr(settings, "SEARCH_GOOGLE_CSE_ENABLED", False):
            return [], "disabled"
        key = getattr(settings, "GOOGLE_CSE_API_KEY", "")
        cx = getattr(settings, "GOOGLE_CSE_ID", "")
        if not key or not cx:
            return [], "no_api_key"
        try:
            r = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": key, "cx": cx, "q": query, "num": 5},
                timeout=10,
            )
            if r.status_code != 200:
                return [], f"api_{r.status_code}"
            items = [
                EvidenceItem(
                    title=i.get("title", ""),
                    url=i.get("link", ""),
                    publisher=i.get("displayLink", ""),
                    snippet=i.get("snippet", ""),
                    rating="",
                    kind="neutral",
                )
                for i in r.json().get("items", [])
            ]
            return items, "ok"
        except Exception as e:
            return [], f"error:{type(e).__name__}"


_REGISTRY = {
    FactCheckProvider.name: FactCheckProvider,
    GoogleCSEProvider.name: GoogleCSEProvider,
}


def get_search_providers():
    """Enabled provider instances, in settings.SEARCH_PROVIDERS order.

    Unknown names are ignored; disabled providers (e.g. legacy CSE without
    its flag/keys) are filtered out. Default is ["factcheck"].
    """
    names = getattr(settings, "SEARCH_PROVIDERS", ["factcheck"])
    providers, seen = [], set()
    for name in names:
        cls = _REGISTRY.get((name or "").strip())
        if cls is None or cls.name in seen:
            continue
        seen.add(cls.name)
        provider = cls()
        if provider.is_enabled():
            providers.append(provider)
    return providers
