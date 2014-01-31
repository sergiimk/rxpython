from ._future_base import FutureBase, InvalidStateError, CancelledError
from ._future_extensions import FutureBaseExt


class Future(FutureBaseExt):
    """Future to be used in cooperative multitasking concurrency environment."""
