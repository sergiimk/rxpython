from .future import Future


class Promise(object):
    def __init__(self, clb_executor=None):
        self._future = Future(clb_executor)

    def success(self, result):
        self._future._success(result)

    def try_success(self, result):
        return self._future._try_success(result)

    def failure(self, exception):
        self._future._failure(exception)

    def try_failure(self, exception):
        self._future._try_failure(exception)

    def complete(self, fun, *vargs, **kwargs):
        self._future._complete(fun, *vargs, **kwargs)

    def try_complete(self, fun, *vargs, **kwargs):
        return self._future._try_complete(fun, *vargs, **kwargs)

    @property
    def is_completed(self):
        return self._future.is_completed

    @property
    def is_cancelled(self):
        return self._future.is_cancelled

    @property
    def future(self):
        return self._future
