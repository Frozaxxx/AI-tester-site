from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import User
from app.security import AccessToken


@dataclass
class Credentials:
    email: str
    password: str


@dataclass
class Tokens:
    user: User
    access: AccessToken
    refresh_token: str
    refresh_expires_at: datetime
