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

FROM geopython/pygeoapi:latest

LABEL maintainer="Tom Kralidis <tomkralidis@gmail.com>"

ENV PYGEOAPI_CONFIG=/pygeoapi/local.config.yml
ENV PYGEOAPI_OPENAPI=/pygeoapi/local.openapi.yml

RUN apt-get update && \
    apt-get install -y curl && \
    /venv/bin/pip3 install pywis-pubsub

COPY ./app.py /pygeoapi/pygeoapi/app.py
COPY ./wis2_grep.py /pygeoapi/pygeoapi/process/wis2_grep.py
COPY ./docker/wis2-grep-api.yml /pygeoapi/local.config.yml
COPY ./docker/entrypoint.sh /app/docker/wis2-grep-api/entrypoint.sh

RUN chmod +x /app/docker/wis2-grep-api/entrypoint.sh && \
    chgrp -R 0 /pygeoapi && \
    chmod -R g=u /pygeoapi

USER 1001

ENTRYPOINT [ "/app/docker/wis2-grep-api/entrypoint.sh" ]
