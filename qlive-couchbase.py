#!/usr/bin/env python

import argparse
import json
import logging
import struct
import time

# see https://github.com/zeromq/pyzmq/wiki/Building-and-Installing-PyZMQ
# QuakeLive requires CZMQ 3.x APIs or newer (libzmq 4.x)
import zmq
from couchbase.cluster import Cluster
from couchbase.cluster import PasswordAuthenticator
from unidecode import unidecode

logger = logging.getLogger(__name__)


def _processMessage(msg, buckets):
    # get message type and insert into couchbase bucket if configured
    if msg['TYPE'] in buckets:
        buckets[msg['TYPE']].insert("{}".format(long(time.time() * 1000 * 1000)), msg['DATA'])


def _readSocketEvent(msg):
    # NOTE: little endian - hopefully that's not platform specific?
    event_id = struct.unpack('<H', msg[:2])[0]
    # NOTE: is it possible I would get a bitfield?
    event_names = {
        zmq.EVENT_ACCEPTED: 'EVENT_ACCEPTED',
        zmq.EVENT_ACCEPT_FAILED: 'EVENT_ACCEPT_FAILED',
        zmq.EVENT_BIND_FAILED: 'EVENT_BIND_FAILED',
        zmq.EVENT_CLOSED: 'EVENT_CLOSED',
        zmq.EVENT_CLOSE_FAILED: 'EVENT_CLOSE_FAILED',
        zmq.EVENT_CONNECTED: 'EVENT_CONNECTED',
        zmq.EVENT_CONNECT_DELAYED: 'EVENT_CONNECT_DELAYED',
        zmq.EVENT_CONNECT_RETRIED: 'EVENT_CONNECT_RETRIED',
        zmq.EVENT_DISCONNECTED: 'EVENT_DISCONNECTED',
        zmq.EVENT_LISTENING: 'EVENT_LISTENING',
        zmq.EVENT_MONITOR_STOPPED: 'EVENT_MONITOR_STOPPED',
    }
    event_name = event_names[event_id] if event_names.has_key(event_id) else '%d' % event_id
    event_value = struct.unpack('<I', msg[2:])[0]
    return (event_id, event_name, event_value)


def _checkMonitor(monitor):
    try:
        event_monitor = monitor.recv(zmq.NOBLOCK)
    except zmq.Again:
        # logging.debug( 'again' )
        return

    (event_id, event_name, event_value) = _readSocketEvent(event_monitor)
    event_monitor_endpoint = monitor.recv(zmq.NOBLOCK)
    logger.info('monitor: %s %d endpoint %s' % (event_name, event_value, event_monitor_endpoint))


def read(conf):
    try:
        # connect to zmq stats socket
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        monitor = socket.get_monitor_socket(zmq.EVENT_ALL)
        if conf['ql_server']['zmq_stats_password'] is not None:
            socket.plain_username = 'stats'
            socket.plain_password = unidecode(conf['ql_server']['zmq_stats_password'])
            socket.zap_domain = 'stats'
        socket.connect(conf['ql_server']['zmq_stats_uri'])
        socket.setsockopt(zmq.SUBSCRIBE, '')
        logging.info('Connecting zmq subscribe : %s' % conf['ql_server']['zmq_stats_uri'])

        # connect to couchbase
        cluster = Cluster(conf['couchbase_server']['uri'])
        authenticator = PasswordAuthenticator(conf['couchbase_server']['username'],
                                              conf['couchbase_server']['password'])
        cluster.authenticate(authenticator)
        logging.info('Connecting couchbase : %s' % conf['couchbase_server']['uri'])

        # connect to couchbase buckets
        buckets = {}
        for x in conf['couchbase_server']['buckets']:
            buckets[x['ql_msg_type']] = cluster.open_bucket(x['bucket_name'])

        while True:
            event = socket.poll(long(conf['ql_server']['zmq_socket_timeout']))
            # check if there are any events to report on the socket
            _checkMonitor(monitor)

            if event == 0:
                logger.info('poll loop')
                continue

            while (True):
                try:
                    msg = socket.recv_json(zmq.NOBLOCK)
                except zmq.error.Again:
                    break
                except Exception, e:
                    logger.error(e)
                    break
                else:
                    _processMessage(msg, buckets)

    except Exception, e:
        logger.error(e)
    finally:
        logger.info("Exiting..")


if __name__ == '__main__':

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', "--debug", action="store_true", help="Enable Debugging")
    parser.add_argument('-c', '--conf', required=True, help="JSON Config File")
    args = parser.parse_args()

    # configure logging
    logging.basicConfig(format="%(asctime)s [%(name)s:%(lineno)d][%(levelname)s] %(message)s", level=logging.INFO)

    # enable debugging
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # open config and parse
    with open(args.conf) as data_file:
        conf = json.load(data_file)

    # log configuration
    logger.info('zmq python bindings %s, libzmq version %s' % (repr(zmq.__version__), zmq.zmq_version()))

    # run
    read(conf)
