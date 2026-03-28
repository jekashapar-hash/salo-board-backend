from django.utils import timezone
from .models import Round, Submission, Team

def check_and_update_round_deadlines(round_obj):
    """
    Checks if the round deadline has passed.
    If so, non-empty DRAFT submissions are set to SUBMITTED.
    Empty submissions or no submissions cause the team to be DISQUALIFIED.
    Returns True if deadline has passed.
    """
    if timezone.now() > round_obj.deadline:
        # Update DRAFT submissions to SUBMITTED if they have content
        draft_submissions = Submission.objects.filter(round=round_obj, status=Submission.Status.DRAFT)
        for sub in draft_submissions:
            # Check if not empty
            if sub.github_url or sub.video_url or sub.demo_url or sub.description:
                sub.status = Submission.Status.SUBMITTED
                sub.submitted_at = timezone.now()
                sub.save()
            else:
                sub.team.status = Team.Status.DISQUALIFIED
                sub.team.save()
                
        # Teams that have NO submission at all get disqualified
        teams_with_submissions = Submission.objects.filter(round=round_obj).values_list('team_id', flat=True)
        teams_without_subs = Team.objects.filter(
            tournament=round_obj.tournament
        ).exclude(id__in=teams_with_submissions)
        
        for team in teams_without_subs:
            team.status = Team.Status.DISQUALIFIED
            team.save()

        # Update round status
        if round_obj.status == Round.Status.ACTIVE:
            round_obj.status = Round.Status.SUBMISSION_CLOSED
            round_obj.save()
            
        return True
    return False

def check_tournament_deadlines(tournament):
    """
    Check all active rounds for a tournament and update their statuses.
    """
    active_rounds = Round.objects.filter(
        tournament=tournament, 
        status=Round.Status.ACTIVE
    )
    for r in active_rounds:
        check_and_update_round_deadlines(r)

