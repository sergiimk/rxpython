import abc


class SchedulerBase(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __call__(self, fn, *args, **kwargs):
        """Same as submit but does not produce future in
        response. This method is intended to allow using
        schedulers as Executors for Future callbacks"""

    @abc.abstractmethod
    def submit(self, fn, *args, **kwargs):
        """Schedule execution of specified function"""

    @abc.abstractmethod
    def shutdown(self, wait=True):
        """Stop scheduler"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False