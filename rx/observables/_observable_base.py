from ._exceptions import StreamEndError
from ..futures import FutureBase, Synchronous, CancelledError, InvalidStateError
from ..config import Default
from .._ensure_exception_handled import EnsureExceptionHandledGuard


# States for Observable
_ACTIVE = 'ACTIVE'
_CANCELLED = 'CANCELLED'
_ENDED = 'ENDED'


# TODO: subscription-based callback removal and cancellation
class ObservableBase:
    _future = None
    _state = _ACTIVE
    _exception = None
    _ex_handler = None

    def __init__(self, *, clb_executor=None):
        self._promises = []
        self._callbacks = []
        self._executor = clb_executor or Synchronous

    def add_observe_callback(self, fun, *, executor=None):
        if self._state != _ACTIVE:
            exc = self._get_exception()
            future = self._future(clb_executor=executor or self._executor)
            future.set_exception(exc)
            self._run_callback(fun, future, executor)
        else:
            self._callbacks.append((fun, executor))

    def remove_observe_callback(self, fun):
        filtered_callbacks = [(f, exec) for f, exec in self._callbacks if f != fun]
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
        """Returns Future representing next value in the stream."""
        promise = self._future(clb_executor=self._executor)

        if self._state != _ACTIVE:
            exc = self._get_exception()
            promise.set_exception(exc)
        else:
            self._promises.append(promise)

        return promise

    def exception(self):
        if self._state == _CANCELLED:
            raise CancelledError()
        if self._state != _ENDED:
            raise InvalidStateError('Observable has not ended yet')
        self._error_handled()
        return self._exception

    def cancel(self):
        """Cancel the observable and trigger callbacks.

        If the observable is already ended or cancelled, returns False.
        Otherwise, changes the state to cancelled, schedules the callbacks
        and returns True.
        """
        if self._state != _ACTIVE:
            return False
        self._error_handled()
        return self._try_end(_CANCELLED, None)

    def set_next_value(self, value):
        if not self._try_set_next_value(value):
            raise InvalidStateError("Observable is already marked as ended")

    def try_set_next_value(self, value):
        return self._try_set_next_value(value)

    def set_exception(self, exception):
        if not self._try_end(_ENDED, exception):
            raise InvalidStateError("Observable is already marked as ended")

    def try_set_exception(self, exception):
        return self._try_end(_ENDED, exception)

    def set_end(self):
        if not self._try_end(_ENDED, None):
            raise InvalidStateError("Observable is already marked as ended")

    def _try_set_next_value(self, value):
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
                promise = self._future(clb_executor=self._executor)
                promise.set_result(value)
            self._run_callbacks(promise)

        return True

    def _try_end(self, state, exception):
        if self._state == _CANCELLED:
            return True
        if self._state == _ENDED:
            return False

        self._state = state

        if exception is not None:
            self._exception = exception
            clb = Default.UNHANDLED_FAILURE_CALLBACK
            self._ex_handler = EnsureExceptionHandledGuard(self._exception, clb)
            self._executor(self._ex_handler.activate)

        exc = self._get_exception()
        promise = None

        if self._promises:
            self._error_handled()
            promise = self._promises[0]
            promises = self._promises[:]
            self._promises.clear()
            for p in promises:
                p.set_exception(exc)

        if self._callbacks:
            self._error_handled()
            if promise is None:
                promise = self._future(clb_executor=self._executor)
                promise.set_exception(exc)
            self._run_callbacks(promise)

        return True

    def _get_exception(self):
        if self._exception is not None:
            return self._exception
        if self._state == _CANCELLED:
            return CancelledError()
        return StreamEndError()

    def _run_callbacks(self, future):
        callbacks = self._callbacks[:]
        for fun, executor in callbacks:
            self._run_callback(fun, future, executor)

    def _run_callback(self, fun, future, executor):
        executor = executor or self._executor
        executor(fun, self, future)

    def _error_handled(self):
        if self._ex_handler is not None:
            self._ex_handler.clear()
            self._ex_handler = None

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
        elif self._exception is not None:
            res += '<exception={!r}>'.format(self._exception)
        else:
            res += '<{}>'.format(self._state)
        return res

    def __iter__(self):
        return self

    def __next__(self):
        return self.next().recover(ObservableBase._rec_iter)

    @staticmethod
    def _rec_iter(exc):
        if isinstance(exc, StreamEndError):
            raise StopIteration
        else:
            raise exc
