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

from concurrent.futures import ThreadPoolExecutor
import logging

from pywis_pubsub.hook import Hook
import redis

from wis2_grep.env import (CACHE_URL, CACHE_RETENTION_SECONDS,
                           MANAGEMENT_WORKERS)
from wis2_grep.loader import Loader
from wis2_grep.util import detect_message_type

EXECUTOR = ThreadPoolExecutor(max_workers=MANAGEMENT_WORKERS)

LOGGER = logging.getLogger(__name__)

CACHE_POOL = redis.ConnectionPool.from_url(CACHE_URL, protocol=2)
CACHE_CLIENT = redis.Redis(connection_pool=CACHE_POOL)


class MessageHook(Hook):
    def execute(self, topic: str, msg_dict: dict) -> None:
        EXECUTOR.submit(self._execute, topic, msg_dict)

    def _execute(self, topic: str, msg_dict: dict) -> None:
        LOGGER.debug('Message hook execution begin')
        LOGGER.debug('Deduplicating message')

        mtype = detect_message_type(msg_dict)

        if mtype == 'wnm':
            value = msg_dict['properties']['data_id']

        elif mtype == 'wmem':
            value = f"{msg_dict['source']}__{msg_dict['subject']}__{msg_dict['time']}"  # noqa

        result = CACHE_CLIENT.set(msg_dict['id'],
                                  value,
                                  nx=True,
                                  ex=CACHE_RETENTION_SECONDS)

        if result:
            LOGGER.info(f"New message {msg_dict['id']}; adding")
            loader = Loader()
            loader.load(msg_dict, topic)
        else:
            LOGGER.info(f"Duplicate message {msg_dict['id']}; skipping")

        LOGGER.debug('Message hook execution end')

    def __repr__(self):
        return '<MessageHook>'
