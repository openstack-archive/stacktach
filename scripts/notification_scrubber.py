import argparse
import json
import os
import sys
import time

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

from stacktach import message_service as msg
from stacktach import utils

import scrubbers


def scrub(args, send_notif=lambda x: None):
    print "Starting scrub."
    start = utils.str_time_to_unix(args.start)
    end = utils.str_time_to_unix(args.end)

    if hasattr(scrubbers, args.scrubber):
        Scrubber = getattr(scrubbers, args.scrubber)
        scrubber = Scrubber(start, end)

        count = 0
        for raw in scrubber.raws():
            matches, body = scrubber.filter(raw)
            if matches and not body:
                body = json.loads(raw['json'])[1]
            if matches and body:
                scrubbed = scrubber.scrub(body)
                count += 1
                send_notif(scrubbed)
        return count
    else:
        print "No scrubber class %s." % args.scrubber
        return 0


def scrub_with_notifications(args):
    print "!!!!!! WARNING: SENDING TO RABBIT !!!!!!"
    print "!!!!!!  Sleeping for 30 seconds   !!!!!!"
    print "!!!!!!     before proceeding      !!!!!!"
    time.sleep(30)
    with open(args.rabbit_config) as fp:
        rabbit_config = json.load(fp)
        exchange = msg.create_exchange(rabbit_config['exchange'],
                                       'topic',
                                       durable=rabbit_config['durable_queue'])
        conn_conf = (rabbit_config['host'], rabbit_config['port'],
                     rabbit_config['userid'], rabbit_config['password'],
                     'librabbitmq', rabbit_config['virtual_host'])

        with msg.create_connection(*conn_conf) as conn:
            def send_notif(notif):
                msg.send_notification(notif, rabbit_config['routing_key'],
                                      conn, exchange)
            count = scrub(args, send_notif=send_notif)
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Stacktach Notification Scrubber')
    parser.add_argument('--rabbit', action='store_true')
    parser.add_argument('--rabbit_config', default='rabbit_config.json')
    parser.add_argument('--scrubber', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    args = parser.parse_args()

    if args.rabbit:
        print "%s Events Scrubbed" % scrub_with_notifications(args)
    else:
        print "%s Events Scrubbed" % scrub(args)


