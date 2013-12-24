from .future_core import FutureCore, _PENDING
from .ensure_exception_handled import EnsureExceptionHandledGuard
from ..config import Default


class FutureCallbacks(FutureCore):
    """Implements Future callbacks behavior."""

    def __init__(self, clb_executor=None):
        """Initialize the future.

        The optional clb_executor argument allows to explicitly set the
        executor object used by the future for running callbacks.
        If it's not provided, the future uses the default executor.
        """
        FutureCore.__init__(self)
        self._callbacks = []
        self._executor = clb_executor or Default.get_callback_executor()

    def add_done_callback(self, fun_res, executor=None):
        """Add a callback to be run when the future becomes done.

        The callback is called with a single argument - the future object. If
        the future is already done when this is called, the callback is
        scheduled with call_soon.
        """
        assert callable(fun_res) or fun_res is None, "Future.add_done_callback expects callable or None"
        if fun_res is not None:
            if self._state != _PENDING:
                self._run_callback(fun_res, executor)
            else:
                self._callbacks.append((fun_res, executor))

    def remove_done_callback(self, fn):
        """Remove all instances of a callback from the "call when done" list.

        Returns the number of callbacks removed.
        """
        filtered_callbacks = [f for f in self._callbacks if f != fn]
        removed_count = len(self._callbacks) - len(filtered_callbacks)
        if removed_count:
            self._callbacks[:] = filtered_callbacks
        return removed_count

    #override
    def _on_result_set(self):
        if self._exception is not None:
            clb = Default.UNHANDLED_FAILURE_CALLBACK
            self._ex_handler = EnsureExceptionHandledGuard(self._exception, clb)
            self._executor(self._ex_handler.activate)

        callbacks = self._callbacks[:]
        if not callbacks:
            return

        self._callbacks[:] = []
        for clb, executor in callbacks:
            self._run_callback(clb, executor)

    def _run_callback(self, clb, executor):
        executor = executor or self._executor
        executor(clb, self)
