from typing import Protocol

from salocore.models import UserProfile
from salocore.repositories.notification.dto import MessageDTO


class NotificationRepositoryProtocol(Protocol):
    def send(self, message: MessageDTO, to: UserProfile) -> None: ...
