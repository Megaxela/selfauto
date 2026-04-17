from .serial_component import SerialComponent as Component
from .connection import Connection
from .multiplexed_connection import (
    MultiplexedConnection,
    WriteLock,
    ConnectionLockedError,
)
