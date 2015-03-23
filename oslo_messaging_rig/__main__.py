import argparse
import eventlet
from oslo_config import cfg
import oslo_messaging

from oslo_messaging_rig import probes
from oslo_messaging_rig import message as test_message


CONF = cfg.CONF


TRANSPORT_ALIASES = {
    'nova.openstack.common.rpc.impl_kombu': 'rabbit',
    'nova.openstack.common.rpc.impl_qpid': 'qpid',
}


def _init_messaging():
    oslo_messaging.set_transport_defaults("oslo-testing-rig")
    # Get the config-files from nova directory - may become configurable later
    CONF([], project="nova")
    transport = oslo_messaging.get_transport(CONF, aliases=TRANSPORT_ALIASES)
    return transport


def producer_test(message_cnt, message_size):
    transport = _init_messaging()
    message = test_message.Message(transport, size_kb=message_size)
    producer = probes.Producer(eventlet.greenpool.GreenPool,
                               message, message_cnt=message_cnt)
    producer.run()
    print("Sent: %(sent)s; Total time: %(total)s; Avg: %(average)s" %
          {"sent": producer.message_cnt,
           "total": producer.execution_time,
           "average": producer.execution_time / producer.message_cnt})


def consumer_test(msg_count, message_size):
    print("Consumer test not implemented yet.")


def main():
    eventlet.monkey_patch()

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--message_count", type=int, default=1000,
                        help="Number of messages to send/receive")
    parser.add_argument("-s", "--message_size", type=int, default=10,
                        help="Individual message size in kilobytes")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p", "--producer", action="store_true",
                        help="Run as a message producer")
    group.add_argument("-c", "--consumer", action="store_true",
                        help="Run as a message consumer")
    args = parser.parse_args()
    test_method = consumer_test if args.consumer else producer_test
    test_method(args.message_count, args.message_size)

main()
