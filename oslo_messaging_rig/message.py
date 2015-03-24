import itertools
import random
import string

import oslo_messaging


class Message(object):
    MESSAGE_NAME = "oslo-rig-test-message"
    TOPIC = "oslo-rig-test-topic"
    HOST = "oslo-rig-test-server"

    _KEY_LENGTH_SPAN = (2, 20)
    _VALUE_LENGTH_SPAN = (40, 200)

    def __init__(self, oslo_transport, size_kb=10, reply_needed=False):
        self.transport = oslo_transport
        self.size = size_kb * 1024
        self.reply = reply_needed
        self.msg = self._generate_message()

    def get_client(self):
        target = oslo_messaging.Target(topic=self.TOPIC)
        return oslo_messaging.RPCClient(self.transport, target)

    def get_server(self, endpoints):
        target = oslo_messaging.Target(topic=self.TOPIC, server=self.HOST)
        return oslo_messaging.get_rpc_server(self.transport, target,
                                             endpoints, executor='eventlet')

    def __len__(self):
        """Actual size of the generated payload in bytes."""
        return len("".join(itertools.chain(*self.msg.iteritems())))

    def _generate_message(self):
        # 15% of the message should be arguments
        keys = ("".join(random.sample(string.ascii_letters,
                                      random.randint(*self._KEY_LENGTH_SPAN)))
                for _ in xrange(int((self.size * 0.15) / 9)))
        values = ("".join(random.sample(string.ascii_letters * 4,
                                        random.randint(
                                            *self._VALUE_LENGTH_SPAN)))
                  for _ in xrange(int((self.size * 0.85) / 80)))
        return dict(zip(keys, values))

    def payloads(self, num=None):
        for cnt in itertools.count(0):
            if num and cnt > num:
                break
            yield self.msg
