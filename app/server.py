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

sys.path.append(os.path.abspath('..'))

from modules.db import DB
from modules.content import Content

from modules.filters import fcrepo_path_from_hash

app = Flask(__name__)
config = None

@app.route("/initdb")
def init_db():
    with app.app_context():
        db = DB(app, config["sqlite"]["db"])
        if db.init_db(config["sqlite"]["schema"]):
            return ('Database Created/Reset', 200)    
        else:
            return ("Something went horribly wrong", 500)

# 91e8c8fe-56f4-4c1d-b296-614f870fda35        
# 2096bf7b-be87-b20c-1268-0d2c3324e402
@app.route("/<any(assets, images):delim>/<fcrepo_id>")
def get_asset(fcrepo_id, delim=''):
    with app.app_context():
        content = Content(app, config, fcrepo_id)
        return content.get()

@app.route("/<any(assets, images):delim>/<fcrepo_id>/fspath")
def get_fs_path(fcrepo_id, delim=''):
    with app.app_context():
        content = Content(app, config, fcrepo_id)
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
            
@app.route("/redirect/iipimage/iiif/<path:iiif_uri>")
def iipimage_redirect(iiif_uri):
    if iiif_uri.endswith("info.json"):
        iiif_uri_parts = iiif_uri.split('/')
        uri_main_parts = iiif_uri_parts[:-1]
        filename = '/'.join(uri_main_parts)
        uri_ending = '/'.join(iiif_uri_parts[-1:])
        if '.' in filename:
            fcrepo_id = iiif_uri.split('.')[0]
        else:
            fcrepo_id = filename
    else:
        iiif_uri_parts = iiif_uri.split('/')
        uri_main_parts = iiif_uri_parts[:-4 or None]
        filename = '/'.join(uri_main_parts)
        uri_ending = '/'.join(iiif_uri_parts[-4:])
        if '.' in filename:
            fcrepo_id = iiif_uri.split('.')[0]
        else:
            fcrepo_id = filename
    if fcrepo_id == None:
        response = Response("404 Not Found")
        response.headers['Content-type'] = "text/plain"
        return (response, 404)
    else:
        with app.app_context():
            content = Content(app, config, fcrepo_id)
            redirect_path = content.iipimage_redirect_path()
            if redirect_path == "Status404":
                response = Response("404 Not Found")
                response.headers['Content-type'] = "text/plain"
                return (response, 404)
            elif fs_path == "Status503":
                response = Response("503 - Service Temporarily Unavailable.  LPM Fedora issue.")
                response.headers['Content-type'] = "text/plain"
                return (response, 503)
            else:
                redirect_to = config["iipimage"]["base"] + redirect_path + '/' + uri_ending
                return redirect(redirect_to, 302)

@app.route("/etags")
def etags():
    with app.app_context():
        db = DB(app, config["sqlite"]["db"])
        results = db.etags()
        if results != None:
            output = "id        fcrepo_id       etag\n"
            for i in results:
                output += str(i[0]) + "     " + i[1] + "        " + i[2] + "\n"
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
        
    if not config["cache"]["basedir"].startswith('/'):
        config["cache"]["basedir"] = config["app_base_path"] + config["cache"]["basedir"]

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
        
    if not config["cache"]["basedir"].startswith('/'):
        config["cache"]["basedir"] = config["app_base_path"] + config["cache"]["basedir"]

    logging.config.dictConfig(config["logging"])
    logging.info('Started')
    logger = getLogger(__name__)

    logger.info("Application loaded using config: {}".format(config))
    app.run(debug=True, host="0.0.0.0", port=8000)

