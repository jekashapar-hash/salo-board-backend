from typing import Protocol


class EvaluationRepositoryProtocol(Protocol):
    def create_evaluations(self, submission_jury_pairs: list[tuple[int, int]]) -> None: ...

    def all_submitted_for_round(self, round_id: int) -> bool: ...
