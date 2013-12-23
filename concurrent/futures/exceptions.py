class Error(Exception):
    """Base class for all future-related exceptions."""
    pass


class CancelledError(Error):
    """The Future was cancelled."""
    pass


class TimeoutError(Error):
    """The operation exceeded the given deadline."""
    pass
