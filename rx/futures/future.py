from threading import Condition
import functools
import logging


class IllegalStateError(Exception):
    pass


#TODO: thread validation
class FutureBase(object):

    class State(object):
        in_progress = 0
        success = 1
        failure = -1

    def __init__(self):
        self._mutex = Condition()
        self._state = FutureBase.State.in_progress
        self._value = None

    #thread: executor
    def _success(self, result):
        if not self._try_success(result):
            raise IllegalStateError("result was already set")

    #thread: executor
    def _try_success(self, result):
        return self._try_set_result(FutureBase.State.success, result)

    #thread: executor
    def _failure(self, exception):
        if not self._try_failure(exception):
            raise IllegalStateError("result was already set")

    #thread: executor
    def _try_failure(self, exception):
        assert(isinstance(exception, BaseException))
        return self._try_set_result(FutureBase.State.failure, exception)

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
            return self._state != FutureBase.State.in_progress

    #thread: any
    def wait(self, timeout=None):
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            return self._state != FutureBase.State.in_progress

    #thread: any
    def result(self, timeout=None):
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            if not self._state:
                raise TimeoutError()
            if self._state == FutureBase.State.failure:
                raise self._value
            return self._value


class Future(FutureBase):
    def __init__(self):
        FutureBase.__init__(self)
        self._success_clb = []
        self._failure_clb = []

    #thread: any
    def on_success(self, clb):
        assert(callable(clb))
        with self._mutex:
            if self._state == FutureBase.State.success:
                self._run_callback(clb)
            elif not self._state:
                self._success_clb.append(clb)

    #thread: any
    def on_failure(self, clb):
        assert(callable(clb))
        with self._mutex:
            if self._state == FutureBase.State.failure:
                self._run_callback(clb)
            elif not self._state:
                self._failure_clb.append(clb)

    #thread: any
    #TODO: executor
    def map(self, f):
        assert(callable(f))
        from .promise import Promise

        p = Promise()
        self.on_success(lambda res: p.complete(functools.partial(f, res)))
        self.on_failure(lambda ex: p.failure(ex))
        return p.future

    #thread: executor
    #override
    def _on_result_set(self):
        success = self._state == FutureBase.State.success
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
