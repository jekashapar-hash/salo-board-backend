from typing import Protocol

from salocore.models import Submission


class SubmissionRepositoryProtocol(Protocol):
    def get_submissions(self, tournament_id: int) -> list[Submission]: ...

    def get_submissions_by_round(self, round_id: int) -> list[Submission]: ...

    def change_submission_status(self, submission_id: int, status: Submission.Status) -> None: ...
