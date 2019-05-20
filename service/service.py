from flask import Flask, request, Response
import json
import os
import logger
from dotdictify import Dotdictify
from requests.auth import HTTPBasicAuth
import requests
from collections import OrderedDict
import cherrypy

app = Flask(__name__)
logger = logger.Logger("sap")

# parse json and return an ordered dictionary


def parsejson(jsonfile):
    return json.loads(jsonfile, object_pairs_hook=OrderedDict)


def process_entity(entity):
    entity = json.loads(json.dumps(entity))
    new_dict = {}
    for k, v in entity.items():
        if k.startswith("_"):
            new_dict[k.split("_")[-1]] = v
        else:
            new_dict[k] = v
    new_dict = remove_namespacing(new_dict)
    return new_dict


def prosses_material_entity(entity):
    entity = json.loads(json.dumps(entity))
    new_dict = {}
    for k, v in entity.items():
        if k.startswith("_"):
            new_dict[k.split("_")[-1]] = v
        else:
            new_dict[k] = v
    new_dict = remove_namespacing(new_dict)
    return new_dict


def remove_namespacing(entity):
    entity = json.loads(json.dumps(entity))
    if isinstance(entity, list):
        for k in entity:
            remove_namespacing(k)
    corrected_dict = {}
    for k, v in entity.items():
        if isinstance(v, dict):
            v = remove_namespacing(v)
        corrected_dict[k.split(":")[-1]] = v
    return corrected_dict


def str_to_bool(string_input):
    return str(string_input).lower() == "true"


class DataAccess:
    def __get_all_json(self, path, args):
        url = os.environ.get("url") + path
        username = os.environ.get("username")
        key = os.environ.get("key")
        logger.info("URL+PATH: %s", url)
        root_key = os.environ.get("root_key")
        element_key = os.environ.get("element_key")
        req = requests.get(url, auth=HTTPBasicAuth(username, key), verify=False, params=args)
        if req.status_code != 200:
            logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
            raise AssertionError(
                "Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
        for entity in Dotdictify(parsejson(req.text))[root_key][element_key]:
            yield process_entity(entity)

    def get_json(self, path, args):
        return self.__get_all_json(path, args)

    def __get_all_material_json(self, path, args):
        url = os.environ.get("url") + path
        username = os.environ.get("username")
        key = os.environ.get("key")
        logger.info("URL+PATH: %s", url)
        root_key = os.environ.get("root_key")
        element_key = os.environ.get("element_key")
        req = requests.get(url, auth=HTTPBasicAuth(username, key), verify=False, params=args)
        if req.status_code != 200:
            logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
            raise AssertionError(
                "Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
        for entity in Dotdictify(parsejson(req.text))[root_key][element_key]:
            if entity["Charact"] == "PCS_GROUP":
                yield process_entity(entity)

    def get_material_json(self, path, args):
        return self.__get_all_material_json(path, args)


data_access_layer = DataAccess()


def stream_json(clean):
    first = True
    yield '['
    for i, row in enumerate(clean):
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(row)
    yield ']'


@app.route("/file/<path:path>", methods=["GET"])
def get_file(path):
    username = os.environ.get("username")
    key = os.environ.get("key")
    url = os.environ.get("url") + path
    args = request.args
    return requests.get(url, auth=HTTPBasicAuth(username, key), verify=False, params=args).content


@app.route("/material", methods=["POST"])
def get_url():
    entities = request.get_json()
    if not isinstance(entities, list):
        entities = [entities]
    for entity in entities:
            for k, v in entity.items():
                    if k == "url":
                        return Response(
                            stream_json(data_access_layer.get_material_json(v, request.args)),
                            mimetype='application/json'
                        )


@app.route("/<path:path>", methods=["GET"])
def get(path):
    entities = data_access_layer.get_json(path, request.args)
    return Response(
        stream_json(entities),
        mimetype='application/json'
    )


if __name__ == '__main__':
    cherrypy.tree.graft(app, '/')

    # Set the configuration of the web server to production mode
    cherrypy.config.update({
        'environment': 'production',
        'engine.autoreload_on': False,
        'log.screen': True,
        'server.socket_port': 5000,
        'server.socket_host': '0.0.0.0'
    })

    # Start the CherryPy WSGI web server
    cherrypy.engine.start()
    cherrypy.engine.block()






