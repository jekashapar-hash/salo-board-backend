from salocore.models import Evaluation


class EvaluationRepositoryImpl:
    def create_evaluations(self, submission_jury_pairs: list[tuple[int, int]]) -> None:
        evaluations = [
            Evaluation(submission_id=sub_id, jury_id=user_id, comment="") for sub_id, user_id in submission_jury_pairs
        ]
        Evaluation.objects.bulk_create(evaluations)

    def all_submitted_for_round(self, round_id: int) -> bool:
        evaluations = Evaluation.objects.filter(submission__round_id=round_id)
        return evaluations.exists() and not evaluations.exclude(status=Evaluation.Status.SUBMITTED).exists()
