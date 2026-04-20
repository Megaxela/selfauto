from logging import getLogger, Logger
from aiohttp.web import Request, Response
from aiohttp.web_exceptions import HTTPForbidden

from selfauto.components.webserver import BasicMiddleware
from selfauto.components import authentication
from .sessions.store import SessionStore

from .config import WebserverAuthenticationConfig, HeaderTokenAuthConfig


class Middleware(BasicMiddleware):
    def __init__(
        self,
        auth_component: authentication.Component,
        session_store: SessionStore,
        config: WebserverAuthenticationConfig,
        logger: Logger,
        *args,
        **kwargs,
    ):
        self._auth_component: authentication.Component = auth_component
        self._config: WebserverAuthenticationConfig = config
        self._session_store: SessionStore = session_store
        self._logger = logger

    @property
    def logger(self):
        return self._logger

    async def on_before_request(self, request: Request):
        # 1. All oauth endpoints should not be checked for
        #    authentication.
        if request.path.startswith("/api/oauth"):
            return

        # 2. Iterate auth methods and handling them
        # 2.1. Check Bearer token for OAuth
        if await self.__check_oauth_bearer_token_auth(request):
            return

        # 2.2. Header Token Auth
        for config in self._config.header_token_auth:
            if await self.__handle_header_token_auth(request, config):
                # Just exit on successfull authentication
                return

        # 3. Raise 403 if no authentication methods was successfull.
        raise HTTPForbidden(reason="Authentication required")

    async def on_after_request(self, request: Request, response: Response):
        pass

    async def on_error(self, request: Request, e: Exception):
        pass

    async def __check_oauth_bearer_token_auth(self, request: Request):
        token_value = request.headers.get("X-Auth-Token")
        if token_value is None:
            # If it's a websocket connection - get token
            # from query arg
            if request.headers.get("Upgrade") == "websocket":
                token_value = request.query["token"]

        if token_value is None:
            return False

        user = self._session_store.get_session_by_token(token_value, prolongate=True)
        if user is None:
            return False

        request.userinfo = user
        return True

    async def __handle_header_token_auth(
        self, request: Request, config: HeaderTokenAuthConfig
    ) -> bool:
        token_value = request.headers.get(config.header_name)
        if token_value is None:
            if request.headers.get("Upgrade") == "websocket":
                token_value = request.query["token"]

        if token_value is None:
            return False

        engine = self._auth_component.get_engine(config.auth_engine)
        if engine is None:
            self.logger.error(
                "No '%s' authentication engine is defined for authentication component. Skipping.",
                config.auth_engine,
            )
            return False

        return await engine.authenticate({"token": token_value})
