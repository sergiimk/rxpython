from .exceptions import StreamEndError
from ..futures.cooperative import Future


class ObservableBase:
    def __init__(self):
        self._promises = []
        self._callbacks = []

    def add_observe_callback(self, fun):
        self._callbacks.append(fun)

    def remove_observe_callback(self, fun):
        filtered_callbacks = [f for f in self._callbacks if f != fun]
        removed_count = len(self._callbacks) - len(filtered_callbacks)
        if removed_count:
            self._callbacks[:] = filtered_callbacks
        return removed_count

    def next(self):
        promise = Future()
        self._promises.append(promise)
        return promise

    def set_next_value(self, value):
        if self._promises:
            promise = self._promises.pop(0)
        else:
            promise = Future()
        promise.set_result(value)
        self._run_callbacks(promise)

    def set_end(self):
        exc = StreamEndError()
        if self._promises:
            promises = self._promises[:]
            promise = promises[0]
            self._promises.clear()
            for p in promises:
                p.set_exception(exc)
        else:
            promise = Future()
            promise.set_exception(exc)
        self._run_callbacks(promise)

    def _run_callbacks(self, future):
        callbacks = self._callbacks[:]
        for clb in callbacks:
            clb(self, future)
