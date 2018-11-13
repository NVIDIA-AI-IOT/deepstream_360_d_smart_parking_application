"""
Main file for streaming Multicam tracker for 360 degree usecase
"""
__version__ = '0.2'

import argparse
import json
import logging
import signal
import sys

from mctrack import mctrackstream

logging.basicConfig(filename='mctracker360.log', level=logging.INFO)
DEFAULT_CONSUMER_KAFKA_BOOTSTRAP_SERVER_URL = "kafka"
DEFAULT_PRODUCER_KAFKA_BOOTSTRAP_SERVER_URL = "kafka"

DEFAULT_CONSUMER_KAFKA_TOPIC = "metromind-raw"
DEFAULT_PRODUCER_KAFKA_TOPIC = "metromind-start"

DEFAULT_MCTRACKER_CONFIG_FILE = "config/config_360d.json"
DEFAULT_STREAM_CONFIG_FILE = "config/config_360d_stream.json"

mctrack_obj = None


def signal_handler(signum, _):
    """Signal handler. This function will dump all tracker stats and exit

    Arguments:
        signum {int} -- The signal number
        frame {list} -- Stack frame
    """

    logging.error("Multicam tracker got a signal: %d", signum)
    try:
        if mctrack_obj is not None:
            mctrack_obj.dump_stats()
    except Exception:
        pass
    exit()


def main():
    """Main function. Starts multicam tracker and runs continiously
    until killed
    """
    global mctrack_obj
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Config file for mctracker",
                        default=DEFAULT_MCTRACKER_CONFIG_FILE)
    parser.add_argument("-s", "--sconfig", help="Config file for streaming setup",
                        default=DEFAULT_STREAM_CONFIG_FILE)
    args = parser.parse_args()

    stream_config = None
    try:
        stream_config = json.load(open(args.sconfig))
    except IOError as ioe:
        err_msg = "ERROR: Stream Config I/O Error({}): {}: {}. Quitting".format(
            ioe.errno, args.sconfig, ioe.strerror)
        logging.error(err_msg)
        print(err_msg)
        exit()

    except:
        err_msg = "ERROR: Stream Config Error: {}: {}. Quitting".format(
            args.sconfig, sys.exc_info()[0])
        logging.error(err_msg)
        print(err_msg)
        exit()

    print(stream_config)
    ckafka = (stream_config
              .get("msgBrokerConfig", {})
              .get("inputKafkaServerUrl",
                   DEFAULT_CONSUMER_KAFKA_BOOTSTRAP_SERVER_URL))

    pkafka = (stream_config
              .get("msgBrokerConfig", {})
              .get("outputKafkaServerUrl",
                   DEFAULT_PRODUCER_KAFKA_BOOTSTRAP_SERVER_URL))

    itopic = (stream_config
              .get("msgBrokerConfig", {})
              .get("inputKafkaTopic", DEFAULT_CONSUMER_KAFKA_TOPIC))

    otopic = (stream_config
              .get("msgBrokerConfig", {})
              .get("outputKafkaTopic",
                   DEFAULT_CONSUMER_KAFKA_TOPIC))
    time_it_flag = stream_config.get("profileTime", False)

    print("Starting MC-Streaming app with following args:\n"
          "consumer kafka server={}\n"
          "consumer kafka topic={}\n"
          "producer kafka server={}\n"
          "producer kafka topic={}\n"
          "Time profile={}\n"
          "MC Tracker Config File={}\n".format(ckafka, itopic,
                                               pkafka, otopic,
                                               time_it_flag,
                                               args.config))

    # Set the signal handler for ctrl-c. Since the program runs indefinitely,
    # we need to dump some stats when sigint is received
    # (when profiling is enabled)
    signal.signal(signal.SIGINT, signal_handler)

    mctrack_obj = mctrackstream.McTrackerStream(ckafka, itopic,
                                                pkafka, otopic,
                                                args.config, time_it_flag)
    mctrack_obj.start_mctracker()


if __name__ == "__main__":
    main()
