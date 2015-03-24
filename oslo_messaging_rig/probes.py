import contextlib
import functools
import logging
import time

from oslo_messaging_rig import utils


LOG = logging.getLogger(__name__)


class Producer(object):
    def __init__(self, pool_cls, message, workers=64, message_cnt=1000):
        """General producer class that spawns workers from a pool.

        This is meant to closely resemble how actual OpenStack services spawn
        client threads. This is usually done as part of a previous
        oslo-messaging RPC callback that dispatches to a thread from a pool
        (this is what oslo-messaging executor does).

        The pool_cls can be any pool of workers that supports imap
        """
        self.workers = workers
        self.pool = pool_cls(workers)
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
        """Generate payloads from the Message instance and send them.

        Spawn workers from a pool per message, trying to simulate how an
        actual OpenStack service works as closely as possible.
        """
        start = time.time()
        LOG.info("Starting sending %(count)s messages of %(size)s bytes" %
                 {'count': self.message_cnt, 'size': len(self.message)})
        responses = self.pool.imap(
            self._producer_thread,
            self.message.payloads(num=self.message_cnt)
        )
        self.process_responses(responses)
        # NOTE: for some reason eventlet.GreenPool.waitall does not block so
        # we want to record the time after processing the events which is not
        # as accurate
        self.execution_time = time.time() - start


def _NoopLock():
    @contextlib.contextmanager
    def _noop_context_mgr(*args, **kwargs):
        yield

    return _noop_context_mgr


class Consumer(object):
    def __init__(self, message, max_messages=1000, lock=None):
        """Base consumer class, not tied to the underlying executor.

        This closely resembles how an actual OpenStack service uses
        oslo_messaging as a server. The instance keeps track of the number
        of messages received and total time, but not much else.
        """
        self.message = message
        self.max_messages = max_messages
        self.server = self.message.get_server([self])
        self._start_time = self.execution_time = None
        self.message_cnt = 0
        self.lock = lock or _NoopLock()

    def run(self):
        """Start an oslo-messaging server.

        The server has callbacks mapped to this instance based on the message.
        """
        self._start_time = time.time()
        LOG.info("Starting oslo.messaging server waiting for %(count)s "
                 "messages" % {'count': self.max_messages})
        self.server.start()
        self.server.wait()

    def stop(self):
        """Stop the oslo-messaging server."""
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
