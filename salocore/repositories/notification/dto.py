from dataclasses import dataclass

from salocore.models import Notification


@dataclass(frozen=True)
class MessageDTO:
    text: str
    title: str
    type: Notification.Type
    action_type: Notification.ActionType
    targetid: int
    target: str
    action_url: str = ""
    how_long_active_days: int = 30
