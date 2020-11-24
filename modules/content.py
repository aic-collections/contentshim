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
        self.logger.debug("Returning filesystem location: {}".format(cached_file_path))
        return cached_file_path


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

