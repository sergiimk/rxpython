import logging
logger = logging.getLogger(__name__)


class SynchronousExecutionContext(object):
    def execute(self, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except:
            logger.exception()


Synchronous = SynchronousExecutionContext()
