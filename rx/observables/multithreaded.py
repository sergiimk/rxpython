from ._observable_base import ObservableBase
from ..futures.multithreaded import Future
from threading import Lock


class Observable(ObservableBase):
    _future = Future

    def __init__(self, *, clb_executor=None):
        super().__init__(clb_executor=clb_executor)
        self._mutex = Lock()

    def add_observe_callback(self, fun, *, executor=None):
        with self._mutex:
            super().add_observe_callback(fun, executor=executor)

    def remove_observe_callback(self, fun):
        with self._mutex:
            return super().remove_observe_callback(fun)

    def cancelled(self):
        with self._mutex:
            return super().cancel()

    def done(self):
        with self._mutex:
            return super().done()

    def next(self):
        with self._mutex:
            return super().next()

    def cancel(self):
        with self._mutex:
            return super().cancel()

    def try_set_next_value(self, value):
        with self._mutex:
            return super().try_set_next_value(value)

    def set_end(self):
        with self._mutex:
            return super().set_end()
