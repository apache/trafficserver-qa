#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import logging
import os

if 'TSQA_LOG_LEVEL' in os.environ:
    lvl_str = os.environ['TSQA_LOG_LEVEL']
    if not lvl_str.isupper():
        raise Exception('Log levels must be all capitals')

    logging.root.setLevel(getattr(logging, lvl_str))
else:
    logging.root.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(os.environ.get('TSQA_LOG_LEVEL', logging.INFO))
handler.setFormatter(logging.Formatter("%(levelname)s %(asctime)-15s - %(message)s"))
logging.root.addHandler(handler)

# quiet a few loggers...
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.WARNING)
