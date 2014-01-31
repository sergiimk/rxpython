from ._observable_extensions import ObservableBaseExt
from ._exceptions import StreamEndError
from ..futures.cooperative import Future, CancelledError, InvalidStateError


class Observable(ObservableBaseExt):
    _future = Future
