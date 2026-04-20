from dataclasses import dataclass
from typing import List, Any, Dict

from aiohttp.web import Request, json_response
from selfauto.components.basic_component import BasicComponent
from selfauto.components import webserver, authentication
from cryptography import fernet
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from .sessions.store import SessionStore
from .middleware import Middleware
from .config import WebserverAuthenticationConfig, HeaderTokenAuthConfig, OAuthConfig
from .oauth.config import OAuthProviderConfig
from .oauth.templates import GenericTemplate, GitlabTemplate
from .sessions.user_info import UserInfo

OAUTH_TEMPLATES = {
    GenericTemplate.NAME: GenericTemplate,
    GitlabTemplate.NAME: GitlabTemplate,
}


def build_oauth_provider(name: str, *args, **kwargs) -> GenericTemplate:
    cls = OAUTH_TEMPLATES.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown OAuth proivder template name '{name}'. Available values: [{', '.join(OAUTH_TEMPLATES.keys())}]"
        )

    return cls(*args, **kwargs)


class WebserverAuthenticationComponent(BasicComponent):
    NAME = "webserver_authentication"

    Config = WebserverAuthenticationConfig

    @staticmethod
    def make_default_config():
        return WebserverAuthenticationConfig(
            header_token_auth=[
                HeaderTokenAuthConfig(
                    auth_engine="engine_label",
                    header_name="X-Auth-Token",
                ),
            ],
            oauth=OAuthConfig(
                external_url="http://example.com",
                providers=[
                    OAuthProviderConfig(
                        template=GenericTemplate.NAME,
                        config=GenericTemplate.Config(
                            host="http://test.server.com",
                            token_endpoint="/oauth/token",
                            user_endpoint="/oauth/user",
                            client_id="CLIENT_ID",
                            client_secret="CLIENT_SECRET",
                        ),
                    ),
                ],
            ),
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Config = None
        self._oauth_templates = []
        self._session_store = SessionStore()

    async def on_initialize(self, config: Config):
        self._config = config

        # Getting authentication component
        authentication_component: authentication.Component = await self.find_component(
            authentication.Component
        )

        # Getting webserver component
        webserver_component: webserver.Component = await self.find_component(
            webserver.Component
        )

        # Adding authentication middleware
        webserver_component.add_middleware(
            Middleware(
                auth_component=authentication_component,
                session_store=self._session_store,
                config=self._config,
                logger=self.logger,
            )
        )

        # todo: change API to proper getter when implemented
        # Setup session storage
        fernet_key = fernet.Fernet.generate_key()
        f = fernet.Fernet(fernet_key)
        setup(webserver_component._app, EncryptedCookieStorage(f))

        # Proceed OAuth providers
        for oauth_config in self._config.oauth.providers:
            await self.__setup_oauth(webserver_component, oauth_config)

        # Handler to list available OAuth providers
        webserver_component.add_handler(
            "GET",
            "/api/oauth/providers",
            self.__make_oauth_list_handler(),
        )

        # Handler to check user
        webserver_component.add_handler(
            "GET",
            "/api/me",
            self.__make_me_handler(),
        )

    def __make_me_handler(self):
        async def handler(request: Request):
            if not hasattr(request, "userinfo"):
                return json_response(
                    {
                        "name": "Unknown",
                        "email": None,
                    }
                )

            userinfo: UserInfo = request.userinfo

            return json_response(
                {
                    "name": userinfo.name,
                    "email": userinfo.email,
                }
            )

        return handler

    def __make_oauth_list_handler(self):
        async def handler(request: Request):
            return json_response(
                {
                    "providers": [
                        {
                            "label": provider_config.label,
                            "title": provider_config.title,
                        }
                        for provider_config in self._config.oauth.providers
                    ]
                }
            )

        return handler

    async def __setup_oauth(
        self,
        server: webserver.Component,
        oauth_config: OAuthProviderConfig,
    ):
        provider_template = build_oauth_provider(
            oauth_config.template,
            logger=self.service.make_logger(f"{self.NAME}.{oauth_config.label}"),
        )
        await provider_template.initialize(
            server,
            self._session_store,
            oauth_config.label,
            self._config.oauth.external_url,
            oauth_config.config,
        )

    async def on_deinitialize(self):
        # todo: figure out a way to remove authentication middleware here
        pass

    async def run(self):
        pass  # do nothing for now
