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


def remove_leading_underscore(entity):
    entity = json.loads(json.dumps(entity))
    corr_dict = {}
    for k, v in entity.items():
        if isinstance(v, dict):
            if k.startswith("_"):
                corr_dict[k.split("_")[-1]] = v
            else:
                remove_leading_underscore(v)
        else:
            if k.startswith("_"):
                corr_dict[k.split("_")[-1]] = v
            else:
                corr_dict[k] = v
    corr_dict = remove_namespacing(corr_dict)
    return corr_dict


def process_material_entity(entity):
    entity = json.loads(json.dumps(entity))
    corr_dict = {}
    for k, v in entity.items():
        if k.startswith("_"):
            corr_dict[k.split("_")[-1]] = v
        else:
            corr_dict[k] = v
    corr_dict = remove_namespacing(corr_dict)
    return corr_dict


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
        password = os.environ.get("password")
        logger.info("URL+PATH: %s", url)
        root_key = os.environ.get("root_key")
        element_key = os.environ.get("element_key")
        req = requests.get(url, auth=HTTPBasicAuth(username, password), verify=False, params=args)
        if req.status_code != 200:
            logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
            raise AssertionError(
                "Unexpected response status code: %d with response text %s" % (req.status_code, req.text))

        cleaned_dictionary = Dotdictify(parsejson(req.text))[root_key][element_key]
        deduplicated_dictionary = {}

        for entity in cleaned_dictionary:
            entity["_id"] = entity["Dokar"] + "_" + "101670" + "_" + entity["Doknr"] + "_" + entity["Dokob"] + "_" + entity["Doktl"] + "_" + entity["Mandt"]
            entity["composite_id"] = entity["_id"]
            entity["metadata"] = entity["__metadata"]
            if entity["_id"] not in deduplicated_dictionary:
                deduplicated_dictionary[entity["_id"]] = entity
            else:
                entity_version = entity["Dokvr"]
                if entity_version > deduplicated_dictionary[entity["_id"]]["Dokvr"]:
                    deduplicated_dictionary[entity["_id"]] = entity

        for k, v in deduplicated_dictionary.items():
            yield remove_leading_underscore(v)

    def get_json(self, path, args):
        return self.__get_all_json(path, args)

    def __get_all_material_json(self, path, args):
        url = os.environ.get("url") + path
        username = os.environ.get("username")
        password = os.environ.get("password")
        logger.info("URL+PATH: %s", url)
        root_key = os.environ.get("root_key")
        element_key = os.environ.get("element_key")
        req = requests.get(url, auth=HTTPBasicAuth(username, password), verify=False, params=args)
        if req.status_code != 200:
            logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
            raise AssertionError(
                "Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
        for entity in Dotdictify(parsejson(req.text))[root_key][element_key]:
            if entity[<"filter_key">] == <"filter_value">:
                yield process_material_entity(entity)

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
    password = os.environ.get("password")
    url = os.environ.get("url") + path
    args = request.args
    return requests.get(url, auth=HTTPBasicAuth(username, password), verify=False, params=args).content


@app.route("/material", methods=["POST"])
def get_url():
    entities = request.get_json()
    if not isinstance(entities, list):
        entities = [entities]
    for entity in entities:
        for k, v in entity.items():
            if k != os.environ.get("url_path"):
                logger.error("Unexpected variable name: %s" % k)
                raise AssertionError(
                    "Unexpected variable name: %s" % k)
            if k == os.environ.get("url_path"):
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




