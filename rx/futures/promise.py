from .future import Future


class Promise(object):
    """Promise is an object which can be completed with a value or failed with an exception.
    """

    def __init__(self, clb_executor=None):
        """Initializes new Promise instance.

        Args:
            clb_executor: Executor object to use when calling
                future on_success and on_failure callbacks.
        """
        self._future = Future(clb_executor)

    def success(self, result):
        """Completes associated future with provided value.

        Args:
            result: Value to complete future with.

        Raises:
            IllegalStateError: If future value was already set.
        """
        self._future._success(result)

    def try_success(self, result):
        """Completes associated future with provided value.

        Args:
            result: Value to complete future with.

        Returns:
            True if future value was set and False if it was already set before.
        """
        return self._future._try_success(result)

    def failure(self, exception):
        """Completes associated future with provided exception.

        Args:
            exception: Exception to complete future with.

        Raises:
            IllegalStateError: If future value was already set.
        """
        self._future._failure(exception)

    def try_failure(self, exception):
        """Completes associated future with provided exception.

        Args:
            exception: Exception to complete future with.

        Returns:
            True if future value was set and False if it was already set before.
        """
        self._future._try_failure(exception)

    def complete(self, fun, *vargs, **kwargs):
        """Executes provided function and sets future value or exception if function raises.

        Args:
            fun: Function to be executed synchronously to set future result.

        Raises:
            IllegalStateError: If future value was already set.
        """
        self._future._complete(fun, *vargs, **kwargs)

    def try_complete(self, fun, *vargs, **kwargs):
        """Executes provided function and sets future value or exception if function raises.

        Args:
            fun: Function to be executed synchronously to set future result.

        Returns:
            True if future value was set and False if it was already set before.
        """
        return self._future._try_complete(fun, *vargs, **kwargs)

    @property
    def is_completed(self):
        """Returns True if the future is completed."""
        return self._future.is_completed

    @property
    def is_cancelled(self):
        """Returns True if the future cancellation was requested by client."""
        return self._future.is_cancelled

    @property
    def future(self):
        """Returns associated future instance."""
        return self._future
