import threading
import O4_UI_Utils as UI

################################################################################
class parallel_worker(threading.Thread):
    def __init__(self, task, queue, progress=None, success=[1]):
        threading.Thread.__init__(self)
        self._task = task
        self._queue = queue
        self._progress = progress
        self._success = success

    def run(self):
        while True:
            args = self._queue.get()
            if isinstance(args, str) and args == "quit":
                try:
                    UI.progress_bar(self._progress["bar"], 100)
                except:
                    pass
                return 1
            self._success[0] = self._task(*args) and self._success[0]
            if self._progress:
                self._progress["done"] += 1
                UI.progress_bar(
                    self._progress["bar"],
                    int(
                        100
                        * self._progress["done"]
                        / (self._progress["done"] + self._queue.qsize())
                    ),
                )
            if UI.red_flag:
                return 0

################################################################################
def parallel_execute(task, queue, nbr_workers, progress=None):
    workers = []
    success = [1]
    for _ in range(nbr_workers):
        queue.put("quit")
        worker = parallel_worker(task, queue, progress, success)
        worker.start()
        workers.append(worker)
    for worker in workers:
        worker.join()
    if UI.red_flag:
        return 0
    return success[0]


################################################################################
def parallel_launch(task, queue, nbr_workers, progress=None):
    workers = []
    for _ in range(nbr_workers):
        worker = parallel_worker(task, queue, progress)
        worker.start()
        workers.append(worker)
    return workers

################################################################################
def parallel_join(workers):
    for worker in workers:
        worker.join()