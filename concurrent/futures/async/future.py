from concurrent.futures.sync.future_core import FutureState, CancelledError
from concurrent.futures.sync.future_callbacks import FutureCoreCallbacks
from concurrent.futures.sync.future_extensions import FutureExtensions
from threading import Condition


class Future(FutureCoreCallbacks, FutureExtensions):
    def __init__(self, clb_executor=None):
        FutureCoreCallbacks.__init__(self, clb_executor)
        self._mutex = Condition()

    def __del__(self):
        with self._mutex:
            FutureCoreCallbacks.__del__(self)

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

    def done(self):
        """Returns True if future is completed or cancelled."""
        with self._mutex:
            return FutureCoreCallbacks.done(self)

    def cancelled(self):
        """Returns True if the future cancellation was requested."""
        with self._mutex:
            return FutureCoreCallbacks.cancelled(self)

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

    def result(self, timeout=None):
        """Return the result this future represents.
        If the future has not yet been completed this method with block for
        for up to timeout seconds. If timeout is not specified it will block
        for unlimited time.

        If the future has been cancelled, raises CancelledError.  If the
        future does not complete in specified time frame, raises TimeoutError.  If
        the future is done and has an exception set, this exception is raised.
        """
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            if not self._state:
                raise TimeoutError("Future waiting timeout reached")
            return FutureCoreCallbacks.result(self)

    def exception(self, timeout=None):
        """Return the exception that was set on this future.
        If the future has not yet been completed this method with block for
        for up to timeout seconds. If timeout is not specified it will block
        for unlimited time.

        If the future has been cancelled, raises CancelledError.
        If the future does not complete in specified time frame,
        raises TimeoutError
        """
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            if not self._state:
                raise TimeoutError("Future waiting timeout reached")
            return FutureCoreCallbacks.exception(self)
