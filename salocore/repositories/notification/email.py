from salocore.models import UserProfile
from salocore.repositories.notification.dto import MessageDTO


class EmailNotificationRepositoryImpl:
    def send(self, message: MessageDTO, to: UserProfile) -> None:
        pass  # Логика Почты
