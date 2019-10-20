import os
import glob
import re
import errno
import requests

from logging import getLogger

from modules.db import DB
from modules.filters import fcrepo_path_from_hash

from flask import Response

class PublicDomain:
    
    app = None
    config = None
    
    fcrepo_id = ""
    dhurl = ""
    
    is_public_domain = False
    
    def __init__(self, app, config, fcrepo_id):
        self.logger = getLogger(__name__)
        self.app = app
        self.config = config
        self.fcrepo_id = fcrepo_id
        self.session = requests.Session()
        if self._valid_fcrepo_id(fcrepo_id):
            self.dhurl = "http://aggregator-data.artic.edu/api/v1/artworks/search?cache=false&query[bool][should][][term][image_id]=" + self.fcrepo_id + "&query[bool][should][][term][alt_image_ids]=" + self.fcrepo_id + "&fields=is_public_domain,id,is_zoomable,max_zoom_window_size,api_link,title,artist_display"
        self._db = DB(app, config["sqlite"]["db"])
        
        self.logger.debug("fcrepo_id is: {}".format(self.fcrepo_id))
        return

    
    def get(self):
        self.logger.debug("Fetching public_domain status for: {}".format(self.fcrepo_id))
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


    def get_pd_status(self):
        self.logger.debug("Fetching stored public_domain status for: {}".format(self.fcrepo_id))
        if self._valid_fcrepo_id(self.fcrepo_id):
            pd_status = self._pd_desg_get()
            self.logger.debug("Returning public_domain status {} for {}".format(pd_status, self.fcrepo_id))
            if str(pd_status) == "Status503":
                return pd_status
            else:
                return '{ "is_public_domain": ' + str(pd_status).lower() +' }'
        else:
            return "Status404"


    def _pd_desg_get(self):
        
        self.pd_desgs_exists = False
        sql_query = "SELECT public_domain FROM pd_designations WHERE fcrepo_image_id = '" + self.fcrepo_id + "' AND last_checked >= datetime('now', '-24 hours');"
        self.logger.debug("Checking for existing pd_status within expiry time: {}".format(sql_query))
        pd_desgs = self._db.query(sql_query)
        if pd_desgs != None:
            self.logger.debug("Found DB entry for {}.".format(self.fcrepo_id))
            self.pd_desgs_exists = True
            if str(pd_desgs[0][0]) == "1":
                self.is_public_domain = True
        else:
            # Must look it up in the datahub
            self.logger.debug("No DB entry found for {}.".format(self.fcrepo_id))
            self.logger.debug("Checking datahub for {}.".format(self.fcrepo_id))
            try:
                dhresponse = requests.get(self.dhurl)
                dhdata = dhresponse.json()
                if ( len(dhdata["data"]) > 0 ):
                    if (dhdata["data"][0]["is_public_domain"]):
                        self.is_public_domain = True
                else:
                    self.logger.debug("Datahub does not know about {}. Public_domain is true as this may be an Interpretive Resource.".format(self.fcrepo_id))
                    self.is_public_domain = True
                self._pd_desg_put()
            except:
                return "Status503"
        
        return self.is_public_domain


    def _pd_desg_put(self):
        self.logger.debug("Public domain status is {} for insert to DB for Asset {}".format(self.is_public_domain, self.fcrepo_id))
        pd_status_str = "0"
        if self.is_public_domain:
            pd_status_str = "1"
        sql_query = "SELECT public_domain FROM pd_designations WHERE fcrepo_image_id = '" + self.fcrepo_id + "';"
        self.logger.debug("Checking for existing pd_status regardless of expiry: {}".format(sql_query))
        pd_desgs = self._db.query(sql_query)
        if pd_desgs != None:
            sql_query = "UPDATE pd_designations SET public_domain='" + pd_status_str + "', last_checked=datetime('now') WHERE fcrepo_image_id = '" + self.fcrepo_id + "';"
            etags = self._db.update(sql_query)
        else:
            sql_query = "INSERT INTO pd_designations (fcrepo_image_id, public_domain, last_checked) VALUES ('" + self.fcrepo_id + "', '" + pd_status_str + "', datetime('now'))" 
            dbid = self._db.update(sql_query)
        return True


    def _valid_fcrepo_id(self, fcrepo_id):
        regex = re.compile('^[a-z0-9]{8}-?[a-z0-9]{4}-?[a-z0-9]{4}-?[a-z0-9]{4}-?[a-z0-9]{12}$', re.I)
        match = regex.match(fcrepo_id)
        return bool(match)

