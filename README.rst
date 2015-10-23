.. Licensed to the Apache Software Foundation (ASF) under one
   or more contributor license agreements.  See the NOTICE file
   distributed with this work for additional information
   regarding copyright ownership.  The ASF licenses this file
   to you under the Apache License, Version 2.0 (the
   "License"); you may not use this file except in compliance
   with the License.  You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing,
   software distributed under the License is distributed on an
   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
   KIND, either express or implied.  See the License for the
   specific language governing permissions and limitations
   under the License.

=============
What is TSQA?
=============

TSQA is an integration testing framework for Apache TrafficServer. While working
with ATS we've noticed that there little to no integration tests (functional tests)
of ATS, the tests are primarily unit or regression tests-- but none of which actually
start traffic-server. There was some work done on the initial tsqa (which is a
collection of bash scripts). The intent here is to create a more useful and
friendly testing harness for trafficserver and it's plugins. This comes with a
secondary goal of being generic enough to test other proxies-- this has come up
since after writing the majority of code is not ATS specific.



Environment Variables
=====================
TSQA_LAYOUT_PREFIX: Prefix to create layouts for each test execution (defaults to tsqa.env.)
TSQA_LAYOUT_DIR: Directory to create layouts for each test execution (defaults to /tmp)
TSQA_LOG_LEVEL: Log level for TSQA (defaults to INFO)
TSQA_TMP_DIR: temp directory for building of source (environment factory)
