from hashlib import md5

def fcrepo_path_from_uid(uid):
    '''Generate a Fedora pairtree from a given LAKE uid.
    @param uid (string) The resource UID.
    '''
    cksum_raw = md5(bytes(uid, 'ascii')).hexdigest()
    cksum = split_md5_hash(cksum_raw)
    return fcrepo_path_from_hash(cksum)
    
def fcrepo_path_from_hash(cksum):
    '''Generate a Fedora pairtree from a given LAKE uid.
    @param uid (string) The resource UID.
    '''
    cksum_raw = cksum.replace('-', '')
    path = '/{}/{}/{}/{}/{}'.format(cksum_raw[:2], cksum_raw[2:4], cksum_raw[4:6], cksum_raw[6:8], cksum)
    return path
        
def split_md5_hash(hash):
    '''Split MD5 UID with dashes as per ISOXXX.
        @param uid (string) MD5 hash.
    '''
    return '{}-{}-{}-{}-{}'.format(hash[:8],hash[8:12], hash[12:16],hash[16:20],hash[20:])
