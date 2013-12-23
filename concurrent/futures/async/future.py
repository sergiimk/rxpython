from concurrent.futures.sync.future_core import _PENDING, _CANCELLED
from concurrent.futures.sync.future_callbacks import FutureCoreCallbacks
from concurrent.futures.sync.future_extensions import FutureExtensions
from threading import Condition


class Future(FutureCoreCallbacks, FutureExtensions):
    def __init__(self, clb_executor=None):
        """Initialize the future.

        The optional clb_executor argument allows to explicitly set the
        executor object used by the future for running callbacks.
        If it's not provided, the future uses the default executor.
        """
        FutureCoreCallbacks.__init__(self, clb_executor)
        self._mutex = Condition()

    def _try_set_result(self, state, result, exception):
        with self._mutex:
            return FutureCoreCallbacks._try_set_result(self, state, result, exception)

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
            if self._state != _PENDING:
                return False
            return FutureCoreCallbacks._try_set_result(self, _CANCELLED, None, None)

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
            if self._state == _PENDING:
                self._mutex.wait(timeout)
            if self._state == _PENDING:
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
            if self._state == _PENDING:
                self._mutex.wait(timeout)
            if self._state == _PENDING:
                raise TimeoutError("Future waiting timeout reached")
            return FutureCoreCallbacks.exception(self)

    def add_done_callback(self, fun_res, executor=None):
        """Add a callback to be run when the future becomes done.

        The callback is called with a single argument - the future object. If
        the future is already done when this is called, the callback is
        scheduled with call_soon.
        """
        with self._mutex:
            FutureCoreCallbacks.add_done_callback(self, fun_res, executor)

    def remove_done_callback(self, fn):
        """Remove all instances of a callback from the "call when done" list.

        Returns the number of callbacks removed.
        """
        with self._mutex:
            return FutureCoreCallbacks.remove_done_callback(self, fn)

    #override
    def _on_result_set(self):
        FutureCoreCallbacks._on_result_set(self)
        self._mutex.notify_all()
