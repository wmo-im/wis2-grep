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

from wis2_grep.backend import BACKENDS
from wis2_grep.env import (BACKEND_TYPE, BACKEND_CONNECTION,
                           MESSAGE_RETENTION_HOURS)

LOGGER = logging.getLogger(__name__)


class Loader:
    def __init__(self):
        """
        Initializer

        :returns: `wis2_grep.loader.Loader`
        """

        self.backend = BACKENDS[BACKEND_TYPE](
                    {'connection': BACKEND_CONNECTION})

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

        LOGGER.debug('Adding topic to message')
        self.message['properties']['topic'] = topic

        LOGGER.debug(f'Notification message: {json.dumps(self.message, indent=4)}')  # noqa

        LOGGER.info('Publishing notification message to backend')
        self._publish()

    def _publish(self):
        """
        Publish notification message from `wis2_grep.loader.Loader.message`
        to backend

        :returns: `None`
        """

        LOGGER.info(f'Saving to {BACKEND_TYPE} ({BACKEND_CONNECTION})')
        self.backend.save(self.message)

    def __repr__(self):
        return '<Loader>'


@click.command()
@click.pass_context
@click.option('--force', '-f', 'force', is_flag=True, default=False,
              help='Force reinitialization of backend')
@click.option('--yes', '-y', 'bypass', is_flag=True, default=False,
              help='Bypass permission prompts')
@cli_options.OPTION_VERBOSITY
def setup(ctx, force, bypass, verbosity='NOTSET'):
    """Create Global Replay Service backend"""

    backend = BACKENDS[BACKEND_TYPE]({'connection': BACKEND_CONNECTION})
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
@click.option('--yes', '-y', 'bypass', is_flag=True, default=False,
              help='Bypass permission prompts')
@cli_options.OPTION_VERBOSITY
def teardown(ctx, bypass, verbosity='NOTSET'):
    """Delete Global Replay Service backend"""

    if not bypass:
        if not click.confirm('Delete Global Replay Service backend?  This will remove existing collections', abort=True):  # noqa
            return

    backend = BACKENDS[BACKEND_TYPE]({'connection': BACKEND_CONNECTION})
    LOGGER.debug(f'Backend: {backend}')
    backend.teardown()


@click.command()
@click.pass_context
@click.argument(
    'path', type=click.Path(exists=True, dir_okay=True, file_okay=True))
@cli_options.OPTION_VERBOSITY
def load(ctx, path, verbosity='NOTSET'):
    """Load notification message"""

    p = Path(path)

    if p.is_file():
        wnms_to_process = [p]
    else:
        wnms_to_process = p.rglob('*.json')

    for w2p in wnms_to_process:
        click.echo(f'Processing {w2p}')
        with w2p.open() as fh:
            r = Loader()
            r.load(fh.read())


@click.command()
@click.pass_context
@click.option('--hours', type=int, default=MESSAGE_RETENTION_HOURS,
              help='Number of hours of messages to keep')
@cli_options.OPTION_VERBOSITY
def clean(ctx, hours, verbosity):
    """Clean messages on API indexes"""

    hours_ = hours or MESSAGE_RETENTION_HOURS

    if hours_ is None or hours_ < 0:
        click.echo('No data retention set. Skipping')
    else:
        backend = BACKENDS[BACKEND_TYPE]({'connection': BACKEND_CONNECTION})
        LOGGER.debug(f'Backend: {backend}')
        backend.clean(hours_)

        click.echo(f'Deleting messages > {hours_} hour(s) old from {backend}')
