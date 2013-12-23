from .config import Default
from asyncio import InvalidStateError
from concurrent.futures._base import TimeoutError, CancelledError


class FutureState(object):
    in_progress = 0
    success = 1
    failure = -1
    cancelled = -2


class FutureCore(object):
    """Encapsulates Future state."""

    def __init__(self):
        self._state = FutureState.in_progress
        self._value = None
        self._failure_handled = False

    def __del__(self):
        if self._state == FutureState.failure and not self._failure_handled:
            Default.default_callback(self)

    def set_result(self, result):
        if not self.try_set_result(result):
            raise InvalidStateError("result was already set")

    def try_set_result(self, result):
        return self._try_set_result(FutureState.success, result)

    def set_exception(self, exception):
        if not self.try_set_exception(exception):
            raise InvalidStateError("result was already set")

    def try_set_exception(self, exception):
        assert isinstance(exception, Exception), "Promise.failure expects Exception instance"
        return self._try_set_result(FutureState.failure, exception)


    def _complete(self, fun, *args, **kwargs):
        try:
            self.set_result(fun(*args, **kwargs))
        except Exception as ex:
            self.set_exception(ex)

    def _set_from(self, future):
        if future.exception() is None:
            self.set_result(future.result())
        else:
            self.set_exception(future.exception())

    def _try_set_from(self, future):
        if future.exception() is None:
            return self.try_set_result(future.result())
        else:
            return self.try_set_exception(future.exception())

    def _try_set_result(self, state, value):
        if self._state == FutureState.cancelled:
            return True
        if self._state:
            return False
        self._state = state
        self._value = value
        self._on_result_set()
        return True

    #virtual
    def _on_result_set(self):
        pass

    def done(self):
        """Returns True if future is completed or cancelled."""
        return self._state != FutureState.in_progress

    def cancelled(self):
        """Returns True if the future cancellation was requested."""
        return self._state == FutureState.cancelled

    def cancel(self):
        """Requests cancellation of future.

        Returns:
            True if future was not yet completed or cancelled.
        """
        if self._state != FutureState.in_progress:
            return False
        self._state = FutureState.cancelled
        self._value = CancelledError("Future was cancelled")
        self._on_result_set()
        return True

    def result(self):
        """Return the result this future represents.

        If the future has been cancelled, raises CancelledError.  If the
        future's result isn't yet available, raises InvalidStateError.  If
        the future is done and has an exception set, this exception is raised.
        """
        if not self._state:
            raise InvalidStateError("Result is not ready")
        if self._state == FutureState.cancelled:
            raise self._value
        if self._state == FutureState.failure:
            self._failure_handled = True
            raise self._value
        return self._value

    def exception(self):
        """Return the exception that was set on this future.

        The exception (or None if no exception was set) is returned only if
        the future is done.  If the future has been cancelled, raises
        CancelledError.  If the future isn't done yet, raises
        InvalidStateError.
        """
        if not self._state:
            raise TimeoutError()
        if self._state == FutureState.failure or self._state == FutureState.cancelled:
            self._failure_handled = True
            return self._value
        return None
