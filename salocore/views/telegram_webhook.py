import contextlib
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from salocore.models import User, UserTelegramProfile


@csrf_exempt
def telegram_webhook(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    with contextlib.suppress(Exception):
        data = json.loads(request.body)
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if chat_id and text.startswith("/start "):
            user_pk = text.split(" ", 1)[1].strip()
            user = User.objects.filter(pk=user_pk).first()
            if user:
                UserTelegramProfile.objects.update_or_create(
                    user=user,
                    defaults={"chat_id": chat_id},
                )

    return JsonResponse({"ok": True})
