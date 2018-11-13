"""
Multicam tracking module that consumes the data from kafka, tracks the object,
and puts it back into another kafka topic
"""
__version__ = '0.2'

import json
import logging
import time
from timeit import default_timer as timer
from datetime import datetime

import pandas as pd
from kafka import KafkaConsumer, KafkaProducer, errors

from . import constants, ioutils, mctracker, validation

DEFAULT_KAFKA_LOGS_FILE = "consumerlog.csv"
DEFAULT_TRACKER_LOGS_FILE = "mctracker_log.csv"


class McTrackerStream:
    """
    The main class for streaming multicam tracker

    Instance variables stored:
    1. mctracker_obj {MulticamTracker} -- The multi-cam tracker object
    2. in_kafkaservers {string} -- Input kafka bootstrap servers
    3. in_kafkatopics {string} -- Input kafka topic
    4. out_kafkaservers {string} -- Output kafka bootstrap servers
    5. out_kafkatopics {string} -- Output kafka topic
    6. config {dict} -- Config dictionary for MulticamTracker
    7. ignore_dict{dict} -- dictionary of regions to
                be ignored. It will be in the format:
                    key = camera name
                    value = list of polygons to be ignored
    """

    def __init__(self, in_kafkaservers, in_kafkatopics, out_kafkaservers,
                 out_kafkatopics, config_file, time_prof_flag=False):
        """
        Initialize Streaming MC tracker
        Arguments:
            in_kafkaservers {string} -- Input kafka bootstrap servers
            in_kafkatopics {string} -- Input kafka topic
            out_kafkaservers {string} -- Output kafka bootstrap servers
            out_kafkatopics {string} -- Output kafka topic
            config_file {string} -- The multicam tracker config file
            time_prof_file {boolean} -- Flag (True/False) to enable/disable
                time profiling
        """
        self.in_kafkaservers = in_kafkaservers
        self.in_kafkatopics = in_kafkatopics
        self.out_kafkaservers = out_kafkaservers
        self.out_kafkatopics = out_kafkatopics
        self.time_prof_flag = time_prof_flag
        self.config = json.load(open(config_file))
        self.ignore_dict = self.config.get(
            "IGNORE_DETECTION_DICT_MOVING", {})
        # One time creation of polygons
        self.ignore_poly_dict = ioutils.create_poly_dict(self.ignore_dict)

        # Schema validation
        self.schema = None
        self.schema_validator = None
        self.schema_file_name = self.config.get("JSON_SCHEMA_FILE", None)
        if self.schema_file_name is not None:
            try:
                with open(self.schema_file_name) as schema_file:
                    self.schema = json.load(schema_file)
            except IOError:
                logging.error(
                    "ERROR: Schema file (%s) could not be opened. "
                    "No validation will be performed", self.schema_file_name)
            except ValueError:
                logging.error(
                    "ERROR: Schema file (%s) has invalid json. "
                    "No validation will be performed", self.schema_file_name)

        self.sleep_time_sec = self.config.get(
            "resample_time_sec", constants.RESAMPLE_TIME_IN_SEC)
        self.mctracker_obj = mctracker.MulticamTracker(self.config)

        # Debug related
        self.reid_timings = []

        # Instantiate kafka producer/consumer
        self.consumer = None
        self.producer = None
        try:
            self.consumer = KafkaConsumer(self.in_kafkatopics,
                                          bootstrap_servers=self.in_kafkaservers,
                                          value_deserializer=lambda m:
                                          validation.schema_validate(m, self.schema))
        except errors.NoBrokersAvailable:
            err_msg = "ERROR: Consumer broker not available: {}".format(
                self.in_kafkaservers)
            logging.error(err_msg)
            print("Cannot start streaming multitracker: {}".format(err_msg))
            exit()
        except Exception as exception:
            err_msg = "ERROR: Consumer cannot be started. Unknown error: {}".format(
                exception)
            logging.error(err_msg)
            print("Cannot start streaming multitracker: {}".format(err_msg))
            exit()

        if self.consumer is None:
            err_msg = "ERROR: Consumer cannot be instantiated. Unknown error"
            logging.error(err_msg)
            print("Cannot start streaming multitracker: {}".format(err_msg))
            exit()

        try:
            self.producer = KafkaProducer(bootstrap_servers=self.out_kafkaservers,
                                          value_serializer=lambda m:
                                          json.dumps(m).encode('utf-8'))
        except errors.NoBrokersAvailable:
            err_msg = "ERROR: Producer broker not available: {}".format(
                self.out_kafkaservers)
            logging.error(err_msg)
            print("Cannot start streaming multitracker: {}".format(err_msg))
            exit()
        except Exception as exception:
            err_msg = "ERROR: Producer cannot be started. Unknown error: {}".format(
                exception)
            logging.error(err_msg)
            print("Cannot start streaming multitracker: {}".format(err_msg))
            exit()

        if self.producer is None:
            err_msg = "ERROR: Producer cannot be instantiated. Unknown error"
            logging.error(err_msg)
            print("Cannot start streaming multitracker: {}".format(err_msg))
            exit()

    def start_mctracker(self):
        """
        This method:
        1. Continiously listens to an input kafka (given by in_kafkaservers and
        in_kafkatopics)
        2. Performs multicam tracking
        3. Writes the tracked objects to another kafka (given by out_kafkaservers
        and out_kafkatopics)
        """

        iters = 0
        num_msgs_received = 0
        recs = []
        # Debugging-related objects
        start_time = tstart_time = ptime_taken = ttime_taken = None
        num_iters_to_print = int(
            constants.APPROX_TIME_PERIOD_TO_PRINT_INFO_IN_SEC /
            float(self.sleep_time_sec))

        while True:
            if self.time_prof_flag:
                tstart_time = time.time()

            raw_messages = self.consumer.poll(
                timeout_ms=self.sleep_time_sec*1000.0, max_records=5000)

            start_time = time.time()
            json_list = []
            for _, msg_list in raw_messages.items():
                num_msgs_received += len(msg_list)
                for msg in msg_list:
                    curr_time = int(round(time.time() * 1000))
                    kafka_ts = msg.timestamp
                    recs.append({'currTime': curr_time, 'kafkaTs': kafka_ts})
                    json_list.append(msg.value)

            if self.time_prof_flag:
                pstart_time = time.time()

            retval = self.track_list(json_list)
            time_taken = time.time() - start_time

            if self.time_prof_flag:
                ptime_taken = time.time() - pstart_time
                ttime_taken = time.time() - tstart_time

                res = {'currTime': start_time, 'count': len(json_list),
                       'timeTakenMs': time_taken * 1000.0,
                       'reidTimeTakenMs': ptime_taken*1000.0,
                       'totalTimeTakenMs': ttime_taken * 1000.0,
                       "num_unidentified_cars":
                       len(self.mctracker_obj.state.unidentified_cars),
                       "num_prev_list":
                       len(self.mctracker_obj.state.prev_list),
                       "num_carry_over_list":
                       len(self.mctracker_obj.state.carry_over_list),
                       "num_retval":
                       len(retval),
                       "num_match_stats":
                       len(self.mctracker_obj.state.match_stats),
                       "num_possible_parked_cars":
                       len(self.mctracker_obj.state.possible_parked_cars)}
                self.reid_timings.append(res)

            iters += 1
            if (iters % num_iters_to_print) == 0:
                logging.info(
                    "Mc-Tracker Stream: %s: Num msgs received = %d", str(datetime.now()), num_msgs_received)
            if retval:
                self.write_to_kafka(retval)

            time_taken = time.time() - start_time
            tts = self.sleep_time_sec - time_taken
            if tts > 0:
                time.sleep(tts)

        if self.time_prof_flag:
            if recs:
                recs_pd = pd.DataFrame(recs)
                recs_pd['kafkaTsDelayMs'] = recs_pd["currTime"] - \
                    recs_pd["kafkaTs"]
                recs_pd.to_csv(DEFAULT_KAFKA_LOGS_FILE, index=False)
                logging.debug("%s", str(recs_pd.describe(percentiles=[
                    0.05, 0.1, 0.25, 0.5, 0.75, 0.90, 0.95])))
            else:
                logging.debug("No data received")

    def dump_stats(self):
        """
        Write all the tracking timings into the file specified by
        DEFAULT_TRACKER_LOGS_FILE
        """
        if self.reid_timings:
            recs_pd = pd.DataFrame(self.reid_timings)
            recs_pd.to_csv(DEFAULT_TRACKER_LOGS_FILE, index=False)
            logging.debug("%s", str(recs_pd.describe(percentiles=[
                0.05, 0.1, 0.25, 0.5, 0.75, 0.90, 0.95])))
        else:
            logging.debug("No data received")

    def track_list(self, all_json_list):
        """
        This method performs the reid for a given set of detection records
        (all_json_list). It returns re-identified set of json objects.
        Note that all the ignorable-points (corresponding to configuration of
        self.ignore_dict will not be processed)

        Arguments:

            all_json_list {list} -- List of all detections in day2 schema format
        Returns:
            list -- List of all tracked detections in day2 schema format
        """
        retval = []
        all_json_list = validation.ignore_bad_records(all_json_list)
        all_json_list, ignored_list = ioutils.ignore_false_detections(
            all_json_list, self.ignore_poly_dict)

        # Debugging-related objects
        start_time = end_time = None

        if all_json_list:
            if self.time_prof_flag:
                start_time = timer()

            all_json_list.sort(
                key=lambda json_ele: json_ele.get("@timestamp", None))
            self.mctracker_obj.process_batch(all_json_list)

            if self.time_prof_flag:
                end_time = timer()
                logging.info(
                    "Mc-Tracker Stream: Time taken: %f",
                    (end_time - start_time))

            tmp_ret = self.mctracker_obj.state.retval
            if tmp_ret is not None:
                self.mctracker_obj.remove_all_additional_fields(tmp_ret)
                retval += tmp_ret
                self.mctracker_obj.state.retval = []

        return retval

    def write_to_kafka(self, json_list):
        """
        Write the tracked detections to kafka topic

        Arguments:
            json_list {list} -- the list of detections in day2 schema
        """
        if self.producer is not None:
            for json_ele in json_list:
                self.producer.send(self.out_kafkatopics, json_ele)
