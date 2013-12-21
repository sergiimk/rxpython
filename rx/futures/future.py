from .future_core import FutureBase
from .future_callbacks import (FutureCoreCallbacks,
                               FutureCoreCallbacksSuccess,
                               FutureCoreCallbacksFailure)

from threading import Lock
import functools


class Future(FutureCoreCallbacks):
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
    def completed(fun, *args, clb_executor=None):
        """Returns successful or failed future set from provided function."""
        try:
            return FutureSuccess(fun(*args), clb_executor)
        except Exception as ex:
            return FutureFailure(ex, clb_executor)

    def recover(self, fun_ex, executor=None):
        """Returns future that will contain result of original if it
        completes successfully, or set from result of provided function in
        case of failure.

        Args:
            fun_ex: function that accepts Exception parameter.
            executor: Executor to use when performing call to function (default - Synchronous).
        """
        f = Future(self._executor)
        self.on_success(f._success)
        self.on_failure(lambda ex: f._complete(fun_ex, ex), executor=executor)
        return f

    def map(self, fun_res, executor=None):
        """Returns future which will be set from result of applying provided function
        to original future value.

        Args:
            fun_res: function that accepts original result and returns new value.
            executor: Executor to use when performing call to function (default - Synchronous).
        """
        assert callable(fun_res), "Future.map expects callable"

        f = Future(self._executor)
        self.on_success(lambda res: f._complete(fun_res, res), executor=executor)
        self.on_failure(f._failure)
        return f

    def then(self, future_fun, executor=None):
        """Returns future which represents two futures chained one after another.
        Failures are propagated from first future, from second future and from callback function.

        Args:
            future_fun: function that returns future to be chained after successful
            completion of first one (or Future instance directly).
            executor: Executor to use when performing call to function (default - Synchronous).
        """
        assert callable(future_fun), "Future.then expects callable"

        f = Future(self._executor)

        def start_next(_):
            try:
                f2 = future_fun if isinstance(future_fun, FutureBase) else future_fun()
                f2.on_success(f._success)
                f2.on_failure(f._failure)
            except Exception as ex:
                f._failure(ex)

        self.on_success(start_next, executor=executor)
        self.on_failure(f._failure)
        return f

    def fallback(self, future_fun, executor=None):
        """Returns future that will contain result of original if it completes
        successfully, or will be set from future returned from provided
        function in case of failure.

        Args:
            future_fun: function that returns future to be used for fallback
            (or Future instance directly).
            executor: Executor to use when performing call to function (default - Synchronous).
        """
        assert callable(future_fun), "Future.fallback expects callable"

        f = Future(self._executor)

        def start_fallback(_):
            try:
                f2 = future_fun if isinstance(future_fun, FutureBase) else future_fun()
                f2.on_success(f._success)
                f2.on_failure(f._failure)
            except Exception as ex:
                f._failure(ex)

        self.on_success(f._success)
        self.on_failure(start_fallback, executor=executor)
        return f

    class comb_ctx(object):
        def __init__(self):
            self.lock = Lock()
            self.results = None
            self.left = 0

    @staticmethod
    def all(futures, clb_executor=None):
        """Transforms list of futures into one future that will contain list of results.
        In case of any failure future will be failed with first exception to occur.

        Args:
            futures: list of futures to combine.
            clb_executor: default executor to use when running new future's
            callbacks (default - Synchronous).
        """
        if not futures:
            return Future.successful([], clb_executor)

        f = Future(clb_executor)
        ctx = Future.comb_ctx()
        ctx.results = [None] * len(futures)
        ctx.left = len(futures)

        def done(i, res):
            with ctx.lock:
                ctx.results[i] = res
                ctx.left -= 1
                if not ctx.left:
                    f._success(ctx.results)

        for i, fi in enumerate(futures):
            fi.on_success(functools.partial(done, i))
            fi.on_failure(f._failure)

        return f

    @staticmethod
    def first(futures, clb_executor=None):
        """Returns future which will be set from result of first future to complete,
        both successfully or with failure.

        Args:
            futures: list of futures to combine.
            clb_executor: default executor to use when running new future's
            callbacks (default - Synchronous).
        """
        if not futures:
            raise TypeError("Future.first() got empty sequence")

        f = Future(clb_executor)
        for fi in futures:
            fi.on_success(f._try_success)
            fi.on_failure(f._try_failure)

        return f

    @staticmethod
    def first_successful(futures, clb_executor=None):
        """Returns future which will be set from result of first future to
        complete successfully, last detected error will be set in case
        when all of the provided future fail.

        Args:
            futures: list of futures to combine.
            clb_executor: default executor to use when running new future's
            callbacks (default - Synchronous).
        """
        if not futures:
            raise TypeError("Future.first_successful() got empty sequence")

        f = Future(clb_executor)
        ctx = Future.comb_ctx()
        ctx.left = len(futures)

        def on_fail(ex):
            with ctx.lock:
                ctx.left -= 1
                if not ctx.left:
                    f._failure(ex)

        for fi in futures:
            fi.on_success(f._success)
            fi.on_failure(on_fail)

        return f

    @staticmethod
    def reduce(futures, fun, *vargs, executor=None, clb_executor=None):
        """Returns future which will be set with reduced result of all provided futures.
        In case of any failure future will be failed with first exception to occur.

        Args:
            futures: list of futures to combine.
            fun: reduce-compatible function.
            executor: Executor to use when performing call to function (default - Synchronous).
            clb_executor: default executor to use when running new future's
            callbacks (default - Synchronous).
        """
        return Future \
            .all(futures, clb_executor=clb_executor) \
            .map(lambda results: functools.reduce(fun, results, *vargs), executor=executor)

    @staticmethod
    def from_concurrent_future(cf, clb_executor=None):
        class CFuture(Future):
            def __init__(self, cf, clb_executor=None):
                Future.__init__(self, clb_executor)
                self.cf = cf
                self.cf.add_done_callback(self._cf_complete)

            def cancel(self):
                Future.cancel(self)
                self.cf.cancel()

            def _cf_complete(self, f):
                self._complete(f.result)

        return CFuture(cf, clb_executor)


class FutureSuccess(FutureCoreCallbacksSuccess):
    """Lightweight class representing successfully completed future, enabling many optimizations.."""

    def recover(self, fun_ex, executor=None):
        return self

    def map(self, fun_res, executor=None):
        return Future.map(self, fun_res, executor=executor)

    def then(self, future_fun, executor=None):
        return Future.then(self, future_fun, executor=executor)

    def fallback(self, future_fun, executor=None):
        return self


class FutureFailure(FutureCoreCallbacksFailure):
    """Lightweight class representing failed future, enabling many optimizations."""

    def recover(self, fun_ex, executor=None):
        return Future.recover(self, fun_ex, executor=executor)

    def map(self, fun_res, executor=None):
        return self

    def then(self, future_fun, executor=None):
        return self

    def fallback(self, future_fun, executor=None):
        return Future.fallback(self, future_fun, executor=executor)
