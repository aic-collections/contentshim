from hashlib import md5

def hashuuid_from_uid(uid):
    md5hash = md5(bytes(uid, 'ascii')).hexdigest()
    return split_md5_hash(md5hash)
    
def path_from_uid(uid):
    '''Generate a Fedora pairtree from a given LAKE uid.
    @param uid (string) The resource UID.
    '''
    hashuuid = hashuuid_from_uid(uid)
    return path_from_hashuuid(hashuuid)
    
def path_from_hashuuid(hashuuid):
    '''Generate a Fedora pairtree from a given LAKE uid.
    @param uid (string) The resource UID.
    '''
    hashuuid_raw = hashuuid.replace('-', '')
    path = '/{}/{}/{}/{}/{}'.format(hashuuid_raw[:2], hashuuid_raw[2:4], hashuuid_raw[4:6], hashuuid_raw[6:8], hashuuid)
    return path
        
def split_md5_hash(md5hash):
    '''Split MD5 UID with dashes as per ISOXXX.
        @param uid (string) MD5 hash.
    '''
    return '{}-{}-{}-{}-{}'.format(md5hash[:8],md5hash[8:12], md5hash[12:16],md5hash[16:20],md5hash[20:])
