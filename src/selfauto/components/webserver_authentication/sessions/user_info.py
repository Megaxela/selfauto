from dataclasses import dataclass


@dataclass
class UserInfo:
    email: str | None
    name: str | None
