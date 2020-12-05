import os
import sys
import yaml
import json

import requests

import sqlite3
from flask import g

from flask import Flask
from flask import request
from flask import Response, redirect

import logging
import logging.config
from logging import getLogger

from time import strftime

sys.path.append(os.path.abspath('..'))

from modules.db import DB
from modules.mysqldb import MySQLDB
from modules.content import Content
from modules.public_domain import PublicDomain
from modules.netx_info import NetXInfo

app = Flask(__name__)
config = None

@app.route("/<any(assets, images, public_domain):delim>/initdb")
def init_db(delim=''):
    with app.app_context():
        db = DB(app, config["sqlite"]["db"])
        if delim == "public_domain":
            if db.init_db(config["sqlite"]["pdschema"]):
                return ('Database Created/Reset for public_domain info', 200)    
            else:
                return ("Something went horribly wrong for public_domain info", 500)
        else:
            return ("Not Found", 404)

# 91e8c8fe-56f4-4c1d-b296-614f870fda35        
# 2096bf7b-be87-b20c-1268-0d2c3324e402
@app.route("/<any(assets, images):delim>/<uuid>")
def get_asset(uuid, delim=''):
    with app.app_context():
        content = Content(app, config, uuid)
        return content.get()

@app.route("/<any(assets, images):delim>/<uuid>/fspath")
def get_fs_path(uuid, delim=''):
    with app.app_context():
        content = Content(app, config, uuid)
        fs_path = content.get_fs_path()
        if fs_path == "Status404":
            response = Response("404 Not Found")
            response.headers['Content-type'] = "text/plain"
            return (response, 404)
        elif fs_path == "Status503":
            response = Response("503 - Service Temporarily Unavailable.  LPM Fedora issue.")
            response.headers['Content-type'] = "text/plain"
            return (response, 503)
        else:
            response = Response(fs_path)
            response.headers['Content-type'] = "text/plain"
            return (response, 200)
            
@app.route("/<any(assets, images):delim>/<uuid>/public_domain")
def get_pd_status(uuid, delim=''):
    with app.app_context():
        pd = PublicDomain(app, config, uuid)
        pdstatus = pd.get_pd_status()
        if pdstatus == "Status404":
            response = Response("404 Not Found")
            response.headers['Content-type'] = "text/plain"
            return (response, 404)
        elif pdstatus == "Status503":
            response = Response("503 - Service Temporarily Unavailable.  Datahub issue?")
            response.headers['Content-type'] = "text/plain"
            return (response, 503)
        else:
            response = Response(pdstatus)
            response.headers['Content-type'] = "application/json"
            return (response, 200)
            
@app.route("/<any(assets, images):delim>/<uuid>/netx_info")
def get_netx_info(uuid, delim=''):
    with app.app_context():
        nxi = NetXInfo(app, config, uuid)
        nxinfo = nxi.get_netx_info()
        if nxinfo == "Status404":
            response = Response("404 Not Found")
            response.headers['Content-type'] = "text/plain"
            return (response, 404)
        elif nxinfo == "Status503":
            response = Response("503 - Service Temporarily Unavailable.  Datahub issue?")
            response.headers['Content-type'] = "text/plain"
            return (response, 503)
        else:
            response = Response(json.dumps(nxinfo, indent=4))
            response.headers['Content-type'] = "application/json"
            return (response, 200)
            
@app.route("/<any(assets, images):delim>/unpublished_assets")
def get_unpublished_assets(delim=''):
    since = request.args.get('since')
    if since == None:
        return ("No Since Date Set", 400)
    with app.app_context():
        nxi = NetXInfo(app, config, "")
        nxinfo = nxi.get_unpublished_assets(since)
        if nxinfo == "Status503":
            response = Response("503 - Service Temporarily Unavailable.  Database issue?")
            response.headers['Content-type'] = "text/plain"
            return (response, 503)
        else:
            response = Response(json.dumps(nxinfo, indent=4))
            response.headers['Content-type'] = "application/json"
            return (response, 200)
            
@app.route("/<any(assets, images):delim>/published_netx_assets")
def published_netx_assets(delim=''):
    with app.app_context():
        db = MySQLDB(config["mysql"], "reader")
        results = db.published_netx_assets()
        if results != None:
            output = "pa_id        pa_dbmodified       pa_lake_uuid     pa_netx_uuid     pa_netx_asset_id     pa_netx_modified     pa_netx_filechecksum     pa_netx_published\n"
            for i in results:
                output += str(i[0]) + "     " + i[1].strftime("%Y-%m-%dT%H:%M:%S") + "        " + str(i[2]) + "        " + i[3] + "        " + str(i[4]) + "        " + i[5].strftime("%Y-%m-%dT%H:%M:%S") + "        " + i[6] + "        " + str(i[7]) + "\n"
            response = Response(output)
            response.headers['Content-type'] = "text/plain"
            return (response, 200)
        else:
            return ("Results was None?", 500)
            
@app.route("/<any(assets, images):delim>/pd_statuses")
def pd_statuses(delim=''):
    with app.app_context():
        db = DB(app, config["sqlite"]["db"])
        results = db.pd_statuses()
        if results != None:
            output = "id        fcrepo_image_id       public_domain     last_checked\n"
            for i in results:
                output += str(i[0]) + "     " + i[1] + "        " + str(i[2]) + "        " + i[3] + "\n"
            response = Response(output)
            response.headers['Content-type'] = "text/plain"
            return (response, 200)
        else:
            return ("Results was None?", 500)


def load_app(configpath):
    global config
    config = yaml.safe_load(open(configpath))
    
    if not config["sqlite"]["db"].startswith('/'):
        config["sqlite"]["db"] = config["app_base_path"] + config["sqlite"]["db"]
        
    if not config["sqlite"]["schema"].startswith('/'):
        config["sqlite"]["schema"] = config["app_base_path"] + config["sqlite"]["schema"]
        
    if not config["sqlite"]["pdschema"].startswith('/'):
        config["sqlite"]["pdschema"] = config["app_base_path"] + config["sqlite"]["pdschema"]
        
    if not config["cache"]["basedir_fcrepo_assets"].startswith('/'):
        config["cache"]["basedir_fcrepo_assets"] = config["app_base_path"] + config["cache"]["basedir_fcrepo_assets"]

    if not config["cache"]["basedir_netx_assets"].startswith('/'):
        config["cache"]["basedir_netx_assets"] = config["app_base_path"] + config["cache"]["basedir_netx_assets"]

    logging.config.dictConfig(config["logging"])
    logging.info('Started')
    logger = getLogger(__name__)

    logger.info("Application loaded using config: {}".format(config))
    return app

if __name__ == "__main__":
    from modules.config_parser import args
    config = yaml.safe_load(open(args.config))
    
    if not config["sqlite"]["db"].startswith('/'):
        config["sqlite"]["db"] = config["app_base_path"] + config["sqlite"]["db"]
        
    if not config["sqlite"]["schema"].startswith('/'):
        config["sqlite"]["schema"] = config["app_base_path"] + config["sqlite"]["schema"]
        
    if not config["sqlite"]["pdschema"].startswith('/'):
        config["sqlite"]["pdschema"] = config["app_base_path"] + config["sqlite"]["pdschema"]
        
    if not config["cache"]["basedir_fcrepo_assets"].startswith('/'):
        config["cache"]["basedir_fcrepo_assets"] = config["app_base_path"] + config["cache"]["basedir_fcrepo_assets"]

    if not config["cache"]["basedir_netx_assets"].startswith('/'):
        config["cache"]["basedir_netx_assets"] = config["app_base_path"] + config["cache"]["basedir_netx_assets"]

    logging.config.dictConfig(config["logging"])
    logging.info('Started')
    logger = getLogger(__name__)

    logger.info("Application loaded using config: {}".format(config))
    app.run(debug=True, host="0.0.0.0", port=8000)

