from ...config import Default


class SynchronousExecutor(object):
    def __call__(self, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except Exception as ex:
            Default.on_unhandled_error(ex)


# alias
Synchronous = SynchronousExecutor()
