from threading import Condition


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
            return True

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
