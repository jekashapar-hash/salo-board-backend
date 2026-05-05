from datetime import timedelta

from django.utils import timezone

from salocore.models import Notification, UserProfile
from salocore.repositories.notification.dto import MessageDTO


class DbNotificationRepositoryImpl:
    def send(self, message: MessageDTO, to: UserProfile) -> None:
        how_long_active = timezone.now() + timedelta(days=message.how_long_active_days)
        Notification.objects.create(
            user=to.user,
            title=message.title,
            message=message.text,
            type=message.type,
            action_type=message.action_type,
            action_url=message.action_url,
            how_long_active=how_long_active,
        )
