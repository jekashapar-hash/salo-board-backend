from salocore.repositories.notification.factory import NotificationFactoryImpl, NotificationFactoryProtocol


def get_notification_factory() -> NotificationFactoryProtocol:
    return NotificationFactoryImpl()
