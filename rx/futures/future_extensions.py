from .future_core import FutureBase
from threading import Lock
import functools


class FutureExtensions(object):
    """Mixin class for Future combination functions."""

    def recover(self, fun_ex, executor=None):
        """Returns future that will contain result of original if it
        completes successfully, or set from result of provided function in
        case of failure.

        Args:
            fun_ex: function that accepts Exception parameter.
            executor: Executor to use when performing call to function (default - Synchronous).
        """
        return self._recover(self, fun_ex, executor)

    @classmethod
    def _recover(cls, self, fun_ex, executor=None):
        assert callable(fun_ex), "Future.recover expects callable"
        f = cls(self._executor)
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
        return self._map(self, fun_res, executor)

    @classmethod
    def _map(cls, self, fun_res, executor=None):
        assert callable(fun_res), "Future.map expects callable"
        f = cls(self._executor)
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
        return self._then(self, future_fun, executor)

    @classmethod
    def _then(cls, self, future_fun, executor=None):
        assert callable(future_fun), "Future.then expects callable"

        f = cls(self._executor)

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
        return self._fallback(self, future_fun, executor)

    @classmethod
    def _fallback(cls, self, future_fun, executor=None):
        assert callable(future_fun), "Future.fallback expects callable"

        f = cls(self._executor)

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

    @classmethod
    def all(cls, futures, clb_executor=None):
        """Transforms list of futures into one future that will contain list of results.
        In case of any failure future will be failed with first exception to occur.

        Args:
            futures: list of futures to combine.
            clb_executor: default executor to use when running new future's
            callbacks (default - Synchronous).
        """
        if not futures:
            return cls.successful([], clb_executor)

        f = cls(clb_executor)
        ctx = FutureExtensions.comb_ctx()
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

    @classmethod
    def first(cls, futures, clb_executor=None):
        """Returns future which will be set from result of first future to complete,
        both successfully or with failure.

        Args:
            futures: list of futures to combine.
            clb_executor: default executor to use when running new future's
            callbacks (default - Synchronous).
        """
        if not futures:
            raise TypeError("Future.first() got empty sequence")

        f = cls(clb_executor)
        for fi in futures:
            fi.on_success(f._try_success)
            fi.on_failure(f._try_failure)

        return f

    @classmethod
    def first_successful(cls, futures, clb_executor=None):
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

        f = cls(clb_executor)
        ctx = FutureExtensions.comb_ctx()
        ctx.left = len(futures)

        def on_fail(ex):
            with ctx.lock:
                ctx.left -= 1
                if not ctx.left:
                    f._failure(ex)

        for fi in futures:
            fi.on_success(f._try_success)
            fi.on_failure(on_fail)

        return f

    @classmethod
    def reduce(cls, futures, fun, initial, executor=None, clb_executor=None):
        """Returns future which will be set with reduced result of all provided futures.
        In case of any failure future will be failed with first exception to occur.

        Args:
            futures: list of futures to combine.
            fun: reduce-compatible function.
            executor: Executor to use when performing call to function (default - Synchronous).
            clb_executor: default executor to use when running new future's
            callbacks (default - Synchronous).
        """
        return cls \
            .all(futures, clb_executor=clb_executor) \
            .map(lambda results: functools.reduce(fun, results, initial), executor=executor)

    @classmethod
    def from_concurrent_future(cls, cf, clb_executor=None):
        f = cls(clb_executor)
        cf.add_done_callback(lambda cf: f._complete(cf.result))
        orig_cancel = f.cancel

        def cancel():
            orig_cancel()
            cf.cancel()

        f.cancel = cancel
        return f
