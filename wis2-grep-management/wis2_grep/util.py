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

import logging

LOGGER = logging.getLogger(__name__)


def detect_message_type(msg_dict: dict) -> str:
    """
    Helper function to detect a message type

    :param msg_dict: `dict` of message

    :returns: `str` of message type (wnm or wmem)

    """

    mtype = None

    if 'http://wis.wmo.int/spec/wnm/1/conf/core' in msg_dict.get('conformsTo', []):  # noqa
        mtype = 'wnm'
    elif 'http://wis.wmo.int/spec/wme/1/conf/monitoring-event-message-core' in msg_dict.get('data', {}).get('conformsTo', []):  # noqa
        mtype = 'wmem'

    return mtype
