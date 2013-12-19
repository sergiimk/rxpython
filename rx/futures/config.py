import traceback
import sys


def log_to_stderr(ex):
    try:
        sys.stderr.write("Unhandled Future exception:\n")
        tb = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
        sys.stderr.write(''.join(tb))
        sys.stderr.flush()
    except:
        pass


on_unhandled_failure = log_to_stderr
