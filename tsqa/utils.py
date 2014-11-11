def merge_dicts(*args):
    '''
    Merge dicts in order

    We do them in reverse to avoid having to set/unset a lot of things
    '''
    ret = {}
    for arg in reversed(args):
        for k, v in arg.iteritems():
            if k not in ret:
                ret[k] = v
    return ret

# TODO: move to utils library
def configure_list(configure):
    ret = []
    for k, v in configure.iteritems():
        if v is None:  # if value is None, then its just an arg
            ret.append('--{0}'.format(k))
        else:  # otherwise there was a value
            ret.append('--{0}={1}'.format(k, v))
    return ret

def configure_string_to_dict(configure_string):
    '''
    Take a configure string and break it into a dict
    '''
    ret = {}
    for part in configure_string.split():
        part = part.strip('-').strip()
        if '=' in part:
            k, v = part.split('=', 1)
        else:
            k = part
            v = None
        ret[k] = v
    return ret

