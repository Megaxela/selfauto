from abc import ABC, abstractmethod

from aiohttp.web import Request, Response


class BasicMiddleware:
    async def on_before_request(self, request: Request):
        pass

    async def on_after_request(self, request: Request, response: Response):
        pass

    async def on_error(self, request: Request, e: Exception):
        pass
