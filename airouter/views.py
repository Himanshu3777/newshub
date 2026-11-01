import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from airouter import router
from airouter.models import AIGenerationLog

@staff_member_required
def dashboard(request):
    return render(request, "airouter/dashboard.html", {
        "rows": router.provider_snapshot(),
        "totals": router.today_totals(),
        "logs": AIGenerationLog.objects.all()[:25],
    })

@staff_member_required
@require_POST
def api_text(request):
    """POST {prompt, class} -> spec-10 JSON. Staff only; keys never leave the server."""
    try:
        body = json.loads(request.body or b"{}")
    except Exception:
        body = {}
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return JsonResponse({"success": False, "error": "prompt is required"}, status=400)
    result = router.generate_text(prompt, request_class=body.get("class", "normal"))
    return JsonResponse(result)
