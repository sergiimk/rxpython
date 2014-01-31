from ..futures.cooperative import Future
from ._observable_base import (ObservableBase,
                               StreamEndError,
                               CancelledError,
                               InvalidStateError)


class Observable(ObservableBase):
    _future = Future
