from salocore.models import UserProfile
from salocore.repositories.notification.db import DbNotificationRepositoryImpl
from salocore.repositories.notification.discord import DiscordNotificationRepositoryImpl
from salocore.repositories.notification.protocol import NotificationRepositoryProtocol
from salocore.repositories.notification.telegram import TelegramNotificationRepositoryImpl


class NotificationFactoryProtocol:
    def smart_make(self, user_profile: UserProfile) -> list[NotificationRepositoryProtocol]: ...


class NotificationFactoryImpl:
    def smart_make(self, user_profile: UserProfile) -> list[NotificationRepositoryProtocol]:
        # DB notification is always created for every user
        notifications: list[NotificationRepositoryProtocol] = [DbNotificationRepositoryImpl()]
        if hasattr(user_profile.user, "telegram_profile"):
            notifications.append(TelegramNotificationRepositoryImpl())
        if user_profile.discord:
            notifications.append(DiscordNotificationRepositoryImpl())
        return notifications
