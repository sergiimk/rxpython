from .ensure_exception_handled import EnsureExceptionHandledGuard
from .synchronous_executor import Synchronous
from .exceptions import (InvalidStateError, CancelledError)
from ..config import Default


# States for Future.
_PENDING = 'PENDING'
_CANCELLED = 'CANCELLED'
_FINISHED = 'FINISHED'


class FutureBase:
    """Encapsulates Future state and maintains callbacks."""

    _state = _PENDING
    _result = None
    _exception = None
    _ex_handler = None

    def __init__(self, *, clb_executor=None):
        """Initializes future instance.

        Args:
            clb_executor: specifies default executor object for scheduling
            callbacks (by default set from ``config.Default.CALLBACK_EXECUTOR``)
        """
        self._callbacks = []
        self._callbacks = []
        self._executor = clb_executor or Synchronous

    def add_done_callback(self, fun_res, *, executor=None):
        """Add a callback to be run when the future becomes done.

        The callback is called with a single argument - the future object.
        Callback is scheduled with either provided executor or with default
        executor of this future.
        """
        assert callable(fun_res) or fun_res is None, \
            "Future.add_done_callback expects callable or None"

        if fun_res is not None:
            if self._state != _PENDING:
                self._run_callback(fun_res, executor)
            else:
                self._callbacks.append((fun_res, executor))

    def remove_done_callback(self, fn):
        """Remove all instances of a callback from the "call when done" list.

        Returns the number of callbacks removed.
        """
        filtered_callbacks = [(f, executor) for f, executor in self._callbacks if f != fn]
        removed_count = len(self._callbacks) - len(filtered_callbacks)
        if removed_count:
            self._callbacks[:] = filtered_callbacks
        return removed_count

    def cancelled(self):
        """Return True if the future was cancelled."""
        return self._state == _CANCELLED

    def done(self):
        """Return True if the future is done.

        Done means either that a result / exception are available, or that the
        future was cancelled.
        """
        return self._state != _PENDING

    def result(self):
        """Return the result this future represents.

        If the future has been cancelled, raises CancelledError.  If the
        future's result isn't yet available, raises InvalidStateError.  If
        the future is done and has an exception set, this exception is raised.
        """
        if self._state == _CANCELLED:
            raise CancelledError
        if self._state != _FINISHED:
            raise InvalidStateError('Result is not ready.')

        self._error_handled()
        if self._exception is not None:
            raise self._exception
        return self._result

    def exception(self):
        """Return the exception that was set on this future.

        The exception (or None if no exception was set) is returned only if
        the future is done.  If the future has been cancelled, raises
        CancelledError.  If the future isn't done yet, raises
        InvalidStateError.
        """
        if self._state == _CANCELLED:
            raise CancelledError
        if self._state != _FINISHED:
            raise InvalidStateError('Exception is not set.')

        self._error_handled()
        return self._exception

    def cancel(self):
        """Cancel the future and schedule callbacks.

        If the future is already done or cancelled, return False.  Otherwise,
        change the future's state to cancelled, schedule the callbacks and
        return True.
        """
        if self._state != _PENDING:
            return False
        self._error_handled()
        return self._try_set_state(_CANCELLED, None, None)

    def set_result(self, result):
        """Mark the future done and set its result.

        If the future is already done when this method is called, raises
        InvalidStateError.
        """
        if not self.try_set_result(result):
            raise InvalidStateError("result was already set")

    def try_set_result(self, result):
        """Attempts to mark the future done and set its result.

        Returns False if the future is already done when this method is called.
        """
        return self._try_set_state(_FINISHED, result, None)

    def set_exception(self, exception):
        """Mark the future done and set an exception.

        If the future is already done when this method is called, raises
        InvalidStateError.
        """
        if not self.try_set_exception(exception):
            raise InvalidStateError("result was already set")

    def try_set_exception(self, exception):
        """Attempts to mark the future done and set an exception.

        Returns False if the future is already done when this method is called.
        """
        assert isinstance(exception, Exception), "Promise.failure expects Exception instance"
        return self._try_set_state(_FINISHED, None, exception)

    def set_from(self, other):
        """Copies result of another future into this one.

        Copies either result, exception, or cancelled state depending on how
        other future was completed.

        If this future is already done when this method is called, raises
        InvalidStateError. Other future should be done() before making this call.
        """
        if not self.try_set_from(other):
            raise InvalidStateError("result was already set")

    def try_set_from(self, other):
        """Copies result of another future into this one.

        Copies either result, exception, or cancelled state depending on how
        other future was completed.

        Returns False if this future is already done when this method is called.
        Other future should be done() before making this call.
        """
        assert isinstance(other, FutureBase)
        assert other.done()

        if other.cancelled():
            return self.cancel()
        else:
            exception = other.exception()
            if exception is not None:
                return self.try_set_exception(exception)
            else:
                return self.try_set_result(other.result())

    def _try_set_state(self, state, result, exception):
        if self._state == _CANCELLED:
            return True
        if self._state != _PENDING:
            return False
        self._state = state
        self._result = result
        self._exception = exception
        self._on_result_set()
        return True

    def _error_handled(self):
        if self._ex_handler is not None:
            self._ex_handler.clear()
            self._ex_handler = None

    def _on_result_set(self):
        if self._exception is not None:
            clb = Default.UNHANDLED_FAILURE_CALLBACK
            self._ex_handler = EnsureExceptionHandledGuard(self._exception, clb)
            self._executor(self._ex_handler.activate)

        callbacks = self._callbacks[:]
        if not callbacks:
            return

        self._callbacks[:] = []
        for clb, executor in callbacks:
            self._run_callback(clb, executor)

    def _run_callback(self, clb, executor):
        executor = executor or self._executor
        executor(clb, self)

    def __repr__(self):
        res = self.__class__.__name__
        if self._state == _FINISHED:
            if self._exception is not None:
                res += '<exception={!r}>'.format(self._exception)
            else:
                res += '<result={!r}>'.format(self._result)
        elif self._callbacks:
            size = len(self._callbacks)
            if size > 2:
                res += '<{}, [{}, <{} more>, {}]>'.format(
                    self._state, self._callbacks[0],
                    size - 2, self._callbacks[-1])
            else:
                res += '<{}, {}>'.format(self._state, self._callbacks)
        else:
            res += '<{}>'.format(self._state)
        return res
