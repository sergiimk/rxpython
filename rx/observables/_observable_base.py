from ._exceptions import StreamEndError
from ..futures.cooperative import Future, CancelledError, InvalidStateError


# States for Observable
_ACTIVE = 'ACTIVE'
_CANCELLED = 'CANCELLED'
_ENDED = 'ENDED'


class ObservableBase:
    _state = _ACTIVE

    def __init__(self):
        self._promises = []
        self._callbacks = []

    def add_observe_callback(self, fun):
        if self._state != _ACTIVE:
            future = Future()
            future.set_exception(StreamEndError() if self._state == _ENDED else CancelledError())
            self._run_callback(fun, future)
        else:
            self._callbacks.append(fun)

    def remove_observe_callback(self, fun):
        filtered_callbacks = [f for f in self._callbacks if f != fun]
        removed_count = len(self._callbacks) - len(filtered_callbacks)
        if removed_count:
            self._callbacks[:] = filtered_callbacks
        return removed_count

    def cancelled(self):
        """Return True if the observable stream was cancelled."""
        return self._state == _CANCELLED

    def done(self):
        """Return True if the observable stream is ended or has been cancelled."""
        return self._state != _ACTIVE

    def next(self):
        promise = Future()
        self._promises.append(promise)
        return promise

    def cancel(self):
        """Cancel the observable and trigger callbacks.

        If the observable is already ended or cancelled, returns False.
        Otherwise, changes the state to cancelled, schedules the callbacks
        and returns True.
        """
        if self._state != _ACTIVE:
            return False
        self._set_state(_CANCELLED)
        return True

    def set_next_value(self, value):
        if not self.try_set_next_value(value):
            raise InvalidStateError("Observable is already marked as ended")

    def try_set_next_value(self, value):
        if self._state == _CANCELLED:
            return True
        if self._state == _ENDED:
            return False

        promise = None
        if self._promises:
            promise = self._promises.pop(0)
            promise.set_result(value)

        if self._callbacks:
            if promise is None:
                promise = Future()
                promise.set_result(value)
            self._run_callbacks(promise)

        return True

    def set_end(self):
        if self._state == _CANCELLED:
            return False
        if self._state == _ENDED:
            raise InvalidStateError("Observable is already marked as ended")
        self._set_state(_ENDED)
        return True

    def _set_state(self, state):
        self._state = state
        exc = StreamEndError() if state == _ENDED else CancelledError()
        promise = None

        if self._promises:
            promise = self._promises[0]
            promises = self._promises[:]
            self._promises.clear()
            for p in promises:
                p.set_exception(exc)

        if self._callbacks:
            if promise is None:
                promise = Future()
                promise.set_exception(exc)
            self._run_callbacks(promise)

    def _run_callbacks(self, future):
        callbacks = self._callbacks[:]
        for clb in callbacks:
            clb(self, future)

    def _run_callback(self, fun, future):
        fun(self, future)

    def __repr__(self):
        res = self.__class__.__name__
        if self._state == _ACTIVE and self._callbacks:
            size = len(self._callbacks)
            if size > 2:
                res += '<{}, [{}, <{} more>, {}]>'.format(
                    self._state, self._callbacks[0],
                    size - 2, self._callbacks[-1])
            else:
                res += '<{}, {}>'.format(self._state, self._callbacks)
        else:
            res += '<{}>'.format(self._state)
        return res
