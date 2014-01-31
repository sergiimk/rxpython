import traceback


class EnsureExceptionHandledGuard:
    """Helper for ensuring that Future's exceptions were handled.

    This solves a nasty problem with Futures and Tasks that have an
    exception set: if nobody asks for the exception, the exception is
    never logged.  This violates the Zen of Python: 'Errors should
    never pass silently.  Unless explicitly silenced.'

    However, we don't want to log the exception as soon as
    set_exception() is called: if the calling code is written
    properly, it will get the exception and handle it properly.  But
    we *do* want to log it if result() or exception() was never called
    -- otherwise developers waste a lot of time wondering why their
    buggy code fails silently.

    An earlier attempt added a __del__() method to the Future class
    itself, but this backfired because the presence of __del__()
    prevents garbage collection from breaking cycles.  A way out of
    this catch-22 is to avoid having a __del__() method on the Future
    class itself, but instead to have a reference to a helper object
    with a __del__() method that logs the traceback, where we ensure
    that the helper object doesn't participate in cycles, and only the
    Future has a reference to it.

    The helper object is added when set_exception() is called.  When
    the Future is collected, and the helper is present, the helper
    object is also collected, and its __del__() method will log the
    traceback.  When the Future's result() or exception() method is
    called (and a helper object is present), it removes the the helper
    object, after calling its clear() method to prevent it from
    logging.

    One downside is that we do a fair amount of work to extract the
    traceback from the exception, even when it is never logged.  It
    would seem cheaper to just store the exception object, but that
    references the traceback, which references stack frames, which may
    reference the Future, which references the _EnsureExceptionHandledGuard,
    and then the _EnsureExceptionHandledGuard would be included in a cycle,
    which is what we're trying to avoid! As an optimization, we don't
    immediately format the exception; we only do the work when
    activate() is called, which call is delayed until after all the
    Future's callbacks have run.  Since usually a Future has at least
    one callback (typically set by 'yield from') and usually that
    callback extracts the callback, thereby removing the need to
    format the exception.

    PS. I don't claim credit for this solution.  I first heard of it
    in a discussion about closing files when they are collected.
    """

    __slots__ = ['exc', 'tb', 'hndl', 'cls']

    def __init__(self, exc, handler):
        self.exc = exc
        self.hndl = handler
        self.cls = type(exc)
        self.tb = None

    def activate(self):
        exc = self.exc
        if exc is not None:
            self.exc = None
            self.tb = traceback.format_exception(exc.__class__, exc,
                                                 exc.__traceback__)

    def clear(self):
        self.exc = None
        self.tb = None

    def __del__(self):
        if self.tb:
            self.hndl(self.cls, self.tb)
