import os

import pymongo
from flask import Flask, jsonify, render_template, request, g
import db
from werkzeug.local import LocalProxy
from dotenv import load_dotenv
import uuid

load_dotenv()

app = Flask(__name__, template_folder="../templates")

db.init_app(app)

collection: pymongo.collection.Collection = LocalProxy(db.get_db)

app.config.from_mapping(
    DATABASE=os.path.join(app.instance_path, 'tourdeflask.sqlite'),
)

# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass


@app.route('/')
def hello_tda():
    return "Hello TdA"


@app.route('/api')
def api():
    return jsonify({"secret": "The cake is a lie"}), 200


@app.route("/api/lecturers/<uuid>", methods=["GET", "PUT", "DELETE"])
@app.route("/api/lecturers", methods=["GET", "POST"], defaults={"uuid": 0})
def api_lecturers(uuid):
    match request.method:
        case "GET":
            if not uuid:
                return jsonify([i for i in collection.find()]), 200
            else:
                select = [i for i in collection.find({"uuid": uuid})]
                if not select:
                    return {"code": 404, "message": "User not found"}, 404
                return "None", 200
        case "POST":
            pass
        case "PUT":
            pass
        case "DELETE":
            pass
        case _:
            return {"message": "Unsupported method", "code": 405}, 405


@app.route("/lecturer")
def lecturer():
    return render_template("lecturer.html"), 200


if __name__ == '__main__':
    app.run()
    db.close_db()
