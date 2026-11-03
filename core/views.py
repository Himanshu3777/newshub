from django.shortcuts import render, redirect
from django import forms
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from news.models import NewsArticle
from news.views import home as news_home
from sources.models import NewsSource, FetchingLog
from verification.models import VerificationReport
from moderation.models import SensitiveContentFinding
from feedback_app.forms import FeedbackForm, CorrectionForm
from verification.models import ClaimSubmission

def home(request): return news_home(request)
def about(request): return render(request,"core/about.html")
def methodology(request): return render(request,"core/methodology.html")
def sources_page(request): return render(request,"core/sources.html",{"sources":NewsSource.objects.annotate(count=Count("articles"))})
def factcheck_page(request):
    from news.models import NewsArticle as NA
    reports=VerificationReport.objects.select_related("article").prefetch_related("evidence")[:30]
    flagged=NA.objects.filter(verification_status__in=["false","misleading","disputed"]).select_related("source")[:20]
    unconfirmed=NA.objects.filter(is_unconfirmed=True).select_related("source")[:20]
    return render(request,"core/factcheck.html",{"reports":reports,"flagged":flagged,"unconfirmed":unconfirmed})
def analysis_page(request):
    by_cat=NewsArticle.objects.values("category__name").annotate(c=Count("id")).order_by("-c")
    by_status=NewsArticle.objects.values("verification_status").annotate(c=Count("id")).order_by("-c")
    by_source=NewsArticle.objects.values("source__name").annotate(c=Count("id")).order_by("-c")
    return render(request,"core/analysis.html",{"by_cat":by_cat,"by_status":by_status,"by_source":by_source})
def dashboard(request):
    ctx={
      "total":NewsArticle.objects.count(),
      "verified":NewsArticle.objects.filter(verification_status="verified").count(),
      "disputed":NewsArticle.objects.filter(verification_status__in=["disputed","misleading","false"]).count(),
      "unverified":NewsArticle.objects.filter(verification_status="unverified").count(),
      "pending":NewsArticle.objects.filter(verification_status="needs_review").count(),
      "sensitive_pending":SensitiveContentFinding.objects.filter(needs_human_review=True,reviewed=False).count(),
      "by_source":NewsArticle.objects.values("source__name").annotate(c=Count("id")).order_by("-c"),
      "history":VerificationReport.objects.select_related("article")[:15],
      "fetch_logs":FetchingLog.objects.select_related("source")[:10],
    }
    return render(request,"core/dashboard.html",ctx)
def contact(request):
    if request.method=="POST":
        form=CorrectionForm(request.POST) if "description" in request.POST else FeedbackForm(request.POST)
        if form.is_valid(): form.save(); messages.success(request,f"Thanks! Your request is saved. Reference ID: NV-{form.instance.id}. An editor will review it and the correction will be logged."); return redirect("contact")
    return render(request,"core/contact.html",{"feedback_form":FeedbackForm(),"correction_form":CorrectionForm()})

def check_claim_page(request):
    result=None
    if request.method=="POST":
        text=request.POST.get("claim_text","").strip()
        if len(text)>=10:
            from verification.claimcheck import check_claim
            result=check_claim(text, request.POST.get("platform","other"), request.POST.get("source_url","").strip())
        else:
            messages.error(request,"Please paste the full claim / post text (at least a sentence).")
    recent=ClaimSubmission.objects.all()[:8]
    return render(request,"core/check_claim.html",{"result":result,"recent":recent})

class RegisterForm(UserCreationForm):
    """Public reader registration (a normal account - never staff/admin)."""
    email = forms.EmailField(required=False, help_text="Optional, sirf account recovery ke liye.")
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        messages.success(request, f"Welcome to NewsHub, {user.username}! Tumhara account ban gaya hai aur tum login ho.")
        return redirect("home")
    return render(request, "core/register.html", {"form": form})
