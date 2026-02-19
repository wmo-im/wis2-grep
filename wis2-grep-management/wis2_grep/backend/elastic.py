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
#   https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
###############################################################################

from datetime import datetime, UTC
import logging
from urllib.parse import urlparse

from elasticsearch import Elasticsearch

from wis2_grep.env import MESSAGE_RETENTION_HOURS
from wis2_grep.backend.base import BaseBackend

LOGGER = logging.getLogger(__name__)


class ElasticsearchBackend(BaseBackend):

    from urllib.parse import urlparse
    from elasticsearch import Elasticsearch

    def __init__(self, defs):
        super().__init__(defs)

        self.url_parsed = urlparse(self.defs.get('connection'))
        url2 = f'{self.url_parsed.scheme}://{self.url_parsed.netloc}'

        if self.url_parsed.port is None:
            LOGGER.debug('No port found; trying autodetect')
            port = None
            if self.url_parsed.scheme == 'http':
                port = 80
            elif self.url_parsed.scheme == 'https':
                port = 443
            if port is not None:
                url2 = f'{self.url_parsed.scheme}://{self.url_parsed.netloc}:{port}'  # noqa

        if self.url_parsed.path.count('/') > 1:
            LOGGER.debug('ES URL has a basepath')
            basepath = self.url_parsed.path.split('/')[1]
            self.index_name = self.url_parsed.path.split('/')[-1]
            url2 = f'{url2}/{basepath}/'

        self.index_basename = self.url_parsed.path.lstrip('/')
        self.index_basename = self.index_basename.rstrip('.*')
        self.ilm_lifecycle_policy_name = f'{self.index_basename}_policy'
        self.index_mappings = f'{self.index_basename}_mappings'
        self.index_basename = f'{self.index_basename}.'

        LOGGER.debug(f'ES URL: {url2}')
        LOGGER.debug(f'ES index basename: {self.index_basename}')

        self.ES_MAPPINGS = {
            'mappings': {
                'properties': {
                    'id': {
                        'type': 'text',
                        'fields': {
                            'raw': {
                                'type': 'keyword'
                            }
                        }
                    },
                    'geometry': {
                        'type': 'geo_shape'
                    }
                }
            }
        }

        self.ES_SETTINGS = {
            'index_patterns': [f'{self.index_basename}*'],
            'composed_of': [f'{self.index_mappings}'],
            'priority': 1,
            'template': {
                'settings': {
                    'number_of_shards': 1,
                    'number_of_replicas': 0,
                    'index.lifecycle.name': self.ilm_lifecycle_policy_name
                }
            }
        }

        self.ES_CLUSTER_SETTINGS = {
            'transient': {
                'action.destructive_requires_name': False
            }
        }

        self.ES_ILM_LIFECYCLE_POLICY = {
            'phases': {
                'delete': {
                    'min_age': f'{MESSAGE_RETENTION_HOURS}h',
                    'actions': {
                        'delete': {}
                    }
                }
            }
        }

        settings = {
            'hosts': [url2],
            'retry_on_timeout': True,
            'max_retries': 10,
            'timeout': 30
        }

        if self.url_parsed.username and self.url_parsed.password:
            settings['http_auth'] = (
                self.url_parsed.username, self.url_parsed.password)

        LOGGER.debug(f'Settings: {settings}')
        self.es = Elasticsearch(**settings)

    def setup(self) -> None:
        LOGGER.debug(f'Creating ILM lifecycle policy {self.ilm_lifecycle_policy_name}')  # noqa
        self.es.ilm.put_lifecycle(name=self.ilm_lifecycle_policy_name,
                                  policy=self.ES_ILM_LIFECYCLE_POLICY)

        LOGGER.debug(f'Creating component template {self.index_mappings}')
        self.es.cluster.put_component_template(name=f'{self.index_mappings}',
                                               template=self.ES_MAPPINGS)

        LOGGER.debug('Creating cluster settings')
        self.es.cluster.put_settings(body=self.ES_CLUSTER_SETTINGS)

        LOGGER.debug(f'Creating index template {self.index_basename}')
        self.es.indices.put_index_template(name=self.index_basename,
                                           body=self.ES_SETTINGS)

    def teardown(self) -> None:
        LOGGER.debug(f'Deleting indexes of template {self.index_basename}')
        self.es.indices.delete(index=f'{self.index_basename}*',
                               ignore=[400, 404])

        if self.es.indices.exists_index_template(name=self.index_basename):
            LOGGER.debug(f'Deleting index template {self.index_basename}')
            self.es.indices.delete_index_template(name=self.index_basename)

        LOGGER.debug(f'Deleting component template {self.index_mappings}')
        self.es.cluster.delete_component_template(
            name=f'{self.index_mappings}')

        if self.es.ilm.get_lifecycle(name=self.ilm_lifecycle_policy_name):
            LOGGER.debug(f'Deleting ILM lifecycle policy {self.ilm_lifecycle_policy_name}')  # noqa
            self.es.ilm.delete_lifecycle(name=self.ilm_lifecycle_policy_name)

    def save(self, message: dict) -> None:
        now = datetime.now(UTC).strftime('%Y-%m-%d-%H')
        es_index = f'{self.index_basename}{now}'

        LOGGER.debug(f"Indexing message {message['id']} to index {es_index}")
        self.es.index(index=es_index, id=message['id'], body=message)

    def exists(self) -> bool:
        LOGGER.debug('Checking whether backend exists')

        return self.es.indices.exists_index_template(name=self.index_basename)

    def clean(self, hours: int) -> None:
        LOGGER.debug('Elasticsearch cleaning is managed internally by ILM')
        pass

    def __repr__(self):
        return '<ElasticsearchBackend>'
