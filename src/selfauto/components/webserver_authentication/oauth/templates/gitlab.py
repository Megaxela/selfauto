from dataclasses import dataclass

from selfauto.components import webserver
from selfauto.components.webserver_authentication.sessions.store import SessionStore

from .generic import GenericTemplate


class GitlabTemplate:
    NAME = "gitlab"

    @dataclass
    class Config:
        host: str
        client_id: str
        client_secret: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def initialize(
        self,
        server: webserver.Component,
        session_store: SessionStore,
        label: str,
        external_url: str,
        config: Config,
    ):
        await super().initialize(
            server,
            session_store,
            label,
            external_url,
            GenericTemplate.Config(
                host=config.host,
                token_endpoint="",
                user_endpoint="",
                auth_endpoint="",
                client_id=config.client_id,
                client_secret=config.client_secret,
                scope="",
            ),
        )
