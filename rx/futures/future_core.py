from .config import ON_UNHANDLED_FAILURE
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
                ON_UNHANDLED_FAILURE(self._value)

    def _success(self, result):
        if not self._try_success(result):
            raise IllegalStateError("result was already set")

    def _try_success(self, result):
        return self._try_set_result(FutureState.success, result)

    def _failure(self, exception):
        if not self._try_failure(exception):
            raise IllegalStateError("result was already set")

    def _try_failure(self, exception):
        assert isinstance(exception, Exception), "Promise.failure expects Exception instance"
        return self._try_set_result(FutureState.failure, exception)

    def _complete(self, fun, *vargs, **kwargs):
        if not self._try_complete(fun, *vargs, **kwargs):
            raise IllegalStateError("result was already set")

    def _try_complete(self, fun, *vargs, **kwargs):
        try:
            return self._try_success(fun(*vargs, **kwargs))
        except Exception as ex:
            return self._try_failure(ex)

    def _try_set_result(self, state, value):
        with self._mutex:
            if self._state:
                return False
            self._state = state
            self._value = value
            self._mutex.notify_all()
            self._on_result_set()
            return True

    #virtual
    def _on_result_set(self):
        pass

    @property
    def is_completed(self):
        with self._mutex:
            return self._state != FutureState.in_progress

    @property
    def is_cancelled(self):
        with self._mutex:
            return self._cancel

    def cancel(self):
        with self._mutex:
            self._cancel = True

    def wait(self, timeout=None):
        with self._mutex:
            if not self._state:
                self._mutex.wait(timeout)
            return self._state != FutureState.in_progress

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


class FutureCoreCompleted(object):
    def __init__(self, value):
        self._value = value
        self.is_completed = True
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def wait(self, timeout=None):
        return True


class FutureCoreSuccess(FutureCoreCompleted):
    def result(self, timeout=None):
        return self._value


class FutureCoreFailure(FutureCoreCompleted):
    def result(self, timeout=None):
        raise self._value
