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


# TODO: keep track of stat when it was loaded? So we don't clobber manual file changes...

class Config(object):
    '''
    Class to represent a config file
    '''

    def __init__(self, filename):
        self.filename = filename
        self.load()

    def add_lines(self, lines):
        for line in lines:
            self.add_line(line)

    def load(self):
        with open(self.filename, 'r') as fh:
            self.contents = fh.read()

    def write(self):
        '''
        Write contents to disk
        '''
        with open(self.filename, 'w') as fh:
            fh.write(self.contents)

    def add_line(self, line):
        if not line.endswith('\n'):
            line += '\n'
        self.contents += line


class RecordsConfig(Config, dict):
    '''
    Create a "dict" representation of records.config

    This can be accessed as a multi-level dictionary

    such as:
    rc['CONFIG']['proxy.config.log.hostname']
    '''
    kind_map = {'STRING': str,
                'INT': int,
                'FLOAT': float,
                }

    reverse_kind_map = {str: 'STRING',
                        int: 'INT',
                        float: 'FLOAT',
                        }

    line_template = '{top_kind} {name} {kind} {val}\n'

    def __init__(self, filename):
        dict.__init__(self)
        self.filename = filename

        self.load()

    def _load_line(self, line):
        line = line.strip()
        # skip comments
        if not line or line.startswith('#'):
            return
        top_kind, name, kind, val = line.split(' ', 3)
        if top_kind not in self:
            self[top_kind] = {}
        self[top_kind][name] = self.kind_map[kind](val)

    def load(self):
        with open(self.filename, 'r') as fh:
            for line in fh:
                self._load_line(line)

    def add_line(self, line):
        self._load_line(line)

    def write(self):
        with open(self.filename, 'w') as fh:
            for top_kind, config_map in self.iteritems():
                for name, val in config_map.iteritems():
                    fh.write(self.line_template.format(top_kind=top_kind,
                                                       name=name,
                                                       kind=self.reverse_kind_map[type(val)],
                                                       val=val))

if __name__ == '__main__':
    rc = RecordsConfig('/etc/trafficserver/records.config')
    rc['CONFIG']['proxy.config.log.hostname']
    rc['CONFIG'].update({'proxy.config.log.hostname': 'foo'})
    rc.filename = '/tmp/recordstest.config'
    rc.write()

