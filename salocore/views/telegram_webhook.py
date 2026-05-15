import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from salocore.models import User, UserTelegramProfile

logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_webhook(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    try:
        data = json.loads(request.body)
        logger.info("[TG WEBHOOK] payload: %s", data)

        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        logger.info("[TG WEBHOOK] chat_id=%s text=%r", chat_id, text)

        if not chat_id:
            logger.warning("[TG WEBHOOK] no chat_id, skipping")
            return JsonResponse({"ok": True})

        # Deep link: /start <user_pk>
        if text.startswith("/start"):
            parts = text.split(" ", 1)
            if len(parts) < 2:
                logger.warning("[TG WEBHOOK] /start without user_pk, skipping")
                return JsonResponse({"ok": True})

            user_pk = parts[1].strip()
            logger.info("[TG WEBHOOK] user_pk=%r", user_pk)

            user = User.objects.filter(pk=user_pk).first()
            if not user:
                logger.warning("[TG WEBHOOK] user pk=%s not found", user_pk)
                return JsonResponse({"ok": True})

            profile, created = UserTelegramProfile.objects.update_or_create(
                user=user,
                defaults={"chat_id": chat_id},
            )
            logger.info("[TG WEBHOOK] profile %s, created=%s", profile, created)

    except Exception:
        logger.exception("[TG WEBHOOK] unhandled error")

    return JsonResponse({"ok": True})

