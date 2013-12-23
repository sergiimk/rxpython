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

    # Default executor for future callbacks
    CALLBACK_EXECUTOR = None

    @staticmethod
    def get_callback_executor():
        if not Default.CALLBACK_EXECUTOR:
            from .sync.synchronous_executor import Synchronous

            Default.CALLBACK_EXECUTOR = Synchronous
        return Default.CALLBACK_EXECUTOR

    @staticmethod
    def on_unhandled_error(exc):
        tb = traceback.format_exception(exc.__class__, exc,
                                        exc.__traceback__)
        Default.UNHANDLED_FAILURE_CALLBACK(exc.__class__, tb)
