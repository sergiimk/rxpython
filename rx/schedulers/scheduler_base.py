import abc


class SchedulerBase(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def submit(self, fn, *vargs, **kwargs):
        """Schedule execution of specified function"""

    @abc.abstractmethod
    def shutdown(self, wait=True):
        """Stop scheduler"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False