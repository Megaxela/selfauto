import dataclasses

from selfauto.components.basic_component import BasicComponent
from selfauto.components.gitlab.requests_client import RequestsClient


class GitlabComponent(BasicComponent):
    NAME = "gitlab"

    @dataclasses.dataclass()
    class Config:
        token: str
        host: str

    @staticmethod
    def make_default_config():
        return GitlabComponent.Config(
            token="<gitlab_token>",
            host="https://you_gitlab_instance",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._requests_client: RequestsClient = None

    async def on_initialize(self, config: Config):
        self._requests_client = RequestsClient(config.host, config.token)

    @property
    def requests(self):
        return self._requests_client
