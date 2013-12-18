import logging
logger = logging.getLogger(__name__)


class InlineExecutionContext(object):
    def execute(self, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except:
            logger.exception()

Inline = InlineExecutionContext()