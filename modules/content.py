import os
import glob
import re
import errno
import requests

from logging import getLogger

from modules.mysqldb import MySQLDB
from modules.filters import path_from_hashuuid

from flask import Response

class Content:
    
    app = None
    config = None
    
    fcrepo_id = ""
    fcepo_path = ""
    url = ""
    
    etag_exists = False
    content_type_extension_map = {
            "image/jp2": "jp2",
            "image/tiff": "tif",
            "image/tif": "tif",
            
            "audio/mpeg": "mp3",
            "audio/x-wave": "wav",
            
            "text/plain": "txt",
            "application/pdf": "pdf",	
            
            "video/mp4": "mp4",
            "video/mpeg": "mpeg",
            "video/quicktime": "mov",
            "video/x-flv": "flv",
            "application/x-shockwave-flash": "swf",
            
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
        }
    extension = ""
    contenttype = ""


    def __init__(self, app, config, uuid):
        self.logger = getLogger(__name__)
        self.app = app
        self.config = config
        self.uuid = uuid

        if self._valid_uuid(uuid):
            self.uuid_path = path_from_hashuuid(uuid)
        else:
            self.uuid_path = '/' + uuid
        
        self.logger.debug("uuid is: {}".format(self.uuid))
        self.logger.debug("uuid_path is: {}".format(self.uuid_path))
        return

    
    def get(self):
        self.logger.debug("Fetching binary for: {}".format(self.uuid))
        fs_path = self.get_fs_path()
        if fs_path != "Status404":
            self.logger.debug("Reading: {}".format(fs_path))
            with open(fs_path, "rb") as f:
                imagedata = f.read()
                self.logger.debug("Serving: {}".format(fs_path))
            if imagedata:
                response = Response(imagedata)
                response.headers['Content-type'] = self.contenttype
                response.headers['Content-Disposition'] = 'attachment; filename="' + fs_path.split('/')[-1] + '"'
                return (response, "200")
            else:
                return ("What? " + fs_path, 404)
        else:
            return ("404 Not Found", 404)


    def get_fs_path(self):
        self.logger.debug("Fetching fileystem location for: {}".format(self.uuid))
        cached_file_path = "Status404"
        
        # Check if on netx file system first:
        cache_fs_path = self.config["cache"]["basedir_netx_assets"] + self.uuid_path
        cached_file_path = self._try_file_match(cache_fs_path)
        if cached_file_path == "Status404":
            # Did not find asset as part of netx filesystem path.
            # So we need to query the database to see if this identifier is from LPM Fedora.
            # If yes, then we get the NetX UUID and deliver the NETX path.
            # If not, then we see if the FCREPO path exists.
            # Historically, we'd check to see if the Asset binary had changed in FCREPO.
            # However, if FCREPO becomes static, as is the case with the introduction of NETX,
            # then we just need to check if it exists on the file system.
            
            db = MySQLDB(self.config["mysql"], "reader")
            extra = ''
            if 'extra' in self.config["mysql"]:
                extra = self.config["mysql"]["extra"]
            tablename = "pub_assets" + extra
            sqlquery = "SELECT * FROM " + tablename + " WHERE pa_lake_uuid='" + self.uuid + "' LIMIT 1;"
            results = db.query(sqlquery)
            if results != None:
                # Found NetX Asset.  Look for it on system.
                netx_uuid = results[0][3]
                netx_uuid_path = path_from_hashuuid(netx_uuid)
                cache_fs_path = self.config["cache"]["basedir_netx_assets"] + netx_uuid_path
                cached_file_path = self._try_file_match(cache_fs_path)
            else:
                # Did NOT find NetX Asset.  Look for FCREPO Asset on system.
                cache_fs_path = self.config["cache"]["basedir_fcrepo_assets"] + self.uuid_path
                cached_file_path = self._try_file_match(cache_fs_path)
                if cached_file_path == "Status404":
                    cached_file_path = self._check_lpm_fedora_for_path()
        self.logger.debug("Returning filesystem location: {}".format(cached_file_path))
        return cached_file_path
        
    
    # Added Back
    def _check_lpm_fedora_for_path(self):
        self.logger.debug("Checking LPM Fedora for: {}".format(self.uuid))

        self.session = requests.Session()
        self.lpmurl = self.config["httpresolver"]["prefix"] + self.uuid_path + self.config["httpresolver"]["postfix"]
        self._db = DB(self.app, self.config["sqlite"]["db"])
        
        headers = {}
        etag = self._etag_get()
        self.logger.debug("Etag is: {}".format(etag))
        if etag:
            headers["If-None-Match"] = etag

        cache_req = self.session.head(self.lpmurl, headers=headers)
        self.logger.debug('ETag cache response code: {}'.format(cache_req.status_code))
        self.logger.debug("cache_req headers: {}".format(cache_req.headers))
        
        if cache_req.status_code == 304:
            self.logger.debug('LPM Fedora Status was 304.  Looking for cached file.')
            cache_fs_path = self.config["cache"]["basedir_fcrepo_assets"] + self.uuid_path
            
            cached_file_path = _try_file_match(cache_fs_path)
            if cached_file_path == "Status404":
                # Didn't find LPM Fedora file on system.  Fetch and store.
                cached_file_path = self._copy_to_cache(cache_req.headers)
        elif cache_req.status_code == 404:
            cached_file_path = "Status404"
        elif cache_req.status_code == 503:
            cached_file_path = "Status503"
        else:
            cached_file_path = self._copy_to_cache(cache_req.headers)

        return cached_file_path


    # Added Back
    def _copy_to_cache(self, cache_req_headers):
        if "content-type" in cache_req_headers:
            self._set_extension_contenttype(cache_req_headers)
        else:
            contenthead = self.session.head(self.url)
            self._set_extension_contenttype(contenthead.headers)
            
        self.logger.debug("Copying to LPM Fedora cache.")
        ident = self.uuid
        # Will take:
        #   /86/bf/14/11/86bf1411-6180-8103-52a1-e4d84f478ec1
        # and return:
        #   /86/bf/14/11/
        cache_dir = self.config["cache"]["basedir_fcrepo_assets"] + self.uuid_path.replace(self.uuid, '')
        self.logger.debug("Cache dir is: {}".format(cache_dir))
        self._create_cache_dir(cache_dir)

        cache_fs_path = self.config["cache"]["basedir_fcrepo_assets"] + self.uuid_path + "." + self.extension
        if os.path.isfile(cache_fs_path):
            os.unlink(cache_fs_path)
        
        # Mindful of this.  Requests.Session may require non-streamed content
        # or the connection is not released back in to the pool.
        with self.session.get(self.url, stream=True) as r:
            with open(cache_fs_path, 'wb') as f:
                # Increase the chunk size.  Fewer disk writes.
                for chunk in r.iter_content(10240):
                    f.write(chunk)
            # Store ETags.
            self._etag_put(r.headers['etag'])

        '''
        # This code didn't seem to improve matters and, in fact, the memory hit 
        # may have resulted in diminished service.
        # Curious about fewer disk writes.
        r = self.session.get(self.url)
        with open(cache_fs_path, 'wb') as f: 
            f.write(r.content)
        '''
        # Store ETags.
        # self._etag_put(r.headers['etag'])

        return cache_fs_path
        
        
    # Added Back
    def _create_cache_dir(self, cache_dir):
        try:
            os.makedirs(cache_dir)
        except OSError as ose:
            if ose.errno == errno.EEXIST:
                pass
            else:
                raise
            
    # Added Back
    def _etag_get(self):
        sql_query = "SELECT etag FROM etags WHERE fcrepoid = '" + self.fcrepo_id + "';"
        etags = self._db.query(sql_query)
        if etags != None:
            self.etag_exists = True
            return '"' + str(etags[0][0]) + '"'
        else:
            return None

    # Added Back
    def _etag_put(self, etag):
        etag = etag.split(',')[0]
        etag = etag.replace('"', '')
        self.logger.debug("Etag for inserting into DB: {}".format(etag))
        if self.etag_exists:
            sql_query = "UPDATE etags SET etag='" + etag + "' WHERE fcrepoid = '" + self.fcrepo_id + "';"
            etags = self._db.update(sql_query)
        else:
            sql_query = "INSERT INTO etags (fcrepoid, etag) VALUES ('" + self.fcrepo_id + "', '" + etag + "')" 
            dbid = self._db.update(sql_query)
        return True


    def _set_extension_contenttype(self, cache_req_headers):
        if "content-type" in cache_req_headers:
            for key, value in self.content_type_extension_map.items():
                if key == cache_req_headers["content-type"]:
                    self.extension = value
                    self.contenttype = key
                    break
        return

    def _try_file_match(self, test_path):
        cached_file_path = "Status404"
        file_matches = glob.glob(test_path + "*")
        if len(file_matches) > 0:
            # Found as part of netx assets
            cached_file_path = file_matches[0]
            if '.' in cached_file_path:
                self.extension = cached_file_path.split('.')[-1]
                for key, value in self.content_type_extension_map.items():
                    if value == self.extension:
                        self.extension = value
                        self.contenttype = key
                        break
                if self.extension == "":
                    self.extension = "jp2"
                    self.contenttype = "image/jp2"
        return cached_file_path


    def _valid_uuid(self, fcrepo_id):
        regex = re.compile('^[a-z0-9]{8}-?[a-z0-9]{4}-?[a-z0-9]{4}-?[a-z0-9]{4}-?[a-z0-9]{12}$', re.I)
        match = regex.match(fcrepo_id)
        return bool(match)

