from typing import List
from dataclasses import dataclass, field


@dataclass()
class ModemGPIO:
    rts: bool = False


@dataclass()
class ConnectionConfig:
    label: str
    path: str
    modem_gpio: ModemGPIO = field(default_factory=ModemGPIO)
    supported_speeds: List[int] | None = None
