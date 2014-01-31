from ..futures.cooperative import Future
from ._observable_base import (ObservableBase,
                               StreamEndError,
                               CancelledError,
                               InvalidStateError)


class Observable(ObservableBase):
    def __iter__(self):
        return self

    def __next__(self):
        return self.next().recover(Observable._rec_iter)

    @staticmethod
    def _rec_iter(exc):
        if isinstance(exc, StreamEndError):
            raise StopIteration
        else:
            raise exc