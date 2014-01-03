from .future_base import FutureBase, CancelledError
from threading import Lock
import functools


class FutureBaseExt(FutureBase):
    """ABC for Future combination functions."""

    @classmethod
    def successful(cls, result=None, *, clb_executor=None):
        """Returns successfully completed future.

        Args:
            result: value to complete future with.
            clb_executor: default Executor to use for running callbacks (default - Synchronous).
        """
        f = cls._new(clb_executor=clb_executor)
        f.set_result(result)
        return f

    @classmethod
    def failed(cls, exception, *, clb_executor=None):
        """Returns failed future.

        Args:
            exception: Exception to set to future.
            clb_executor: default Executor to use for running callbacks (default - Synchronous).
        """
        f = cls._new(clb_executor=clb_executor)
        f.set_exception(exception)
        return f

    @classmethod
    def completed(cls, fun, *args, clb_executor=None, **kwargs):
        """Returns successful or failed future set from provided function."""
        f = cls._new(clb_executor=clb_executor)
        try:
            f.set_result(fun(*args, **kwargs))
        except Exception as ex:
            f.set_exception(ex)
        return f

    def complete(self, fun, *args, **kwargs):
        try:
            self.set_result(fun(*args, **kwargs))
        except Exception as ex:
            self.set_exception(ex)

    def recover(self, fun_ex_or_value, *, executor=None):
        """Returns future that will contain result of original if it
        completes successfully, or set from result of provided function in
        case of failure.

        New future inherits default callback executor from original future.
        Propagates exceptions from function as well as cancellation.

        Args:
            fun_ex_or_value: function that accepts Exception parameter or
            just value to use in error case.
            executor: Executor to use when performing call to function.
        """
        f = self._new()

        def on_done_recover(fut):
            if fut.cancelled():
                f.cancel()
            if fut.exception() is None:
                f.set_result(fut.result())
            elif callable(fun_ex_or_value):
                f.complete(fun_ex_or_value, fut.exception())
            else:
                f.set_result(fun_ex_or_value)

        def backprop_cancel(fut):
            if fut.cancelled():
                self.cancel()

        self.add_done_callback(on_done_recover, executor=executor)
        f.add_done_callback(backprop_cancel)
        return f

    def map(self, fun_res, *, executor=None):
        """Returns future which will be set from result of applying provided function
        to original future value.

        New future inherits default callback executor from original future.
        Propagates exceptions from function as well as cancellation.

        Args:
            fun_res: function that accepts original result and returns new value.
            executor: Executor to use when performing call to function (default - Synchronous).
        """
        assert callable(fun_res), "Future.map expects callable"
        f = self._new()

        def on_done_map(fut):
            if fut.cancelled():
                f.cancel()
            elif fut.exception() is None:
                f.complete(fun_res, fut.result())
            else:
                f.set_exception(fut.exception())

        def backprop_cancel(fut):
            if fut.cancelled():
                self.cancel()

        self.add_done_callback(on_done_map, executor=executor)
        f.add_done_callback(backprop_cancel)
        return f

    def then(self, future_fun, *, executor=None):
        """Returns future which represents two futures chained one after another.
        Failures are propagated from first future, from second future and from callback function.
        Cancellation is propagated both ways.

        Args:
            future_fun: either function that returns future to be chained after successful
            completion of first one, or Future instance directly.
            executor: Executor to use when performing call to function (default - Synchronous).
        """
        assert callable(future_fun) or isinstance(future_fun, FutureBase), "Future.then expects callable or Future"

        f = self._new()

        def on_done_start_next(fut):
            if fut.cancelled():
                f.cancel()
            elif fut.exception() is None:
                try:
                    f2_raw = future_fun if isinstance(future_fun, FutureBase) else future_fun()
                    f2 = self.convert(f2_raw)
                    self.compatible([self, f2])
                    f2.add_done_callback(f.set_from)
                except Exception as ex:
                    f.set_exception(ex)
            else:
                f.set_exception(fut.exception())

        def backprop_cancel(fut):
            if fut.cancelled():
                self.cancel()

        self.add_done_callback(on_done_start_next, executor=executor)
        f.add_done_callback(backprop_cancel)
        return f

    def fallback(self, future_fun, *, executor=None):
        """Returns future that will contain result of original if it completes
        successfully, or will be set from future returned from provided
        function in case of failure. Provided function is called only if original
        future fails. Cancellation is propagated both ways.

        Args:
            future_fun: either function that returns future to be used for
            fallback, or Future instance directly.
            executor: Executor to use when performing call to function.
        """
        assert callable(future_fun) or isinstance(future_fun, FutureBase), "Future.fallback expects callable or Future"

        f = self._new()

        def on_done_start_fallback(fut):
            if fut.cancelled():
                f.cancel()
            elif fut.exception() is not None:
                try:
                    f2_raw = future_fun if isinstance(future_fun, FutureBase) else future_fun()
                    f2 = self.convert(f2_raw)
                    self.compatible([self, f2])

                    def backprop_cancel_fallback(fut):
                        if fut.cancelled():
                            f2.cancel()

                    f2.add_done_callback(f.set_from)
                    f.add_done_callback(backprop_cancel_fallback)
                except Exception as ex:
                    f.set_exception(ex)
            else:
                f.set_result(fut.result())

        def backprop_cancel_orig(fut):
            if fut.cancelled():
                self.cancel()

        self.add_done_callback(on_done_start_fallback, executor=executor)
        f.add_done_callback(backprop_cancel_orig)
        return f

    @classmethod
    def gather(cls, futures, *, return_exceptions=False, clb_executor=None):
        """Return a future aggregating results from the given futures.

        If all futures are completed successfully, the returned future’s result is
        the list of results (in the order of the original sequence, not necessarily
        in the order of future completion). If return_exceptions is True, exceptions
        in the tasks are treated the same as successful results, and gathered in the
        result list; otherwise, the first raised exception will be immediately
        propagated to the returned future.

        Cancellation: if the outer Future is cancelled, all children that have not
        completed yet are also cancelled. If any child is cancelled, this is treated
        as if it raised CancelledError – the outer Future is not cancelled in this case
        (this is to prevent the cancellation of one child to cause other children to be
        cancelled).

        Args:
            futures: list of futures to combine.
            return_exceptions: treat exceptions as successful results
            clb_executor: default executor to use when running new future's callbacks.
        """
        if not futures:
            return cls.successful([], clb_executor=clb_executor)

        futures = list(map(cls.convert, futures))
        cls.compatible(futures)
        f = cls._new(clb_executor=clb_executor)

        lock = Lock()
        results = [None] * len(futures)
        left = len(futures)

        def done(i, fut):
            nonlocal left
            exc = CancelledError() if fut.cancelled() else fut.exception()
            if exc is not None and not return_exceptions:
                f.set_exception(exc)
            else:
                with lock:
                    results[i] = exc if exc is not None else fut.result()
                    left -= 1
                    if not left:
                        f.set_result(results)

        def backprop_cancel(fut):
            if fut.cancelled():
                for fi in futures:
                    fi.cancel()

        for i, fi in enumerate(futures):
            fi.add_done_callback(functools.partial(done, i))

        f.add_done_callback(backprop_cancel)
        return f

    @classmethod
    def first(cls, futures, *, clb_executor=None):
        """Returns future which will be set from result of first future to complete,
        both successfully or with failure. Cancellation is propagated both ways - if
        aggregate future is cancelled it will cancel all child futures.

        Args:
            futures: list of futures to combine.
            clb_executor: default executor to use when running new future's callbacks.
        """
        if not futures:
            raise TypeError("Future.first() got empty sequence")

        futures = list(map(cls.convert, futures))
        cls.compatible(futures)
        f = cls._new(clb_executor=clb_executor)

        for fi in futures:
            fi.add_done_callback(f.try_set_from)

        def backprop_cancel(fut):
            if fut.cancelled():
                for fi in futures:
                    fi.cancel()

        f.add_done_callback(backprop_cancel)
        return f

    @classmethod
    def first_successful(cls, futures, *, clb_executor=None):
        """Returns future which will be set from result of first future to
        complete successfully, last detected error will be set in case
        when all of the provided future fail. In case of cancelling aggregate
        future all child futures will be cancelled. Only cancellation of all
        child future triggers cancellation of aggregate future.

        Args:
            futures: list of futures to combine.
            clb_executor: default executor to use when running new future's callbacks.
        """
        if not futures:
            raise TypeError("Future.first_successful() got empty sequence")

        futures = list(map(cls.convert, futures))
        cls.compatible(futures)
        f = cls._new(clb_executor=clb_executor)

        lock = Lock()
        left = len(futures)

        def on_done(fut):
            nonlocal left
            if not fut.cancelled() and fut.exception() is None:
                f.try_set_result(fut.result())
            else:
                with lock:
                    left -= 1
                    if not left:
                        f.set_from(fut)

        for fi in futures:
            fi.add_done_callback(on_done)

        def backprop_cancel(fut):
            if fut.cancelled():
                for fi in futures:
                    fi.cancel()

        f.add_done_callback(backprop_cancel)
        return f

    @classmethod
    def reduce(cls, futures, fun, initial, *, executor=None, clb_executor=None):
        """Returns future which will be set with reduced result of all provided futures.
        In case of any failure future will be failed with first exception to occur.

        Cancellation: if the outer Future is cancelled, all children that have not
        completed yet are also cancelled. If any child is cancelled, this is treated
        as if it raised CancelledError – the outer Future is not cancelled in this case
        (this is to prevent the cancellation of one child to cause other children to be
        cancelled).

        Args:
            futures: list of futures to combine.
            fun: reduce-compatible function.
            executor: Executor to use when performing call to function.
            clb_executor: default executor to use when running new future's callbacks.
        """
        return cls \
            .gather(futures, clb_executor=clb_executor) \
            .map(lambda results: functools.reduce(fun, results, initial), executor=executor)

    @classmethod
    def _new(cls, other=None, *, clb_executor=None):
        executor = clb_executor or (other._executor if other else None)
        return cls(clb_executor=executor)

    @classmethod
    def convert(cls, future):
        """Performs future type conversion.

        It either makes sure that passed future is safe to use with current
        future type, or raises TypeError indicating incompatibility.

        Override this method in leaf future classes to enable
        compatibility between different Future implementations.
        """

        if not isinstance(future, cls):
            raise TypeError("{} is not compatible with {}"
            .format(_typename(cls), _typename(type(future))))
        return future

    @classmethod
    def compatible(cls, futures):
        pass


def _typename(cls):
    return cls.__module__ + '.' + cls.__name__
