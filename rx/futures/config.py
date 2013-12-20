import traceback
import sys


def log_to_stderr(ex):
    try:
        sys.stderr.write("Unhandled Future failure:\n")
        tb = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
        sys.stderr.write(''.join(tb))
        sys.stderr.flush()
    except:
        pass


class Default(object):
    # Called when failure of the future was not handled by any callback
    # This includes exceptions in on_success and on_failure callbacks
    UNHANDLED_FAILURE_CALLBACK = log_to_stderr

    # Default executor for future callbacks
    CALLBACK_EXECUTOR = None

    @staticmethod
    def get_callback_executor():
        if not Default.CALLBACK_EXECUTOR:
            from .synchronous_executor import Synchronous

            Default.CALLBACK_EXECUTOR = Synchronous
        return Default.CALLBACK_EXECUTOR
