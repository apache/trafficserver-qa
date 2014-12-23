class Config(object):
    '''
    Class to represent a config file
    '''

    def __init__(self, filename):
        self.filename = filename
        self.load()

    def load(self):
        with open(self.filename, 'r') as fh:
            self.contents = fh.read()

    def write(self):
        '''
        Write contents to disk
        '''
        with open(self.filename, 'w') as fh:
            fh.write(self.contents)



class RecordsConfig(Config, dict):
    '''
    Create a "dict" representation of records.config
    '''
    kind_map = {'STRING': str,
                'INT': int,
                'FLOAT': float,
                }

    reverse_kind_map = {str: 'STRING',
                        int: 'INT',
                        float: 'FLOAT',
                        }

    line_template = 'CONFIG {name} {kind} {val}\n'

    def __init__(self, filename):
        dict.__init__(self)
        self.filename = filename

        self.load()

    def load(self):
        self._config = {}
        with open(self.filename, 'r') as fh:
            for line in fh:
                line = line.strip()
                # skip comments
                if line.startswith('#'):
                    continue
                _, name, kind, val = line.split(' ', 3)
                self[name] = self.kind_map[kind](val)

    def write(self, dest):
        with open(dest, 'w') as fh:
            for name, val in self.iteritems():
                fh.write(self.line_template.format(name=name,
                                                   kind=self.reverse_kind_map[type(val)],
                                                   val=val))

