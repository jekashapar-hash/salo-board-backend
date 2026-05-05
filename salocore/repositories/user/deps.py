from .impl import UserRepositoryImpl
from .protocol import UserRepositoryProtocol


def get_user_repository() -> UserRepositoryProtocol:
    return UserRepositoryImpl()
