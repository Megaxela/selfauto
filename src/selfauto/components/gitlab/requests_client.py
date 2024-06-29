import aiohttp


class RequestsClient:
    def __init__(self, host: str, token: str):
        self._host: str = host
        self._token: str = token

    async def remove_label(self, project_id, issue_id, label):
        await self.__perform_request(
            "PUT",
            f"/projects/{project_id}/issues/{issue_id}?state_event=close&remove_labels={label}",
        )

    async def __perform_request(self, method, path, **kwargs):
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            headers={"PRIVATE-TOKEN": self._token},
        ) as session:
            async with getattr(session, method.lower())(
                f"{host}/api/v4{path}", **kwargs
            ) as resp:
                resp.raise_for_status()
