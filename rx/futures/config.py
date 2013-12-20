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

# Called when failure of the future was not handled by any callback
# This includes exceptions in on_success and on_failure callbacks
ON_UNHANDLED_FAILURE = log_to_stderr

# Default executor for future callbacks
DEFAULT_CALLBACK_EXECUTOR = None


def get_default_callback_executor():
    global DEFAULT_CALLBACK_EXECUTOR
    if not DEFAULT_CALLBACK_EXECUTOR:
        from .synchronous_executor import Synchronous

        DEFAULT_CALLBACK_EXECUTOR = Synchronous
    return DEFAULT_CALLBACK_EXECUTOR
