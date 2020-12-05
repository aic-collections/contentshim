import os

import datetime

from logging import getLogger

from modules.mysqldb import MySQLDB

from flask import Response

class NetXInfo:
    
    app = None
    config = None
    
    uuid = ""
    dhurl = ""
    
    def __init__(self, app, config, uuid):
        self.logger = getLogger(__name__)
        self.app = app
        self.config = config
        self.uuid = uuid
        
        self.fields = ["pa_id", "pa_dbmodified", "pa_lake_uuid", "pa_netx_uuid", "pa_netx_asset_id", "pa_netx_modified", "pa_netx_filechecksum", "pa_netx_published"]
        
        self.logger.debug("uuid is: {}".format(self.uuid))
        return

    
    def get_netx_info(self):
        nx_objects = []
        db = MySQLDB(self.config["mysql"], "reader")
        extra = ''
        if 'extra' in self.config["mysql"]:
            extra = self.config["mysql"]["extra"]
        tablename = "pub_assets" + extra
        sqlquery = "SELECT * FROM " + tablename + " WHERE pa_netx_uuid='" + self.uuid + "' LIMIT 1;"
        results = db.query(sqlquery)
        self.logger.debug("Results: {}".format(results))
        if results != None:
            for r in results:
                nx_objects.append( self._format_row_to_obj(r) )
            return nx_objects
        else:
            # Search using the LAKE UUID
            sqlquery = "SELECT * FROM " + tablename + " WHERE pa_lake_uuid='" + self.uuid + "' LIMIT 1;"
            results = db.query(sqlquery)
            self.logger.debug("Results: {}".format(results))
            if results != None:
                for r in results:
                    nxobj = self._format_row_to_obj(r)
                    nxobj["comment"] = "Found using LAKE UUID"
                    nx_objects.append( nxobj )
                return nx_objects
            else:
                return "Status404"

    def get_unpublished_assets(self, since):
        nx_objects = []
        try:
            db = MySQLDB(self.config["mysql"], "reader")
            extra = ''
            if 'extra' in self.config["mysql"]:
                extra = self.config["mysql"]["extra"]
            tablename = "pub_assets" + extra
            sqlquery = "SELECT * FROM " + tablename + " WHERE pa_netx_published=1 AND pa_dbmodified > '" + since + "';"
            results = db.query(sqlquery)
            if results != None:
                for r in results:
                    nx_objects.append( self._format_row_to_obj(r, ["pa_id", "pa_netx_filechecksum", "pa_netx_published"]) )
            return nx_objects
        except Exception as err:
            return "Status503"
    
    def _format_row_to_obj(self, row, exclude_fields=[]):
        nxobj = {}
        for n in range(0, len(self.fields)):
            if self.fields[n] not in exclude_fields:
                if isinstance(row[n], datetime.datetime):
                    nxobj[self.fields[n].replace('pa_', '')] = row[n].isoformat()
                else:
                    nxobj[self.fields[n].replace('pa_', '')] = row[n]
        return nxobj

