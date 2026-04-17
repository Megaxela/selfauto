from typing import Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from .user_info import UserInfo

DEFAULT_EXPIRE_TIME = timedelta(days=7)


@dataclass
class SessionInfo:
    expires_at: datetime
    expire_time: timedelta
    user_info: UserInfo
    token: str


class SessionStore:
    def __init__(self):
        self.__sessions: Dict[str, SessionInfo] = {}

    def get_session_by_token(
        self,
        token: str,
        prolongate: bool = False,
    ) -> UserInfo | None:
        session_info = self.__sessions.get(token)
        if session_info is None:
            return None

        if session_info.expires_at <= datetime.now():
            self.__sessions.pop(token)
            return None

        if prolongate:
            session_info.expires_at = datetime.now() + session_info.expire_time

        return session_info.user_info

    def create_session(
        self,
        user_info: UserInfo,
        expire_time: timedelta = DEFAULT_EXPIRE_TIME,
    ) -> str:
        token = uuid4().hex

        self.__sessions[token] = SessionInfo(
            expires_at=datetime.now() + expire_time,
            expire_time=expire_time,
            user_info=user_info,
            token=token,
        )

        return token
