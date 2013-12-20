from .future_core import (FutureCore,
                          FutureCoreSuccess,
                          FutureCoreFailure,
                          FutureState)

from .config import Default


class FutureCoreCallbacks(FutureCore):
    def __init__(self, clb_executor=None):
        FutureCore.__init__(self)
        self._success_clb = []
        self._failure_clb = []
        self._executor = clb_executor or Default.get_callback_executor()

    def on_success(self, fun_res, executor=None):
        assert callable(fun_res), "Future.on_success expects callable"
        with self._mutex:
            if self._state == FutureState.success:
                self._run_callback(fun_res, executor)
            elif not self._state:
                self._success_clb.append((fun_res, executor))

    def on_failure(self, fun_ex, executor=None):
        assert callable(fun_ex) or fun_ex is None, "Future.on_failure expects callable or None"
        with self._mutex:
            self._failure_handled = True
            if fun_ex is not None:
                if self._state == FutureState.failure or self._state == FutureState.cancelled:
                    self._run_callback(fun_ex, executor)
                elif not self._state:
                    self._failure_clb.append((fun_ex, executor))

    #override
    def _on_result_set(self):
        success = self._state == FutureState.success
        callbacks = self._success_clb if success else self._failure_clb

        self._success_clb = None
        self._failure_clb = None

        for clb, exc in callbacks:
            self._run_callback(clb, exc)

    def _run_callback(self, clb, executor):
        exc = executor or self._executor
        f = exc.submit(clb, self._value)
        f.on_failure(Default.UNHANDLED_FAILURE_CALLBACK)


class FutureCoreCallbacksSuccess(FutureCoreSuccess):
    def __init__(self, value, clb_executor=None):
        FutureCoreSuccess.__init__(self, value)
        self._executor = clb_executor or Default.get_callback_executor()

    def on_success(self, fun_res, executor=None):
        assert callable(fun_res), "Future.on_success expects callable"
        exc = executor or self._executor
        f = exc.submit(fun_res, self._value)
        f.on_failure(Default.UNHANDLED_FAILURE_CALLBACK)

    def on_failure(self, fun_ex, executor=None):
        pass


class FutureCoreCallbacksFailure(FutureCoreFailure):
    def __init__(self, exception, clb_executor=None):
        FutureCoreFailure.__init__(self, exception)
        self._executor = clb_executor or Default.get_callback_executor()

    def on_success(self, fun_res, executor=None):
        pass

    def on_failure(self, fun_ex, executor=None):
        assert callable(fun_ex), "Future.on_failure expects callable"
        exc = executor or self._executor
        f = exc.submit(fun_ex, self._value)
        f.on_failure(Default.UNHANDLED_FAILURE_CALLBACK)
