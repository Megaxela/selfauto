import dataclasses
import typing as tp

import dacite
import yaml


@dataclasses.dataclass
class Config:
    components: tp.Dict[str, dict]

    @staticmethod
    def load_from_file(path: str):
        with open(path, "r") as f:
            return dacite.from_dict(
                Config, yaml.load(f, Loader=yaml.FullLoader).get("config")
            )
