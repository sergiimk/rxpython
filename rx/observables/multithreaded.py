from ._observable_base import ObservableBase, _ACTIVE, _CANCELLED
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
            return super().cancelled()

    def done(self):
        with self._mutex:
            return super().done()

    def next(self):
        with self._mutex:
            return super().next()

    def exception(self):
        with self._mutex:
            return super().exception()

    def cancel(self):
        with self._mutex:
            if self._state != _ACTIVE:
                return False
            self._error_handled()
            return super()._try_end(_CANCELLED, None)

    def _try_set_next_value(self, value):
        with self._mutex:
            return super()._try_set_next_value(value)

    def _try_end(self, state, exception):
        with self._mutex:
            return super()._try_end(state, exception)

    def __repr__(self):
        with self._mutex:
            return super().__repr__()
