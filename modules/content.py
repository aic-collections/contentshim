import os
import glob
import re
import errno
import requests

from logging import getLogger

from modules.db import DB
from modules.filters import fcrepo_path_from_hash

from flask import Response

class Content:
    
    app = None
    config = None
    
    fcrepo_id = ""
    fcepo_path = ""
    url = ""
    
    etag_exists = False
    content_type_extension_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/tif": "tif",
            "image/tiff": "tif",
            "image/jp2": "jp2",
        }
    extension = ""
    contenttype = ""


    def __init__(self, app, config, fcrepo_id):
        self.logger = getLogger(__name__)
        self.app = app
        self.config = config
        self.fcrepo_id = fcrepo_id
        if self._valid_fcrepo_id(fcrepo_id):
            self.fcrepo_path = fcrepo_path_from_hash(fcrepo_id)
        else:
            self.fcrepo_path = '/' + fcrepo_id
        self.url = self.config["httpresolver"]["prefix"] + self.fcrepo_path + self.config["httpresolver"]["postfix"]
        self._db = DB(app, config["sqlite"]["db"])
        
        self.logger.debug("fcrepo_id is: {}".format(self.fcrepo_id))
        self.logger.debug("fcrepo_path is: {}".format(self.fcrepo_path))
        return

    
    def get(self):
        self.logger.debug("Fetching binary for: {}".format(self.fcrepo_id))
        fs_path = self.get_fs_path()
        if fs_path != "Status404":
            self.logger.debug("Reading: {}".format(fs_path))
            with open(fs_path, "rb") as f:
                imagedata = f.read()
                self.logger.debug("Serving: {}".format(fs_path))
            if imagedata:
                response = Response(imagedata)
                response.headers['Content-type'] = self.contenttype
                return (response, "200")
            else:
                return ("What? " + fs_path, 404)
        else:
            return ("404 Not Found", 404)


    def get_fs_path(self):
        self.logger.debug("Fetching fileystem location for: {}".format(self.fcrepo_id))
        headers = {}
        etag = self._etag_get()
        self.logger.debug("Etag is: {}".format(etag))
        if etag:
            headers["If-None-Match"] = etag

        cache_req = requests.head(self.url, headers=headers)
        self.logger.debug('ETag cache response code: {}'.format(cache_req.status_code))
        self.logger.debug("cache_req headers: {}".format(cache_req.headers))
        self._set_extension_contenttype(cache_req.headers)
        
        if cache_req.status_code == 304:
            self.logger.debug('Status was 304.  Looking for cached file.')
            cache_fs_path = self.config["cache"]["basedir"] + self.fcrepo_path + "." + self.extension
            
            # ABSOLUTE NECESSITY
            file_matches = glob.glob(cache_fs_path + "*")
            if len(file_matches) > 0:
                cached_file_path = file_matches[0]
            else:
                cached_file_path = self._copy_to_cache(cache_req.headers)
        elif cache_req.status_code == 404:
            cached_file_path = "Status404"
        else:
            cached_file_path = self._copy_to_cache(cache_req.headers)
        
        self.logger.debug("Returning filesystem location: {}".format(cached_file_path))
        return cached_file_path


    def iipimage_redirect_path(self):
        fs_path = self.get_fs_path()
        redirect_file = fs_path.replace(self.config["cache"]["basedir"], '')
        return redirect_file
        


    def _set_extension_contenttype(self, cache_req_headers):
        if "content-type" in cache_req_headers:
            for key, value in self.content_type_extension_map.items():
                if key == cache_req_headers["content-type"]:
                    self.extension = value
                    self.contenttype = key
                    break
        else:
            # Lovely.  
            # lakemichigan is using fcrepo 4.7.1, which delivers different
            # headers of a HEAD request.  4.7.3 returns the content-type;
            # 4.7.1 does not.
            self.extension = 'jp2'
            self.contenttype = 'image/jp2'
        return


    def _copy_to_cache(self, cache_req_headers):
        self.logger.debug("Copying to cache.")
        ident = self.fcrepo_id
        # Will take:
        #   /86/bf/14/11/86bf1411-6180-8103-52a1-e4d84f478ec1
        # and return:
        #   /86/bf/14/11/
        cache_dir = self.config["cache"]["basedir"] + self.fcrepo_path.replace(self.fcrepo_id, '')
        self.logger.debug("Cache dir is: {}".format(cache_dir))
        self._create_cache_dir(cache_dir)

        cache_fs_path = self.config["cache"]["basedir"] + self.fcrepo_path + "." + self.extension
        if os.path.isfile(cache_fs_path):
            os.unlink(cache_fs_path)
            
        r = requests.get(self.url, stream=True)
        with open(cache_fs_path, 'wb') as f:
            # Increase the chunk size.  Fewer disk writes.
            for chunk in r.iter_content(10240):
                f.write(chunk)

        '''
        # This code didn't seem to improve matters and, in fact, the memory hit 
        # may have resulted in diminished service.
        # Curious about fewer disk writes.
        r = requests.get(self.url)
        with open(cache_fs_path, 'wb') as f: 
            f.write(r.content)
        '''
        # Store ETags.
        self._etag_put(r.headers['etag'])

        return cache_fs_path
        
        
    def _create_cache_dir(self, cache_dir):
        try:
            os.makedirs(cache_dir)
        except OSError as ose:
            if ose.errno == errno.EEXIST:
                pass
            else:
                raise


    def _etag_get(self):
        sql_query = "SELECT etag FROM etags WHERE fcrepoid = '" + self.fcrepo_id + "';"
        etags = self._db.query(sql_query)
        if etags != None:
            self.etag_exists = True
            return '"' + str(etags[0][0]) + '"'
        else:
            return None


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


    def _valid_fcrepo_id(self, fcrepo_id):
        regex = re.compile('^[a-z0-9]{8}-?[a-z0-9]{4}-?[a-z0-9]{4}-?[a-z0-9]{4}-?[a-z0-9]{12}$', re.I)
        match = regex.match(fcrepo_id)
        return bool(match)

