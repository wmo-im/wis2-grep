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

FROM ubuntu:focal

LABEL maintainer="tomkralidis@gmail.com"

ENV TZ="Etc/UTC" \
    DEBIAN_FRONTEND="noninteractive" \
    DEBIAN_PACKAGES="bash cron curl git python3-pip python3-setuptools sudo vim"

# copy the app
COPY ./ /app

# add to crontab
COPY ./docker/wis2-grep-management.cron /var/spool/cron/crontabs/wis2-grep

RUN apt-get update -y && \
    # install dependencies
    apt-get install -y ${DEBIAN_PACKAGES} && \
    pip3 install --no-cache-dir -r /app/requirements-backend.txt && \
    # install wis2-grep
    cd /app && \
    pip3 install -e . && \
    chmod +x /app/docker/entrypoint.sh && \
    # cleanup
    apt autoremove -y && \
    apt-get -q clean && \
    rm -rf /var/lib/apt/lists/* && \
    chmod 0644 /var/spool/cron/crontabs/wis2-grep && \
    crontab /var/spool/cron/crontabs/wis2-grep && \
    # add wis2-grep user
    useradd -ms /bin/bash wis2-grep && \
    adduser wis2-grep sudo && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER wis2-grep

ENTRYPOINT [ "/app/docker/entrypoint.sh" ]
