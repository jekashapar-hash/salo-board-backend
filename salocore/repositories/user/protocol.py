from typing import Protocol

from salocore.models import UserProfile


class UserRepositoryProtocol(Protocol):
    def get_profile(self, user_id: int) -> UserProfile: ...

    def get_tournament_participants(self, tournament_id: int) -> list[UserProfile]: ...

    def get_juries_ids(self, tournament_id: int) -> list[int]: ...
