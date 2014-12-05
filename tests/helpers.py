import subprocess
import os

from tsqa.utils import run_sync_command

TMP_DIR = '/tmp/tsqa/'


def source_dir():
    '''
    return the directory where source code is checked out
    '''
    # if we don't have it, clone it
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)
        run_sync_command(['git', 'clone', 'https://github.com/apache/trafficserver.git'],
                          cwd=TMP_DIR,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          )
    return TMP_DIR

