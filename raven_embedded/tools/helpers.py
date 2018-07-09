from threading import Thread


def singleton(my_class):
    instances = {}

    def get_instance(*args, **kwargs):
        if my_class not in instances:
            instances[my_class] = my_class(*args, **kwargs)
        return instances[my_class]

    return get_instance


class PropagatingThread(Thread):
    def run(self):
        self.exception = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exception = e

    def join(self):
        super(PropagatingThread, self).join()
        if self.exception:
            raise self.exception
        return self.ret
