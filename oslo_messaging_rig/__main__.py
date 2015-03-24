import argparse
import logging

import eventlet
from oslo_config import cfg
import oslo_messaging

from oslo_messaging_rig import probes
from oslo_messaging_rig import message as test_message


CONF = cfg.CONF


TRANSPORT = None


LOG = None


TRANSPORT_ALIASES = {
    'nova.openstack.common.rpc.impl_kombu': 'rabbit',
    'nova.openstack.common.rpc.impl_qpid': 'qpid',
}


def _init_messaging():
    global TRANSPORT
    oslo_messaging.set_transport_defaults("oslo-testing-rig")
    # Get the config-files from nova directory - may become configurable later
    CONF([], project="nova")
    TRANSPORT = oslo_messaging.get_transport(CONF, aliases=TRANSPORT_ALIASES)

def _setup_logging(debug=False):
    global LOG
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
    LOG = logging.getLogger(__name__)

def producer_test(message_cnt, message_size, worker_count=64):
    global TRANSPORT
    message = test_message.Message(TRANSPORT, size_kb=message_size)
    producer = probes.Producer(eventlet.greenpool.GreenPool,
                               message, workers=worker_count,
                               message_cnt=message_cnt)
    producer.run()
    LOG.info("Sent: %(sent)s; Total time: %(total)s; Avg: %(average)s" %
             {"sent": producer.message_cnt,
              "total": producer.execution_time,
              "average": producer.execution_time / producer.message_cnt})


def consumer_test(msg_count, message_size, **kwargs):
    global TRANSPORT
    message = test_message.Message(TRANSPORT, size_kb=message_size)
    consumer = probes.Consumer(message, max_messages=msg_count)
    consumer.run()
    LOG.info("Received: %(sent)s; Total time: %(total)s; Avg: %(average)s" %
             {"sent": consumer.max_messages,
              "total": consumer.execution_time,
              "average": consumer.execution_time / consumer.max_messages})


def main():
    eventlet.monkey_patch(time=False)

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Show debug output")
    parser.add_argument("-m", "--message_count", type=int, default=1000,
                        help="Number of messages to send/receive")
    parser.add_argument("-s", "--message_size", type=int, default=10,
                        help="Individual message size in kilobytes")
    parser.add_argument("-w", "--worker_count", type=int, default=64,
                        help="Number of producer workers")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p", "--producer", action="store_true",
                        help="Run as a message producer")
    group.add_argument("-c", "--consumer", action="store_true",
                        help="Run as a message consumer")
    args = parser.parse_args()

    _setup_logging(args.debug)
    _init_messaging()

    test_method = consumer_test if args.consumer else producer_test
    test_method(args.message_count, args.message_size,
                worker_count=args.worker_count)

main()
