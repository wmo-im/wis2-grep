#!/bin/bash
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

# wis2-grep entry script

echo "START /entrypoint.sh"

printenv | grep -v "no_proxy" > /tmp/environment
sudo sh -c 'cat /tmp/environment >> /etc/environment'
rm -f /tmp/environment

echo "Starting cron"
sudo service cron start
service cron status

echo "Caching WNM schema"
pywis-pubsub schema sync

echo "Setting up notification message backend"
wis2-grep setup

echo "END /entrypoint.sh"
exec "$@"
