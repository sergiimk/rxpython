from .future_core import FutureCore
from .config import Default


class FutureCoreCallbacks(FutureCore):
    """Implements Future callbacks behavior."""

    def __init__(self, clb_executor=None):
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
        self._failure_handled = True
        if fun_res is not None:
            if self._state:
                self._run_callback(fun_res, executor)
            else:
                self._callbacks.append((fun_res, executor))

    #override
    def _on_result_set(self):
        callbacks = self._callbacks
        self._callbacks = None

        for clb, executor in callbacks:
            self._run_callback(clb, executor)

    def _run_callback(self, clb, executor):
        exc = executor or self._executor
        f = exc.submit(clb, self)
        #f.add_done_callback(Default.default_callback)
