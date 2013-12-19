from .execution_context import Synchronous
from threading import Condition, Lock
import functools


class IllegalStateError(Exception):
    pass


class FutureState(object):
    in_progress = 0
    success = 1
    failure = -1


#TODO: thread validation
#TODO: tracing
class FutureBaseState(object):
    def __init__(self):
        self._mutex = Condition()
        self._state = FutureState.in_progress
        self._value = None

    #thread: executor
    def _success(self, result):
        if not self._try_success(result):
            raise IllegalStateError("result was already set")

    #thread: executor
    def _try_success(self, result):
        return self._try_set_result(FutureState.success, result)

    #thread: executor
    def _failure(self, exception):
        if not self._try_failure(exception):
            raise IllegalStateError("result was already set")

    #thread: executor
    def _try_failure(self, exception):
        assert(isinstance(exception, BaseException))
        return self._try_set_result(FutureState.failure, exception)

    #thread executor
    def _try_set_result(self, state, value):
        with self._mutex:
            if self._state:
                return False
            self._state = state
            self._value = value
            self._mutex.notify_all()
            self._on_result_set()
            return True

    #thread executor
    #virtual
    def _on_result_set(self):
        pass

    #thread: any
    @property
    def is_completed(self):
        with self._mutex:
            return self._state != FutureState.in_progress

    #thread: any
    def wait(self, timeout=None):
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            return self._state != FutureState.in_progress

    #thread: any
    def result(self, timeout=None):
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            if not self._state:
                raise TimeoutError()
            if self._state == FutureState.failure:
                raise self._value
            return self._value


class FutureBaseCallbacks(FutureBaseState):
    def __init__(self, clb_executor=None):
        FutureBaseState.__init__(self)
        self._executor = clb_executor or Synchronous
        self._success_clb = []
        self._failure_clb = []

    #thread: any
    def on_success(self, fun_res, executor=None):
        assert(callable(fun_res))
        with self._mutex:
            if self._state == FutureState.success:
                self._run_callback(fun_res, executor)
            elif not self._state:
                self._success_clb.append((fun_res, executor))

    #thread: any
    def on_failure(self, fun_ex, executor=None):
        assert(callable(fun_ex))
        with self._mutex:
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
        exc.execute(clb, self._value)


class FutureMetaSubscriptable(type):
    def __getitem__(cls, executor, clb_executor=None):
        def apply(fn, *args, **kwargs):
            p = Promise(clb_executor)
            executor.execute(p.complete, fn, *args, **kwargs)
            return p.future

        return apply


class Future(FutureBaseCallbacks, metaclass=FutureMetaSubscriptable):
    def __init__(self, clb_executor=None):
        FutureBaseCallbacks.__init__(self, clb_executor)

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
        assert(callable(fun_res))

        p = Promise(self._executor)
        self.on_success(lambda res: p.complete(fun_res, res), executor=executor)
        self.on_failure(p.failure)
        return p.future

    def then(self, future_fun, executor=None):
        assert(callable(future_fun))

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
        assert(callable(future_fun))

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
        p = Promise(clb_executor)
        cf.add_done_callback(lambda f: p.complete(f.result))
        return p.future


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
    def future(self):
        return self._future
