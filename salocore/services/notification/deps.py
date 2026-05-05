from salocore.repositories.notification.deps import get_notification_factory
from salocore.repositories.user.deps import get_user_repository
from salocore.services.notification.impl import NotificationServiceImpl
from salocore.services.notification.protocol import NotificationServiceProtocol


def get_notification_service() -> NotificationServiceProtocol:
    return NotificationServiceImpl(get_notification_factory(), get_user_repository())
