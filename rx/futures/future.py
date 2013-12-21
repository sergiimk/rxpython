from .future_extensions import FutureExtensions
from .future_callbacks import (FutureCoreCallbacks,
                               FutureCoreCallbacksSuccess,
                               FutureCoreCallbacksFailure)


class Future(FutureCoreCallbacks, FutureExtensions):
    """Client-facing object returned by systems which expose
    asynchronous APIs. Main way to interact with Future is to
    use callbacks and combination methods to chain computations
    on top of result that is yet to be returned.
    """

    @staticmethod
    def successful(result=None, clb_executor=None):
        """Returns successfully completed future.

        Args:
            result: value to complete future with.
            clb_executor: default Executor to use for running callbacks (default - Synchronous).
        """
        return FutureSuccess(result, clb_executor)

    @staticmethod
    def failed(exception, clb_executor=None):
        """Returns failed future.

        Args:
            exception: Exception to set to future.
            clb_executor: default Executor to use for running callbacks (default - Synchronous).
        """
        return FutureFailure(exception, clb_executor)

    @staticmethod
    def completed(fun, clb_executor=None):
        """Returns successful or failed future set from provided function."""
        try:
            return FutureSuccess(fun(), clb_executor)
        except Exception as ex:
            return FutureFailure(ex, clb_executor)


class FutureSuccess(FutureCoreCallbacksSuccess, FutureExtensions):
    """Lightweight class representing successfully completed future, enabling many optimizations."""

    def recover(self, fun_ex, executor=None):
        return self

    def map(self, fun_res, executor=None):
        return Future._map(self, fun_res, executor=executor)

    def then(self, future_fun, executor=None):
        return Future._then(self, future_fun, executor=executor)

    def fallback(self, future_fun, executor=None):
        return self


class FutureFailure(FutureCoreCallbacksFailure, FutureExtensions):
    """Lightweight class representing failed future, enabling many optimizations."""

    def recover(self, fun_ex, executor=None):
        return Future._recover(self, fun_ex, executor=executor)

    def map(self, fun_res, executor=None):
        return self

    def then(self, future_fun, executor=None):
        return self

    def fallback(self, future_fun, executor=None):
        return Future._fallback(self, future_fun, executor=executor)
