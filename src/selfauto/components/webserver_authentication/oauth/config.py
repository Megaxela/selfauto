from dataclasses import dataclass

from .templates.generic import GenericTemplate


@dataclass
class OAuthProviderConfig:
    label: str
    title: str
    template: str
    config: GenericTemplate.Config
