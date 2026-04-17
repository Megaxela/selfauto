from dataclasses import dataclass
from typing import List

from .oauth.config import OAuthProviderConfig


@dataclass
class HeaderTokenAuthConfig:
    auth_engine: str
    header_name: str


@dataclass
class OAuthConfig:
    external_url: str
    providers: List[OAuthProviderConfig]


@dataclass
class WebserverAuthenticationConfig:
    header_token_auth: List[HeaderTokenAuthConfig] | None = None
    oauth: OAuthConfig | None = None
