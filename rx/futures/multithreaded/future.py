from ..future_base import _PENDING, _CANCELLED
from ..future_extensions import FutureBaseExt
from ..exceptions import InvalidStateError, TimeoutError
from threading import Condition

from ..cooperative.future import Future as FutureCoop
from concurrent.futures import Future as FutureCF


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

    def wait(self, timeout=None):
        """Blocking wait for future to complete.
        If the future has not yet been completed this method blocks for
        specified number of seconds. If timeout is not specified it will
        block indefinitely.

        Returns True if future is completed.
        """
        with self._mutex:
            if self._state == _PENDING:
                self._mutex.wait(timeout)
            return self._state != _PENDING

    def result(self, *, timeout=None):
        """Return the result this future represents.
        If the future has not yet been completed this method blocks for
        up to timeout seconds.

        If timeout is not specified and the future is not completed, raises
        InvalidStateError.
        If the future has been cancelled, raises CancelledError.
        If the future does not complete in specified time frame, raises TimeoutError.
        If the future is done and has an exception set, this exception is raised.
        """
        with self._mutex:
            if self._state == _PENDING:
                if timeout is None:
                    raise InvalidStateError('Result is not ready.')
                else:
                    self._mutex.wait(timeout)
            if self._state == _PENDING:
                raise TimeoutError("Future waiting timeout reached")
            return super().result()

    def exception(self, *, timeout=None):
        """Return the exception that was set to this future.
        If the future has not yet been completed this method blocks for
        up to timeout seconds.

        If timeout is not specified and the future is not completed, raises
        InvalidStateError.
        If the future has been cancelled, raises CancelledError.
        If the future does not complete in specified time frame,
        raises TimeoutError.
        """
        with self._mutex:
            if self._state == _PENDING:
                if timeout is None:
                    raise InvalidStateError('Result is not ready.')
                else:
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
        if isinstance(future, cls) or isinstance(future, FutureCoop):
            return future
        if isinstance(future, FutureCF):
            return cls._wrap_concurrent_future(future)
        raise TypeError("{} is not compatible with {}"
        .format(_typename(cls), _typename(type(future))))

    @classmethod
    def _wrap_concurrent_future(cls, cff):
        f = cls()

        def done(_):
            if cff.cancelled():
                f.cancel()
            else:
                exception = cff.exception()
                if exception is not None:
                    f.set_exception(exception)
                else:
                    f.set_result(cff.result())

        def backprop_cancel(_):
            if f.cancelled():
                cff.cancel()

        cff.add_done_callback(done)
        f.add_done_callback(backprop_cancel)

        return f


def _typename(cls):
    return cls.__module__ + '.' + cls.__name__

