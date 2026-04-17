from dataclasses import dataclass
from logging import Logger
from json import dumps
from urllib.parse import quote_plus

from aiohttp_session import get_session
from selfauto.components import webserver
from components.webserver_authentication.sessions.store import SessionStore
from components.webserver_authentication.sessions.user_info import UserInfo

from authlib.integrations.httpx_client import AsyncOAuth2Client
from aiohttp.web import Request, json_response, Response, HTTPFound, HTTPBadRequest


class GenericTemplate:
    NAME = "generic"

    @dataclass
    class Config:
        host: str
        token_endpoint: str
        user_endpoint: str
        auth_endpoint: str
        client_id: str
        client_secret: str
        scope: str

    def __init__(self, logger: Logger):
        self._config: GenericTemplate.Config | None = None
        self._label: str | None = None
        self.__oauth_client: AsyncOAuth2Client | None = None
        self.__session_store: SessionStore | None = None
        self._logger = logger

    @property
    def logger(self) -> Logger:
        return self._logger

    async def initialize(
        self,
        server: webserver.Component,
        session_store: SessionStore,
        label: str,
        external_url: str,
        config: Config,
    ):
        self._config = config
        self._label = label
        self.__session_store = session_store

        server.add_handler(
            "GET",
            self._make_callback_endpoint(),
            self._make_oauth_callback_handler(external_url, config),
        )

        # server.add_handler(
        #     "GET",
        #     self.make_endpoint(),
        #     self._make_oauth_get_handler(external_url, config),
        # )

        server.add_handler(
            "GET",
            self._make_login_endpoint(),
            self._make_oauth_login_handler(external_url, config),
        )

    def _make_endpoint(self):
        return f"/api/oauth/{self._label}"

    def _make_auth_endpoint(self):
        return f"{self._make_endpoint()}/auth"

    def _make_callback_endpoint(self):
        return f"{self._make_endpoint()}/callback"

    def _make_login_endpoint(self):
        return f"{self._make_endpoint()}/login"

    def _make_oauth_login_handler(
        self,
        external_url: str,
        config: Config,
    ):
        async def handler(request: Request):
            session = await get_session(request)

            redirect_uri = request.query.get("redirect_uri")
            client = self.__make_oauth_client(external_url, config)

            # todo: store state in csrf session
            auth_url, state = client.create_authorization_url(
                f"{config.host}{config.auth_endpoint}"
            )

            session["oauth_state"] = state
            session["redirect_uri"] = redirect_uri

            return HTTPFound(auth_url)

        return handler

    def _make_oauth_callback_handler(
        self,
        external_url: str,
        config: Config,
    ):
        async def handler(request: Request):
            code = request.query.get("code")
            state = request.query.get("state")
            session = await get_session(request)

            if state != session.get("oauth_state"):
                return HTTPBadRequest(text="Invalid state")

            async with self.__make_oauth_client(external_url, config) as client:
                # todo: wrap oauth token with webserver session token
                token = await client.fetch_token(code=code)
                user = await client.get(f"{config.host}{config.user_endpoint}")

                self.logger.info("Received user info: %s", dumps(user.json(), indent=2))

                user = user.json()

                # Create new bearer token session with received user data
                session_token = self.__session_store.create_session(
                    UserInfo(
                        email=user.get("email"),
                        name=user.get("name", user.get("sub")),
                    )
                )

                redirect_uri = session.get("redirect_uri")
                if redirect_uri:
                    return HTTPFound(
                        f"{redirect_uri}#access_token={quote_plus(session_token)}"
                    )

                return json_response(
                    {
                        "token": session_token,
                    }
                )

        return handler

    def __make_oauth_client(
        self,
        external_url: str,
        config: Config,
    ):
        return AsyncOAuth2Client(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=f"{external_url}{self._make_callback_endpoint()}",
            scope=config.scope,
            token_endpoint=f"{config.host}{config.token_endpoint}",
        )
