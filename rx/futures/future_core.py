from .config import Default
from threading import Condition
from concurrent.futures import CancelledError


class IllegalStateError(Exception):
    pass


class FutureState(object):
    in_progress = 0
    success = 1
    failure = -1
    cancelled = -2


class FutureBase(object):
    pass


class FutureCore(FutureBase):
    def __init__(self):
        self._mutex = Condition()
        self._state = FutureState.in_progress
        self._value = None
        self._failure_handled = False

    def __del__(self):
        with self._mutex:
            if self._state == FutureState.failure and not self._failure_handled:
                Default.UNHANDLED_FAILURE_CALLBACK(self._value)

    def _success(self, result):
        if not self._try_success(result):
            raise IllegalStateError("result was already set")

    def _try_success(self, result):
        return self._try_set_result(FutureState.success, result)

    def _failure(self, exception):
        if not self._try_failure(exception):
            raise IllegalStateError("result was already set")

    def _try_failure(self, exception):
        assert isinstance(exception, Exception), "Promise.failure expects Exception instance"
        return self._try_set_result(FutureState.failure, exception)

    def _complete(self, fun, *vargs, **kwargs):
        if not self._try_complete(fun, *vargs, **kwargs):
            raise IllegalStateError("result was already set")

    def _try_complete(self, fun, *vargs, **kwargs):
        try:
            return self._try_success(fun(*vargs, **kwargs))
        except Exception as ex:
            return self._try_failure(ex)

    def _try_set_result(self, state, value):
        with self._mutex:
            if self._state == FutureState.cancelled:
                return True
            if self._state:
                return False
            self._state = state
            self._value = value
            self._mutex.notify_all()
            self._on_result_set()
            return True

    #virtual
    def _on_result_set(self):
        pass

    @property
    def is_completed(self):
        """Returns True if future is completed or cancelled."""
        with self._mutex:
            return self._state != FutureState.in_progress

    @property
    def is_cancelled(self):
        """Returns True if the future cancellation was requested."""
        with self._mutex:
            return self._state == FutureState.cancelled

    def cancel(self):
        """Requests cancellation of future.

        Returns:
            True if future was not yet completed or cancelled.
        """
        with self._mutex:
            if self._state != FutureState.in_progress:
                return False
            self._state = FutureState.cancelled
            self._value = CancelledError("Future was cancelled")
            self._mutex.notify_all()
            self._on_result_set()
            return True

    def wait(self, timeout=None):
        """Blocking wait for future to complete.

        Args:
            timeout: time in seconds to wait for completion (default - infinite).

        Returns:
            True if future completes within timeout.
        """
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            return self._state != FutureState.in_progress

    def result(self, timeout=None):
        """Blocking wait for future result.

        Args:
            timeout: time in seconds to wait for completion (default - infinite).

        Returns:
            Future result value.

        Raises:
            TimeoutError: if future does not complete within timeout.
            CancelledError: if future cancellation was requested,
            Exception: if future was failed.
        """
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            if not self._state:
                raise TimeoutError()
            if self._state == FutureState.cancelled:
                raise self._value
            if self._state == FutureState.failure:
                self._failure_handled = True
                raise self._value
            return self._value

    def exception(self, timeout=None):
        """Blocking wait for future exception.

        Args:
            timeout: time in seconds to wait for completion (default - infinite).

        Returns:
            Exception future failed with, including CancelledError, or None if succeeded.

        Raises:
            TimeoutError: if future does not complete within timeout.
        """
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            if not self._state:
                raise TimeoutError()
            if self._state == FutureState.failure or self._state == FutureState.cancelled:
                self._failure_handled = True
                return self._value
            return None


class FutureCoreCompleted(FutureBase):
    def __init__(self, value):
        self._value = value
        self.is_completed = True
        self.is_cancelled = False

    def cancel(self):
        return False

    def wait(self, timeout=None):
        return True


class FutureCoreSuccess(FutureCoreCompleted):
    def result(self, timeout=None):
        return self._value

    def exception(self, timeout=None):
        return None


class FutureCoreFailure(FutureCoreCompleted):
    def result(self, timeout=None):
        raise self._value

    def exception(self, timeout=None):
        return self._value
