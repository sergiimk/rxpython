import abc


class FutureBase(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def add_done_callback(self, fun_res, executor=None):
        """Add a callback to be run when the future becomes done.

        The callback is called with a single argument - the future object. If
        the future is already done when this is called, the callback is
        scheduled with call_soon.
        """
        pass

    @abc.abstractmethod
    def remove_done_callback(self, fn):
        """Remove all instances of a callback from the "call when done" list.

        Returns the number of callbacks removed.
        """
        pass

    @abc.abstractmethod
    def cancel(self):
        """Cancel the future and schedule callbacks.

        If the future is already done or cancelled, return False.  Otherwise,
        change the future's state to cancelled, schedule the callbacks and
        return True.
        """
        pass

    @abc.abstractmethod
    def cancelled(self):
        """Return True if the future was cancelled."""
        pass

    @abc.abstractmethod
    def done(self):
        """Return True if the future is done.

        Done means either that a result / exception are available, or that the
        future was cancelled.
        """
        pass

    @abc.abstractmethod
    def result(self):
        """Return the result this future represents.

        If the future has been cancelled, raises CancelledError.  If the
        future's result isn't yet available, raises InvalidStateError.  If
        the future is done and has an exception set, this exception is raised.
        """
        pass

    @abc.abstractmethod
    def exception(self):
        """Return the exception that was set on this future.

        The exception (or None if no exception was set) is returned only if
        the future is done.  If the future has been cancelled, raises
        CancelledError.  If the future isn't done yet, raises
        InvalidStateError.
        """
        pass

    @abc.abstractmethod
    def set_result(self, result):
        """Mark the future done and set its result.

        If the future is already done when this method is called, raises
        InvalidStateError.
        """
        pass

    @abc.abstractmethod
    def try_set_result(self, result):
        """Attempts to mark the future done and set its result.

        Returns False if the future is already done when this method is called.
        """
        pass

    @abc.abstractmethod
    def set_exception(self, exception):
        """Mark the future done and set an exception.

        If the future is already done when this method is called, raises
        InvalidStateError.
        """
        pass

    @abc.abstractmethod
    def try_set_exception(self, exception):
        """Attempts to mark the future done and set an exception.

        Returns False if the future is already done when this method is called.
        """
        pass

    @abc.abstractmethod
    def set_from(self, other_future):
        """Copies result of another future into this one.

        Copies either result, exception, or cancelled state depending on how
        other future was completed.

        If this future is already done when this method is called, raises
        InvalidStateError. Other future should be done() before making this call.
        """
        pass

    @abc.abstractmethod
    def try_set_from(self, other_future):
        """Copies result of another future into this one.

        Copies either result, exception, or cancelled state depending on how
        other future was completed.

        Returns False if this future is already done when this method is called.
        Other future should be done() before making this call.
        """
        pass
