from flask import g

from pymongo.mongo_client import MongoClient
import os

uri = ""


def get_db():
    if 'mongo_client' not in g:
        g.mongo_client = MongoClient(uri)
        g.db = g.mongo_client["tda"]
    return g.db


def close_db(e=None):
    mongo_client = g.pop('mongo_client', None)
    g.pop("db", None)
    g.pop("collection", None)

    if mongo_client is not None:
        mongo_client.close()


def init_db(app):
    with app.app_context():
        if 'mongo_client' not in g:
            g.mongo_client = MongoClient(uri)
            g.db = g.mongo_client["tda"]
            g.collection = g.db["lecturers"]


def init_app(app):
    global uri
    uri = f"mongodb://{os.environ.get('DB_USERNAME')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_URLS')}/?ssl=true&replicaSet=atlas-g84ywi-shard-0&authSource=admin&retryWrites=true&w=majority"
    init_db(app)
