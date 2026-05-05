from salocore.repositories.evaluation.impl import EvaluationRepositoryImpl
from salocore.repositories.evaluation.protocol import EvaluationRepositoryProtocol


def get_evaluation_repository() -> EvaluationRepositoryProtocol:
    return EvaluationRepositoryImpl()
