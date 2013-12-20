from .future import Future


class SynchronousExecutor(object):
    @staticmethod
    def execute(fn, *args, **kwargs):
        try:
            return Future.successful(fn(*args, **kwargs))
        except Exception as ex:
            return Future.failed(ex)


# alias
Synchronous = SynchronousExecutor
