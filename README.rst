Oslo Messaging Performance Testing Rig
====

`oslo-messaging <https://github.com/openstack/oslo.messaging/>`_ is the OpenStack messaging
library that is used by all projects for RPC.

This projects aims to make *realistic* performance testing of oslo.messaging as easy as possible, and
to uncover flaws in the design of the library internals that impact real-world usage. An example of
issues could be: flaws in driver/executor design and implementation, or inefficiencies in how underlying
libraries are used. It is meant to help developers iterate quickly and get quick feedback on how their changes
actually impact performance for a common usage pattern.

Performance of the messaging layer should be something all of OpenStack cares about, since every project
uses it. We also want to make sure that development time goes into fixing problems that
impact how oslo-messaging is *actually* used in production. For that we need ways to do realistic benchmarks.

Usage
-----

oslo_messaging_rig command line utility can be run in ``producer`` and ``consumer`` mode. Help actually
tells us more about it:

.. code-block:: bash

    $ python oslo_messaging_rig --help
    usage: oslo_messaging_rig [-h] [-d] [-m MESSAGE_COUNT] [-s MESSAGE_SIZE]
                              [-w WORKER_COUNT] [-p | -c]

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           Show debug output
      -m MESSAGE_COUNT, --message_count MESSAGE_COUNT
                            Number of messages to send/receive
      -s MESSAGE_SIZE, --message_size MESSAGE_SIZE
                            Individual message size in kilobytes
      -w WORKER_COUNT, --worker_count WORKER_COUNT
                            Number of producer workers
      -p, --producer        Run as a message producer
      -c, --consumer        Run as a message consumer

When run in producer mode, it will try to emulate how an actual OpenStack service uses
oslo-messaging to send RPC messages (single process with multiple green threads competing
for underlying oslo-messaging resources), but without doing any other actual work
a real service would do. What this design attempts to do is uncover bottlenecks in oslo-messaging
internal design when used by an OpenStack service, and not just measure throughput.

Consumer mode is similar - it will start an actual oslo-messaging RPC server that simply receives
all the messages it can without doing much else, but it will still do it while running a real
eventloop in a single process, much like a production OpenStack service does.

Configuration is made super easy, as the oslo_messaging_rig utility will try 
to grab the Nova configuration from the machine it is run on, so simply dropping
it on any of your OpenStack servers should work.

Examples
--------

* Run a consumer that will send 20k 10kb messages as fast as it can.

.. code-block:: bash

    $ python oslo_messaging_rig -p -m 20000 -s 10

* Do the same but run only 10 eventlet worker threads in parallel

.. code-block:: bash

    $ python oslo_messaging_rig -p -m 20000 -s 10 -w 10

* Consume 100k messages from the test queue

.. code-block:: bash

    $ python oslo_messaging_rig -c 100000

Bugs and PR
------------

Feel free to open them here. Write nice commit messages, and keep commits small.
