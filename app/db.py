from flask import Flask, g

import pymongo
import os


def get_db():
    if 'mongo_client' not in g:
        g.mongo_client = pymongo.MongoClient(host=os.environ.get("MONGODB_URL"),
                                             port=int(os.environ.get("MONGODB_PORT")))
        g.db = g.mongo_client["tda"]
        g.collection = g.db["lecturers"]
    return g.collection


def close_db(e=None):
    mongo_client = g.pop('mongo_client', None)
    g.pop("db", None)
    g.pop("collection", None)

    if mongo_client is not None:
        mongo_client.close()


def init_db(app):
    with app.app_context():
        if 'mongo_client' not in g:
            g.mongo_client = pymongo.MongoClient(host=os.environ.get("MONGODB_URL"),
                                                 port=int(os.environ.get("MONGODB_PORT")))
            g.db = g.mongo_client["tda"]
            g.collection = g.db["lecturers"]


def init_app(app):
    init_db(app)
