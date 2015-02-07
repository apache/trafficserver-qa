import subprocess
import os
import os.path
import tempfile

import tsqa.test_cases


import tsqa.utils

TMP_DIR = os.path.join(tempfile.gettempdir(), 'tsqa')
unittest = tsqa.utils.import_unittest()

def source_dir():
    '''
    return the directory where source code is checked out
    '''
    path = os.path.join(TMP_DIR, 'trafficserver')
    # if we don't have it, clone it
    if not os.path.exists(path):
        tsqa.utils.run_sync_command(['git', 'clone', 'https://github.com/apache/trafficserver.git'],
                          cwd=TMP_DIR,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          )
    return os.path.join(TMP_DIR, 'trafficserver')


class EnvironmentCase(tsqa.test_cases.EnvironmentCase):
    '''
    This class will get an environment (which is unique) but won't start it
    '''
    @classmethod
    def getEnv(cls):
        '''
        This function is responsible for returning an environment
        '''
        SOURCE_DIR = os.path.realpath(os.path.join(__file__, '..', '..', '..', '..'))
        TMP_DIR = os.path.join(tempfile.gettempdir(), 'tsqa')
        ef = tsqa.environment.EnvironmentFactory(source_dir(),
                                                 os.path.join(TMP_DIR, 'base_envs'),
                                                 default_configure={'enable-example-plugins': None,
                                                                    'enable-test-tools': None,
                                                                    'enable-example-plugins': None,
                                                                    },
                                                 )
        # TODO: figure out a way to determine why the build didn't fail and
        # not skip all build failures?
        return ef.get_environment(cls.environment_factory['configure'], cls.environment_factory['env'])
