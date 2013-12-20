from .config import on_unhandled_failure
from threading import Condition


class IllegalStateError(Exception):
    pass


class FutureState(object):
    in_progress = 0
    success = 1
    failure = -1


class FutureCore(object):
    def __init__(self):
        self._mutex = Condition()
        self._state = FutureState.in_progress
        self._value = None
        self._cancel = False
        self._failure_handled = False

    def __del__(self):
        with self._mutex:
            if self._state == FutureState.failure and not self._failure_handled:
                on_unhandled_failure(self._value)

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
        assert (isinstance(exception, BaseException))
        return self._try_set_result(FutureState.failure, exception)

    #thread: executor
    def _complete(self, fun, *vargs, **kwargs):
        if not self._try_complete(fun, *vargs, **kwargs):
            raise IllegalStateError("result was already set")

    #thread: executor
    def _try_complete(self, fun, *vargs, **kwargs):
        try:
            return self._try_success(fun(*vargs, **kwargs))
        except Exception as ex:
            return self._try_failure(ex)

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
    @property
    def is_cancelled(self):
        with self._mutex:
            return self._cancel

    #thread: any
    def cancel(self):
        with self._mutex:
            self._cancel = True

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
                self._failure_handled = True
                raise self._value
            return self._value
