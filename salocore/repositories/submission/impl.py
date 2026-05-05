from salocore.models import Submission


class SubmissionRepositoryImpl:
    def get_submissions(self, tournament_id: int) -> list[Submission]:
        # Using team__tournament_id as Submission doesn't have tournament_id directly
        return list(Submission.objects.filter(team__tournament_id=tournament_id))

    def get_submissions_by_round(self, round_id: int) -> list[Submission]:
        return list(Submission.objects.filter(round_id=round_id))

    def change_submission_status(self, submission_id: int, status: str) -> None:
        submission = Submission.objects.get(id=submission_id)
        submission.status = status
        submission.save()
