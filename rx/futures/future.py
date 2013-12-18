from threading import Condition, Lock
import functools
import logging


class IllegalStateError(Exception):
    pass


class FutureState(object):
    in_progress = 0
    success = 1
    failure = -1


#TODO: thread validation
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
    def __init__(self):
        FutureBaseState.__init__(self)
        self._success_clb = []
        self._failure_clb = []

    #thread: any
    def on_success(self, clb, *vargs, **kwargs):
        assert(callable(clb))
        nclb = functools.partial(clb, *vargs, **kwargs)
        with self._mutex:
            if self._state == FutureState.success:
                self._run_callback(nclb)
            elif not self._state:
                self._success_clb.append(nclb)

    #thread: any
    def on_failure(self, clb, *vargs, **kwargs):
        assert(callable(clb))
        nclb = functools.partial(clb, *vargs, **kwargs)
        with self._mutex:
            if self._state == FutureState.failure:
                self._run_callback(nclb)
            elif not self._state:
                self._failure_clb.append(nclb)

    #thread: executor
    #override
    def _on_result_set(self):
        success = self._state == FutureState.success
        callbacks = self._success_clb if success else self._failure_clb

        self._success_clb = None
        self._failure_clb = None

        for clb in callbacks:
            self._run_callback(clb)

    #thread: executor
    #TODO: executor
    #TODO: exceptions
    def _run_callback(self, clb):
        try:
            clb(self._value)
        except:
            log = logging.getLogger(__name__)
            log.exception()


class Future(FutureBaseCallbacks):
    def __init__(self):
        FutureBaseCallbacks.__init__(self)

    @staticmethod
    def successful(result=None):
        f = Future()
        f._success(result)
        return f

    @staticmethod
    def failed(exception):
        f = Future()
        f._failure(exception)
        return f

    def recover(self, fun_ex):
        from .promise import Promise
        p = Promise()
        self.on_success(p.success)
        self.on_failure(p.complete, fun_ex)
        return p.future

    #TODO: executor
    def map(self, fun_res):
        assert(callable(fun_res))
        from .promise import Promise

        p = Promise()
        self.on_success(p.complete, fun_res)
        self.on_failure(p.failure)
        return p.future

    #TODO: executor
    def then(self, future_fun, *vargs, **kargs):
        assert(callable(future_fun))
        from .promise import Promise

        p = Promise()

        def start_next(_):
            try:
                f = future_fun(*vargs, **kargs)
                f.on_success(p.success)
                f.on_failure(p.failure)
            except Exception as ex:
                p.failure(ex)

        self.on_success(start_next)
        self.on_failure(p.failure)
        return p.future

    class all_ctx(object):
        def __init__(self, futures):
            self.lock = Lock()
            self.results = [None] * len(futures)
            self.left = len(futures)

    @staticmethod
    def all(futures):
        from .promise import Promise

        p = Promise()
        if not futures:
            p.success([])
            return p.future

        ctx = Future.all_ctx(futures)

        def done(i, res):
            with ctx.lock:
                ctx.results[i] = res
                ctx.left -= 1
                if not ctx.left:
                    p.success(ctx.results)

        for i, f in enumerate(futures):
            f.on_success(done, i)
            f.on_failure(p.failure)

        return p.future

    @staticmethod
    def first(futures):
        from .promise import Promise
        p = Promise()
        for f in futures:
            f.on_success(p.try_success)
            f.on_failure(p.try_failure)
        return p.future

    @staticmethod
    def reduce(fun, futures, *vargs):
        return Future.all(futures) \
            .map(lambda results: functools.reduce(fun, results, *vargs))
