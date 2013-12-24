class Error(Exception):
    """Base class for all future-related exceptions."""
    pass


class CancelledError(Error):
    """The Future was cancelled."""
    pass


class TimeoutError(Error):
    """The operation exceeded the given deadline."""
    pass


class InvalidStateError(Error):
    """The operation is not allowed in this state."""
    # TODO: Show the future, its state, the method, and the required state.
