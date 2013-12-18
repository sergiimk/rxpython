from .future import Future


class Promise(object):
    def __init__(self):
        self._future = Future()

    def complete(self, fun):
        try:
            self.success(fun())
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
