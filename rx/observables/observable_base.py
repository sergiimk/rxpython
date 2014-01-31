
class ObservableBase:
    def __init__(self):
        self._callbacks = []

    def add_observe_callback(self, fun):
        self._callbacks.append(fun)

    def remove_observe_callback(self, fun):
        filtered_callbacks = [f for f in self._callbacks if f != fun]
        removed_count = len(self._callbacks) - len(filtered_callbacks)
        if removed_count:
            self._callbacks[:] = filtered_callbacks
        return removed_count

    def set_next_value(self, value):
        pass
