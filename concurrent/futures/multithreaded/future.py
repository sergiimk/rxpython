from concurrent.futures.cooperative.future_base import _PENDING, _CANCELLED
from concurrent.futures.cooperative.future_extensions import FutureBaseExt
from concurrent.futures.cooperative.future import Future as FutureST
from ..exceptions import TimeoutError
from threading import Condition


class Future(FutureBaseExt):
    def __init__(self, *, clb_executor=None):
        """Initialize the future.

        The optional clb_executor argument allows to explicitly set the
        executor object used by the future for running callbacks.
        If it's not provided, the future uses the default executor.
        """
        super().__init__(clb_executor=clb_executor)
        self._mutex = Condition()

    def add_done_callback(self, fun_res, *, executor=None):
        """Add a callback to be run when the future becomes done.

        The callback is called with a single argument - the future object. If
        the future is already done when this is called, the callback is
        scheduled with call_soon.
        """
        with self._mutex:
            super().add_done_callback(fun_res, executor=executor)

    def remove_done_callback(self, fn):
        """Remove all instances of a callback from the "call when done" list.

        Returns the number of callbacks removed.
        """
        with self._mutex:
            return super().remove_done_callback(fn)

    def done(self):
        """Returns True if future is completed or cancelled."""
        with self._mutex:
            return super().done()

    def cancelled(self):
        """Returns True if the future cancellation was requested."""
        with self._mutex:
            return super().cancelled()

    def result(self, *, timeout=None):
        """Return the result this future represents.
        If the future has not yet been completed this method blocks for
        up to timeout seconds. If timeout is not specified it will block
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
            return super().result()

    def exception(self, *, timeout=None):
        """Return the exception that was set on this future.
        If the future has not yet been completed this method blocks for
        up to timeout seconds. If timeout is not specified it will block
        for unlimited time.

        If the future has been cancelled, raises CancelledError.
        If the future does not complete in specified time frame,
        raises TimeoutError.
        """
        with self._mutex:
            if self._state == _PENDING:
                self._mutex.wait(timeout)
            if self._state == _PENDING:
                raise TimeoutError("Future waiting timeout reached")
            return super().exception()

    def cancel(self):
        """Requests cancellation of future.

        Returns:
            True if future was not yet completed or cancelled.
        """
        with self._mutex:
            if self._state != _PENDING:
                return False
            return super()._try_set_state(_CANCELLED, None, None)

    def _try_set_state(self, state, result, exception):
        with self._mutex:
            return super()._try_set_state(state, result, exception)

    def _on_result_set(self):
        super()._on_result_set()
        self._mutex.notify_all()

    @classmethod
    def convert(cls, future):
        """Single-threaded futures are compatible with multithreaded."""
        if isinstance(future, cls):
            return future
        if not isinstance(future, FutureST):
            raise TypeError("{} is not compatible with {}"
            .format(_typename(cls), _typename(type(future))))
        return future


def _typename(cls):
    return cls.__module__ + '.' + cls.__name__

