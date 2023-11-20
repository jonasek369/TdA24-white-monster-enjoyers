import os

import pymongo
from flask import Flask, jsonify, render_template, request, g
from . import db
from werkzeug.local import LocalProxy
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

app = Flask(__name__, template_folder="../templates", static_folder="../static")

db.init_app(app)

database: pymongo.collection.Collection = LocalProxy(db.get_db)

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


def check_keys(data):
    for key in ["first_name", "last_name"]:
        if key not in data:
            print("dosent have", key)
            return False
    for nested_keys in [["contact", "telephone_numbers"], ["contact", "emails"]]:
        if not data.get(nested_keys[0]) or nested_keys[1] not in data.get(nested_keys[0]):
            return False
    return True


def get_lecturer_from_data(data, uuid, tags):
    print(tags)
    contact = {
        "telephone_number": data["contact"]["telephone_numbers"],
        "email": data["contact"]["emails"]
    }

    return {
        "uuid": uuid if uuid else str(uuid4()),
        "title_before": data.get("title_before"),
        "first_name": data.get("first_name"),
        "middle_name": data.get("middle_name"),
        "last_name": data.get("last_name"),
        "title_after": data.get("title_after"),
        "picture_url": data.get("picture_url"),
        "location": data.get("location"),
        "claim": data.get("claim"),
        "bio": data.get("bio"),
        "tags": tags,
        "price_per_hour": data.get("price_per_hour"),
        "contact": contact
    }


# TODO: Finish
@app.route("/api/lecturers/<uuid>", methods=["GET", "PUT", "DELETE"])
@app.route("/api/lecturers", methods=["GET", "POST"], defaults={"uuid": 0})
def api_lecturers(uuid):
    match request.method:
        case "GET":
            if not uuid:
                return jsonify([i for i in database["lecturer"].find({}, {"_id": 0})]), 200
            else:
                select = [i for i in database["lecturer"].find({"uuid": uuid})]
                if not select:
                    return {"code": 404, "message": "User not found"}, 404
                return "None", 200
        case "POST":
            data = request.json
            if not data:
                return {"code": 403, "message": "Cannot add lecturer without any data"}, 403
            if not check_keys(data):
                return {"code": 403, "message": "Cannot add lecturer. Json dose not have all the needed keys"}, 403
            if uuid:
                select = [i for i in database["lecturer"].find({"uuid": uuid})]
                if select:
                    return {"code": 403, "message": "Lecturer with this uuid already exists"}
            data["tags"] = [i["name"].capitalize() for i in data["tags"]]

            query = {"name": {"$in": data["tags"]}}
            projection = {"name": 1, "uuid": 1, "_id": 0}
            result = database["tags"].find(filter=query, projection=projection)
            tags_in_db = [document["name"] for document in result]

            tags_not_in_db = [tag for tag in data["tags"] if tag not in tags_in_db]
            tags_to_db = []

            for tag in tags_not_in_db:
                tags_to_db.append({"uuid": str(uuid4()), "name": tag})
            if tags_to_db:
                database["tags"].insert_many(tags_to_db)

            lect_to_db = get_lecturer_from_data(data, uuid,
                                                [{"name": document.get("name"), "uuid": document.get("uuid")} for
                                                 document in result] + tags_to_db)
            # TODO: Check if this is right
            database["lecturer"].insert_one(lect_to_db)
            return lect_to_db
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
