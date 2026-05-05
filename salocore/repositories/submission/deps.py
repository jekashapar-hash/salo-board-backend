from .impl import SubmissionRepositoryImpl
from .protocol import SubmissionRepositoryProtocol


def get_submission_repository() -> SubmissionRepositoryProtocol:
    return SubmissionRepositoryImpl()
