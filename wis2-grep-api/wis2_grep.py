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

from datetime import datetime, timedelta
import json
import logging
import os
import threading
import uuid

from pywis_pubsub.mqtt import MQTTPubSubClient
import requests

from pygeoapi.process.base import BaseProcessor, ProcessorExecuteError

API_URL_DOCKER = os.environ['WIS2_GREP_API_URL_DOCKER']
BROKER_URL = os.environ['WIS2_GREP_BROKER_URL']
CENTRE_ID = os.environ['WIS2_GREP_CENTRE_ID']

API_ENDPOINT = f'{API_URL_DOCKER}/collections/wis2-notification-messages/items'

MQTT_CLIENT = MQTTPubSubClient(BROKER_URL)
MQTT_CLIENT.client_id = 'wis2-grep-api-client'

LOGGER = logging.getLogger(__name__)

GB_LINKS = []

EXAMPLE_UUID = str(uuid.uuid4())
NOW = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
TWO_HOURS_AGO = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')  # noqa

for key, value in os.environ.items():
    if key.startswith('WIS2_GREP_GB_LINK'):
        # centre_id, url, title = value.rsplit(',', 2)
        GB_LINKS.append(value.split(',', 2))


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
        'title': 'wis2-grep information',
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
            'description': 'Topic to subscribe to',
            'schema': {
                'type': 'string',
                'example': 'cache/a/wis2/meteofrance'
            },
            'minOccurs': 1,
            'maxOccurs': 1,
            'keywords': ['topic', 'mqtt']
        },
        'datetime': {
            'title': 'Datetime',
            'description': 'Datetime (RFC3339) instant or envelope',
            'schema': {
                'type': 'string',
                'format': 'date-time',
                'example': f'{TWO_HOURS_AGO}/{NOW}'
            },
            'minOccurs': 1,
            'maxOccurs': 1,
            'keywords': ['datetime', 'rfc3339']
        },
        'subscriber-id': {
            'title': 'Subscriber id',
            'description': 'UUID of subscriber, used in response topic',
            'schema': {
                'type': 'string',
                'format': 'uuid',
                'example': EXAMPLE_UUID
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
                    'subscriptions': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'required': [
                                'href',
                                'rel'
                            ],
                            'properties': {
                                'href': {
                                    'type': 'string',
                                    'description': 'MQTT endpoint',
                                    'example': GB_LINKS[0][1]
                                },
                                'rel': {
                                    'type': 'string',
                                    'description': 'link relation',
                                    'example': 'alternate'
                                },
                                'type': {
                                    'type': 'string',
                                    'description': 'media type',
                                    'example': 'application/geo+json'
                                },
                                'title': {
                                    'type': 'string',
                                    'description': 'title of link',
                                    'example': GB_LINKS[0][2]
                                },
                                'channel': {
                                    'type': 'string',
                                    'description': 'topic to subscribe to',
                                    'example': f'replay/a/wis2/{EXAMPLE_UUID}'
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    'example': {
        'inputs': {
            'topic': 'cache/a/wis2/fr-meteofrance',
            'datetime': f'{TWO_HOURS_AGO}/{NOW}',
            'subscriber-id': EXAMPLE_UUID
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

    def execute(self, data, outputs=None):
        datetime_ = data.get('datetime')
        topic = data.get('topic')
        subscriber_id = data.get('subscriber-id')

        LOGGER.debug('Sanitizing topic')
        api_topic = topic.replace('/#', '').replace('+', '*')

        if None in [datetime_, topic, subscriber_id]:
            msg = 'datetime/topic/subscriber-id required'
            LOGGER.error(msg)
            raise ProcessorExecuteError(msg)

        if len(topic.split('/')) < 4:
            msg = 'topic level minimum of centre-id required'
            LOGGER.error(msg)
            raise ProcessorExecuteError(msg)

        try:
            LOGGER.debug('Validating subscriber-id')
            uuid.UUID(subscriber_id)
        except ValueError:
            raise ProcessorExecuteError('Invalid UUID')

        outputs = {}
        pub_topic = f'replay/a/wis2/{CENTRE_ID}/{subscriber_id}'

        api_params = {
            'datetime': datetime_,
            'topic': api_topic,
            'limit': 100000
        }

        LOGGER.debug('Sending API query to thread')
        t = threading.Thread(target=self._get_messages,
                             args=(api_params, pub_topic))
        t.start()

        outputs['status'] = 'successful'
        outputs['subscriptions'] = []

        for gb_link in GB_LINKS:
            outputs['subscriptions'].append({
                'rel': 'items',
                'type': 'application/geo+json',
                'href': gb_link[1],
                'title': gb_link[2],
                'channel': pub_topic
            })

        return 'application/json', outputs

    def _get_messages(self, api_params, pub_topic) -> None:
        """
        Utility to fetch all messages from API

        :param api_params: `dict` of API query parameters
        :param pub_topic: `str` of publication topic

        :returns: `None`
        """

        next_link = None
        found_next_link = False

        while True:
            try:
                if next_link is None:
                    LOGGER.debug(f'Querying API with {api_params}')
                    r = requests.get(API_ENDPOINT, params=api_params)
                else:
                    LOGGER.debug(f'Querying API with {next_link}')
                    r = requests.get(next_link)

                r.raise_for_status()
                r = r.json()

                for feature in r['features']:
                    MQTT_CLIENT.pub(pub_topic, json.dumps(feature))

                for link in r['links']:
                    if 'next' in link:
                        next_link = link['next']
                        found_next_link = True

                if not found_next_link:
                    break

            except requests.exceptions.HTTPError as err:
                LOGGER.error(err)

    def __repr__(self):
        return f'<WIS2GrepSubscriberProcessor> {self.name}'
