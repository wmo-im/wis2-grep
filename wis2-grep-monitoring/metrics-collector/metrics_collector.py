###############################################################################
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
###############################################################################

import json
import logging
import os
import sys
from urllib.parse import urlparse

import paho.mqtt.client as mqtt_client
from prometheus_client import (
    Gauge, start_http_server, REGISTRY, GC_COLLECTOR,
    PLATFORM_COLLECTOR, PROCESS_COLLECTOR
)

REGISTRY.unregister(GC_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(PROCESS_COLLECTOR)

BROKER_URL = os.environ['WIS2_GREP_BROKER_URL']
HTTP_PORT = 8006
LOGGING_LEVEL = os.environ['WIS2_GREP_LOGGING_LEVEL']

logging.basicConfig(stream=sys.stdout)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(LOGGING_LEVEL)

# sets metrics as per https://github.com/wmo-im/wis2-metric-hierarchy/blob/main/metric-hierarchy/grep.csv  # noqa

METRIC_MESSAGES_PROCESSED_TOTAL = Gauge(
    'wmo_wis2_grep_messages_processed_total',
    'Number of messages processed',
    ['centre_id', 'report_by', 'topic']
)


def init_metrics() -> None:
    """
    Initializes metrics on startup

    :returns: `None`
    """

    pass


def collect_metrics() -> None:
    """
    Subscribe to MQTT wis2-grep/metrics and collect metrics

    :returns: `None`
    """

    def _sub_connect(client, userdata, flags, rc):
        LOGGER.info('Subscribing to topic wis2-grep/metrics/#')
        client.subscribe('wis2-grep/metrics/#', qos=0)

    def _sub_message(client, userdata, msg):
        LOGGER.debug('Processing message')
        topic = msg.topic
        payload = json.loads(msg.payload)
        labels = payload['labels']
        value = payload.get('value')
        LOGGER.debug(f'Topic: {topic}')
        LOGGER.debug(f"Labels: {labels}")
        LOGGER.debug(f"Value: {value}")

        if topic == 'wis2-grep/metrics/clear':
            LOGGER.info('Clearing all metrics')
            METRIC_MESSAGES_PROCESSED_TOTAL.clear()
        elif topic == 'wis2-grep/metrics/init':
            LOGGER.info('Initializing metrics')
            init_metrics()
        elif topic == 'wis2-grep/metrics/messages_processed_total':
            METRIC_MESSAGES_PROCESSED_TOTAL.labels(*labels).inc()

    url = urlparse(BROKER_URL)

    client_id = 'wis2-grep metrics collector'

    try:
        LOGGER.info('Setting up MQTT client')
        client = mqtt_client.Client(client_id)
        client.on_connect = _sub_connect
        client.on_message = _sub_message
        client.username_pw_set(url.username, url.password)
        LOGGER.info(f'Connecting to {url.hostname}')
        client.connect(url.hostname, url.port)
        client.loop_forever()
    except Exception as err:
        LOGGER.error(err)


if __name__ == '__main__':
    LOGGER.info(f'Starting metrics collector server on port {HTTP_PORT}')
    start_http_server(HTTP_PORT)
    init_metrics()
    collect_metrics()
