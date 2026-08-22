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
from pathlib import Path
from typing import Union

import click

from pywis_pubsub import cli_options
from pywis_pubsub.mqtt import MQTTPubSubClient

from wis2_grep.backend import BACKENDS
from wis2_grep.env import (BACKEND_TYPE, BACKEND_CONNECTION, BROKER_URL,
                           CENTRE_ID, INCLUDE_GATEWAYS,
                           MESSAGE_RETENTION_HOURS)
from wis2_grep.util import detect_message_type

LOGGER = logging.getLogger(__name__)

METRICS_PUBSUB_CLIENT = MQTTPubSubClient(BROKER_URL)

WNM_BACKEND = BACKENDS[BACKEND_TYPE]({
    'connection': BACKEND_CONNECTION,
    'index': 'wis2-notification-messages'
})

WME_BACKEND = BACKENDS[BACKEND_TYPE]({
    'connection': BACKEND_CONNECTION,
    'index': 'wis2-monitoring-event-messages'
})


class Loader:
    def __init__(self):
        """
        Initializer

        :returns: `wis2_grep.loader.Loader`
        """

        self.index = None
        self.backend = None

    def load(self, message: Union[dict, str], topic: str = None) -> None:
        """
        Register a notification message

        :param message: `dict` or `str` of notification message
        :param topic: `str` of incoming topic (default is `None`)

        :returns: `None`
        """

        if isinstance(message, dict):
            LOGGER.debug('Notification message is already a dict')
            self.message = message
        elif isinstance(message, str):
            LOGGER.debug('Notification message is a string; parsing')
            try:
                self.message = json.loads(message)
            except json.decoder.JSONDecodeError as err:
                LOGGER.warning(err)
                return

        centre_id = topic.split('/')[3]
        if centre_id.endswith('-gts-to-wis2') and not INCLUDE_GATEWAYS:
            msg = 'Discarding GTS to WIS2 Gateway messages from {centre_id}'
            LOGGER.debug(msg)
            return

        LOGGER.debug('Adding topic to message')
        mtype = detect_message_type(self.message)

        if mtype == 'wnm':
            self.index = 'wis2-notification-messages'
            self.message['properties']['topic'] = topic
            self.backend = WNM_BACKEND
        elif mtype == 'wmem':
            self.index = 'wis2-monitoring-event-messages'
            self.message['topic'] = topic
            self.message['properties'] = {
                'topic': topic,
                'time': self.message['time']
            }
            self.backend = WME_BACKEND

        LOGGER.debug(f'Notification message: {self.message}')

        LOGGER.info('Publishing notification message to backend')
        LOGGER.debug(f'Backend: {self.backend}')

        self._publish()
        self._publish_metrics(topic)

    def _publish(self) -> None:
        """
        Publish notification message from `wis2_grep.loader.Loader.message`
        to backend

        :returns: `None`
        """

        LOGGER.info(f'Saving to {BACKEND_TYPE} ({BACKEND_CONNECTION})')
        self.backend.save(self.message)

    def _publish_metrics(self, topic: str) -> None:
        """
        Publish metrics

        :param topic: `str` of incoming topic (default is `None`)

        :returns: `None`
        """

        message = {
            'labels': [
                topic.split('/')[3],
                CENTRE_ID,
                topic
            ]
        }

        publish_metrics_topic = 'wis2-grep/metrics/messages_processed_total'
        METRICS_PUBSUB_CLIENT.pub(publish_metrics_topic, json.dumps(message))

    def __repr__(self):
        return '<Loader>'


@click.command()
@click.pass_context
@click.argument('index')
@click.option('--force', '-f', 'force', is_flag=True, default=False,
              help='Force reinitialization of backend')
@click.option('--yes', '-y', 'bypass', is_flag=True, default=False,
              help='Bypass permission prompts')
@cli_options.OPTION_VERBOSITY
def setup(ctx, index, force, bypass, verbosity='NOTSET'):
    """Create Global Replay Service backend"""

    backend_defs = {'connection': BACKEND_CONNECTION, 'index': index}
    backend = BACKENDS[BACKEND_TYPE](backend_defs)
    LOGGER.debug(f'Backend: {backend}')

    if backend.exists():
        if not force:
            click.echo('Backend already exists')
            return
        else:
            if bypass:
                click.echo('Reinitializing backend')
                backend.teardown()
                backend.setup()
            else:
                msg = ('Recreate backend?  This will delete all metadata '
                       'and delete/setup/reinitialize the backend.')

                if not click.confirm(msg, abort=True):
                    click.echo('Not reinitializing backend')
                    return
                else:
                    click.echo('Reinitializing backend')
                    backend.teardown()
                    backend.setup()
    else:
        click.echo('Setting up backend')
        backend.setup()

    click.echo('Done')


@click.command()
@click.pass_context
@click.argument('index')
@click.option('--yes', '-y', 'bypass', is_flag=True, default=False,
              help='Bypass permission prompts')
@cli_options.OPTION_VERBOSITY
def teardown(ctx, index, bypass, verbosity='NOTSET'):
    """Delete Global Replay Service backend"""

    if not bypass:
        if not click.confirm('Delete Global Replay Service backend?  This will remove index {index}', abort=True):  # noqa
            return

    backend_defs = {'connection': BACKEND_CONNECTION, 'index': index}
    backend = BACKENDS[BACKEND_TYPE](backend_defs)
    LOGGER.debug(f'Backend: {backend}')
    backend.teardown()


@click.command()
@click.pass_context
@click.argument('index')
@cli_options.OPTION_VERBOSITY
def get_retention(ctx, index, verbosity='NOTSET'):
    """Get current retention settings"""

    backend_defs = {'connection': BACKEND_CONNECTION, 'index': index}
    backend = BACKENDS[BACKEND_TYPE](backend_defs)
    LOGGER.debug(f'Backend: {backend}')

    retention = backend.get_retention()

    click.echo(f'Retention is currently set to {retention} hours for index {index}')  # noqa

    click.echo('Done')


@click.command()
@click.pass_context
@click.argument('index')
@click.argument('hours', type=int)
@cli_options.OPTION_VERBOSITY
def set_retention(ctx, index, hours, verbosity='NOTSET'):
    """Get current retention settings"""

    backend_defs = {'connection': BACKEND_CONNECTION, 'index': index}
    backend = BACKENDS[BACKEND_TYPE](backend_defs)
    LOGGER.debug(f'Backend: {backend}')

    click.echo(f'Setting retention to {hours} hours on index {index}')

    backend.set_retention(hours)
    ctx.invoke(get_retention, index=index)


@click.command()
@click.pass_context
@click.argument(
    'path', type=click.Path(exists=True, dir_okay=True, file_okay=True))
@cli_options.OPTION_VERBOSITY
def load(ctx, path, verbosity='NOTSET'):
    """Load notification message"""

    p = Path(path)

    if p.is_file():
        messages_to_process = [p]
    else:
        messages_to_process = p.rglob('*.json')

    for m2p in messages_to_process:
        click.echo(f'Processing {m2p}')
        with m2p.open() as fh:
            r = Loader()
            r.load(fh.read())


@click.command()
@click.pass_context
@click.argument('index')
@click.option('--hours', type=int, default=MESSAGE_RETENTION_HOURS,
              help='Number of hours of messages to keep')
@cli_options.OPTION_VERBOSITY
def clean(ctx, index, hours, verbosity):
    """Clean messages on API indexes"""

    hours_ = hours or MESSAGE_RETENTION_HOURS

    if hours_ is None or hours_ < 0:
        click.echo('No data retention set. Skipping')
    else:
        backend_defs = {'connection': BACKEND_CONNECTION, 'index': index}
        backend = BACKENDS[BACKEND_TYPE](backend_defs)
        LOGGER.debug(f'Backend: {backend}')
        backend.clean(hours_)

        click.echo(f'Deleting messages > {hours_} hour(s) old from {backend}')
