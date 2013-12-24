from concurrent.futures.exceptions import (InvalidStateError,
                                           CancelledError)


# States for Future.
_PENDING = 'PENDING'
_CANCELLED = 'CANCELLED'
_FINISHED = 'FINISHED'


class FutureCore(object):
    """Encapsulates Future state."""
    _state = _PENDING
    _result = None
    _exception = None
    _ex_handler = None

    def __init__(self):
        self._callbacks = []

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

    def _try_set_result(self, state, result, exception):
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

    #virtual
    def _on_result_set(self):
        pass

    def cancel(self):
        """Cancel the future and schedule callbacks.

        If the future is already done or cancelled, return False.  Otherwise,
        change the future's state to cancelled, schedule the callbacks and
        return True.
        """
        if self._state != _PENDING:
            return False
        self._error_handled()
        return self._try_set_result(_CANCELLED, None, None)

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
        return self._try_set_result(_FINISHED, result, None)

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
        return self._try_set_result(_FINISHED, None, exception)

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
        assert isinstance(other, FutureCore)
        assert other.done()

        if other.cancelled():
            return self.cancel()
        else:
            exception = other.exception()
            if exception is not None:
                return self.try_set_exception(exception)
            else:
                return self.try_set_result(other.result())
