from .future_core import FutureCore, FutureState
from .config import on_unhandled_failure
from threading import Lock
import functools


class FutureCoreCallbacks(FutureCore):
    def __init__(self, clb_executor=None):
        FutureCore.__init__(self)
        self._executor = clb_executor or Synchronous
        self._success_clb = []
        self._failure_clb = []

    #thread: any
    def on_success(self, fun_res, executor=None):
        assert (callable(fun_res))
        with self._mutex:
            if self._state == FutureState.success:
                self._run_callback(fun_res, executor)
            elif not self._state:
                self._success_clb.append((fun_res, executor))

    #thread: any
    def on_failure(self, fun_ex, executor=None):
        assert (callable(fun_ex))
        with self._mutex:
            self._failure_handled = True
            if self._state == FutureState.failure:
                self._run_callback(fun_ex, executor)
            elif not self._state:
                self._failure_clb.append((fun_ex, executor))

    #thread: executor
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
        f = exc.execute(clb, self._value)
        f.on_failure(on_unhandled_failure)


class Future(FutureCoreCallbacks):
    def __init__(self, clb_executor=None):
        FutureCoreCallbacks.__init__(self, clb_executor)

    @staticmethod
    def successful(result=None, clb_executor=None):
        f = Future(clb_executor)
        f._success(result)
        return f

    @staticmethod
    def failed(exception, clb_executor=None):
        f = Future(clb_executor)
        f._failure(exception)
        return f

    def recover(self, fun_ex, executor=None):
        p = Promise(self._executor)
        self.on_success(p.success)
        self.on_failure(lambda ex: p.complete(fun_ex, ex), executor=executor)
        return p.future

    def map(self, fun_res, executor=None):
        assert (callable(fun_res))

        p = Promise(self._executor)
        self.on_success(lambda res: p.complete(fun_res, res), executor=executor)
        self.on_failure(p.failure)
        return p.future

    def then(self, future_fun, executor=None):
        assert (callable(future_fun))

        p = Promise(self._executor)

        def start_next(_):
            try:
                f = future_fun()
                f.on_success(p.success)
                f.on_failure(p.failure)
            except Exception as ex:
                p.failure(ex)

        self.on_success(start_next, executor=executor)
        self.on_failure(p.failure)
        return p.future

    def fallback(self, future_fun, executor=None):
        assert (callable(future_fun))

        p = Promise(self._executor)

        def start_fallback(_):
            try:
                f = future_fun()
                f.on_success(p.success)
                f.on_failure(p.failure)
            except Exception as ex:
                p.failure(ex)

        self.on_success(p.success)
        self.on_failure(start_fallback, executor=executor)
        return p.future

    class comb_ctx(object):
        def __init__(self):
            self.lock = Lock()
            self.results = None
            self.left = 0

    @staticmethod
    def all(futures, clb_executor=None):
        if not futures:
            return Future.successful([], clb_executor)

        p = Promise(clb_executor)
        ctx = Future.comb_ctx()
        ctx.results = [None] * len(futures)
        ctx.left = len(futures)

        def done(i, res):
            with ctx.lock:
                ctx.results[i] = res
                ctx.left -= 1
                if not ctx.left:
                    p.success(ctx.results)

        for i, f in enumerate(futures):
            f.on_success(functools.partial(done, i))
            f.on_failure(p.failure)

        return p.future

    @staticmethod
    def first(futures, clb_executor=None):
        if not futures:
            raise TypeError("Future.first() got empty sequence")

        p = Promise(clb_executor)
        for f in futures:
            f.on_success(p.try_success)
            f.on_failure(p.try_failure)
        return p.future

    @staticmethod
    def first_successful(futures, clb_executor=None):
        if not futures:
            raise TypeError("Future.first_successful() got empty sequence")

        p = Promise(clb_executor)
        ctx = Future.comb_ctx()
        ctx.left = len(futures)

        def on_fail(ex):
            with ctx.lock:
                ctx.left -= 1
                if not ctx.left:
                    p.failure(ex)

        for f in futures:
            f.on_success(p.success)
            f.on_failure(on_fail)

        return p.future

    @staticmethod
    def reduce(fun, futures, *vargs, executor=None, clb_executor=None):
        return Future \
            .all(futures, clb_executor=clb_executor) \
            .map(lambda results: functools.reduce(fun, results, *vargs), executor=executor)

    @staticmethod
    def from_concurrent_future(cf, clb_executor=None):
        class CFuture(Future):
            def __init__(self, cf, clb_executor=None):
                Future.__init__(self, clb_executor)
                self.cf = cf
                self.cf.add_done_callback(self._complete)

            def cancel(self):
                Future.cancel(self)
                self.cf.cancel()

            def _complete(self, f):
                try:
                    self._success(f.result())
                except Exception as ex:
                    self._failure(ex)

        return CFuture(cf, clb_executor)


class Promise(object):
    def __init__(self, clb_executor=None):
        self._future = Future(clb_executor)

    def complete(self, fun, *vargs, **kwargs):
        try:
            self.success(fun(*vargs, **kwargs))
        except Exception as ex:
            self.failure(ex)

    def success(self, result):
        self._future._success(result)

    def try_success(self, result):
        return self._future._try_success(result)

    def failure(self, exception):
        self._future._failure(exception)

    def try_failure(self, exception):
        self._future._try_failure(exception)

    @property
    def is_completed(self):
        return self._future.is_completed

    @property
    def is_cancelled(self):
        return self._future.is_cancelled

    @property
    def future(self):
        return self._future


class SynchronousExecutor(object):
    @staticmethod
    def execute(fn, *args, **kwargs):
        try:
            return Future.successful(fn(*args, **kwargs))
        except Exception as ex:
            return Future.failed(ex)

# alias
Synchronous = SynchronousExecutor