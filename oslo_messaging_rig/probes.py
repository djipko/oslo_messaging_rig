import contextlib
import functools
import time

from oslo_messaging_rig import utils


class Producer(object):
    def __init__(self, pool_cls, message, workers=64, message_cnt=1000):
        self.workers = workers
        self.pool = pool_cls(size=workers)
        self.message = message
        self.client = message.get_client()
        self.message_cnt = message_cnt
        self.execution_time = None

    @utils.return_exception
    def _producer_thread(self, msg, cast_to_host=False):
        ctxt = self.client.prepare(
            server=self.message.HOST if cast_to_host else None)
        # Oslo messaging client interface requires a context arg
        dummy_context = {"user": "test-user", "tenant": "test-tenant"}
        client_method = functools.partial(ctxt.cast, dummy_context)
        if self.message.reply:
            client_method = functools.partial(ctxt.call, dummy_context)

        client_method(self.message.MESSAGE_NAME, **msg)

    def process_responses(self, responses):
        for response in responses:
            if utils.returned_exception(response):
                raise response.exc

    def run(self):
        start = time.time()
        responses = self.pool.imap(
            self._producer_thread,
            self.message.payloads(num=self.message_cnt)
        )
        responses.pool.waitall()
        self.execution_time = time.time() - start
        self.process_responses(responses)


def _NoopLock():
    @contextlib.contextmanager
    def _noop_context_mgr(*args, **kwargs):
        yield

    return _noop_context_mgr


class Consumer(object):
    def __init__(self, message, max_messages=1000, lock=None):
        self.message = message
        self.max_messages = max_messages
        self.server = self.message.get_server([self])
        self._start_time = self.execution_time = None
        self.message_cnt = 0
        self.lock = lock or _NoopLock()

    def run(self):
        self._start_time = time.time()
        self.server.start()
        self.server.wait()

    def stop(self):
        if self._start_time:
            self.execution_time = time.time() - self._start_time
            self.server.stop()

    def __getattr__(self, name):
        def _worker_method(*args, **kwargs):
            with self.lock():
                self.message_cnt += 1
                if self.message_cnt >= self.max_messages:
                    self.stop()

        if name == self.message.MESSAGE_NAME:
            return _worker_method
        raise AttributeError("No callback for message %(name)s.")
