from threading import Lock


class IllegalStateError(Exception):
    pass


#TODO: thread validation
class FutureBase(object):
    def __init__(self):
        self._mutex = Lock()
        self._completed = 0
        self._result = None
        self._exception = None

    #thread: executioner
    def _success(self, result):
        if not self._try_success(result):
            raise IllegalStateError("result was already set")

    #thread: executioner
    def _try_success(self, result):
        with self._mutex:
            if self._completed:
                return False
            self._completed = 1
            self._result = result
            return True

    #thread: executioner
    def _failure(self, exception):
        if not self._try_failure(exception):
            raise IllegalStateError("result was already set")

    #thread: executioner
    def _try_failure(self, exception):
        assert(isinstance(exception, BaseException))
        with self._mutex:
            if self._completed:
                return False
            self._completed = -1
            self._exception = exception
            return True

    #thread: any
    @property
    def is_completed(self):
        with self._mutex:
            return self._completed != 0

    #thread: any
    #TODO: timeout
    def result(self, timeout=None):
        with self._mutex:
            if not self._completed:
                raise TimeoutError()
            if self._completed < 0:
                raise self._exception
            return self._result


class Future(FutureBase):
    def __init__(self):
        FutureBase.__init__(self)
