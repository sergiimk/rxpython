import traceback
import logging

logger = logging.getLogger(__package__)


def log_error_handler(cls, tb):
    try:
        logger.error('Future/Task exception was never retrieved:\n%s',
                     ''.join(tb))
    except:
        pass


class Default(object):
    # Called when failure of the future was not handled by any callback
    # This includes exceptions in on_success and on_failure callbacks
    UNHANDLED_FAILURE_CALLBACK = staticmethod(log_error_handler)

    @staticmethod
    def on_unhandled_error(exc):
        tb = traceback.format_exception(exc.__class__, exc,
                                        exc.__traceback__)
        Default.UNHANDLED_FAILURE_CALLBACK(exc.__class__, tb)
