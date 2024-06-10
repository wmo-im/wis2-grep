# =================================================================
#
# Authors: Tom Kralidis <tomkralidis@gmail.com>
#
# Copyright (c) 2024 Tom Kralidis
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

import json
import logging
import os
import requests

from pywis_pubsub.mqtt import MQTTPubSubClient

from pygeoapi.process.base import BaseProcessor, ProcessorExecuteError

API_ENDPOINT = 'http://localhost/collections/wis2-notification-messages/items'

BROKER_URL = os.environ['WIS2_GREP_BROKER_URL']

MQTT_CLIENT = MQTTPubSubClient(BROKER_URL)

LOGGER = logging.getLogger(__name__)

#: Process metadata and description
PROCESS_METADATA = {
    'version': '0.1.0',
    'id': 'wis2-grep-subscriber',
    'title': {
        'en': 'Global Replay subscriber',
        'fr': 'Global Replay subscriber'
    },
    'description': {
        'en': 'A process that allows for user-defined subscription to '
              'replay WIS2 notification messages',
        'fr': 'A process that allows for user-defined subscription to '
              'replay WIS2 notification messages'
    },
    'jobControlOptions': ['sync-execute', 'async-execute'],
    'keywords': ['wis2-grep', 'subscribe', 'notifications'],
    'links': [{
        'type': 'text/html',
        'rel': 'canonical',
        'title': 'wis2grep information',
        'href': 'https://github.com/wmo-im/wis2-grep',
        'hreflang': 'en-US'
    }, {
        'type': 'text/html',
        'rel': 'related',
        'title': 'WIS2 information',
        'href': 'https://wmo-im.github.io/wis2-guide',
        'hreflang': 'en-US'
    }],
    'inputs': {
        'topic': {
            'title': 'Topic',
            'description': 'The topic to subscribe to',
            'schema': {
                'type': 'string'
            },
            'minOccurs': 1,
            'maxOccurs': 1,
            'keywords': ['topic', 'mqtt']
        },
        'datetime': {
            'title': 'Datetime',
            'description': 'Datetime (RFC3339) instant or envelope',
            'schema': {
                'type': 'string'
            },
            'minOccurs': 1,
            'maxOccurs': 1,
            'keywords': ['datetime', 'rfc3339']
        },
        'subscriber-id': {
            'title': 'Subscriber id',
            'description': 'identifier of subscribe, used in response topic',
            'schema': {
                'type': 'string'
            },
            'minOccurs': 1,
            'maxOccurs': 1,
            'keywords': ['subscriber']
        }
    },
    'outputs': {
        'subscription': {
            'title': 'Subscription reponse',
            'description': 'Response of subscription result',
            'schema': {
                'type': 'object',
                'contentMediaType': 'application/json',
                'properties': {
                    'status': {
                        'type': 'string',
                        'description': 'Result of subscription request'
                    },
                    'subscription': {
                        'type': 'object',
                        'required': [
                            'href',
                            'rel'
                        ],
                        'properties': {
                            'href': {
                                'type': 'string',
                                'example': 'http://data.example.com/buildings/123'  # noqa
                            },
                            'rel': {
                                'type': 'string',
                                'example': 'alternate'
                            },
                            'type': {
                                'type': 'string',
                                'example': 'application/geo+json'
                            },
                            'title': {
                                'type': 'string',
                                'example': 'Trierer Strasse 70, 53115 Bonn'
                            },
                            'channel': {
                                'type': 'string',
                                'description': 'topic to subscribe to for broker workflow'  # noqa
                            }
                        }
                    }
                }
            }
        }
    },
    'example': {
        'inputs': {
            'topic': 'origin/a/wis2/fr-meteofrance',
            'datetime': '2024-06-10T03:00:00Z/2024-06-10T06:00:00Z',
            'subscriber-id': 'foobar123'
        }
    }
}


class WIS2GrepSubscriberProcessor(BaseProcessor):
    """wis2-grep Subscriber"""

    def __init__(self, processor_def):
        """
        Initialize object

        :param processor_def: provider definition

        :returns: pygeoapi.process.wis2_grep.WIS2GrepSubscriberProcessor
        """

        super().__init__(processor_def, PROCESS_METADATA)
        self.supports_outputs = True

    def execute(self, data):
        datetime_ = data.get('datetime')
        topic = data.get('topic')
        subscriber_id = data.get('subscriber-id')

        if None in [datetime_, topic, subscriber_id]:
            msg = 'datetime/topic/subscriber-id required'
            raise ProcessorExecuteError(msg)

        outputs = {}
        pub_topic = f'replay/a/wis2/{subscriber_id}'

        api_params = {
            # 'datetime': datetime_
            'topic': topic,
        }

        try:
            r = requests.get(API_ENDPOINT, params=api_params).json()
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            LOGGER.error(err)
            outputs['status'] = 'failed'
            outputs['description'] = err
            return 'application/json', outputs

        outputs['status'] = 'successful'
        outputs['subscription'] = {
            'rel': 'items',
            'type': 'application/geo+json',
            'href': BROKER_URL,
            'title': 'User-defined notifications',
            'channel': pub_topic
        }

        for feature in r['features']:
            MQTT_CLIENT.pub(pub_topic, json.dumps(feature))

        return 'application/json', outputs

    def __repr__(self):
        return f'<WIS2GrepSubscriberProcessor> {self.name}'
