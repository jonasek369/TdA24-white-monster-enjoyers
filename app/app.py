import json
import os
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
from . import db
import html

import sys
from io import StringIO

# Create a StringIO object to capture the output
output_buffer = StringIO()

# Redirect the standard output to the StringIO object
sys.stdout = output_buffer

app = Flask(__name__, static_folder="../static", template_folder="../templates")

app.config.from_mapping(
    DATABASE=os.path.join(app.instance_path, 'database.db'),
)

# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

db.init_app(app)


@app.route('/')
def hello_tda():
    return "Hello TdA"


@app.route('/api')
def api():
    return jsonify({"secret": "The cake is a lie"}), 200


def check_keys(data):
    for key in ["first_name", "last_name"]:
        if key not in data:
            return False
    for nested_keys in [["contact", "telephone_numbers"], ["contact", "emails"]]:
        if not data.get(nested_keys[0]) or nested_keys[1] not in data.get(nested_keys[0]):
            return False
    return True


def get_lecturer_as_json(data, uuid, tags):
    contact = {
        "telephone_numbers": data["contact"]["telephone_numbers"],
        "emails": data["contact"]["emails"]
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
        "bio": data.get("bio").replace("<script>", "").replace("</script>", ""),
        "tags": [{"uuid": tag[0], "name": tag[1]} for tag in tags],
        "price_per_hour": data.get("price_per_hour"),
        "contact": contact
    }


def get_lecturer_db_insert_value(data, uuid, tags):
    contact = {
        "telephone_numbers": [html.escape(i) for i in data["contact"]["telephone_numbers"]],
        "emails": [html.escape(i) for i in data["contact"]["emails"]],
    }
    data = [
        uuid if uuid else str(uuid4()),
        data.get("title_before"),
        data.get("first_name"),
        data.get("middle_name"),
        data.get("last_name"),
        data.get("title_after"),
        data.get("picture_url"),
        data.get("location"),
        data.get("claim"),
        data.get("bio"),
        "|".join([tag[0] for tag in tags]),
        data.get("price_per_hour"),
    ]
    for index, value in enumerate(data.copy()):
        if isinstance(value, str):
            data[index] = html.escape(value)
    # add it later so it doesn't get escaped
    data.append(json.dumps(contact))
    return data


def parse_db_data_to_json(db_data, cursor) -> dict:
    uuid, title_before, first_name, middle_name, last_name, title_after, picture_url, location, claim, bio, tags, price_per_hour, contact = db_data

    tags_data = [i for i in tags.split("|")]

    placeholders = ",".join("?" for _ in [i for i in tags.split("|")])
    query = f"SELECT * FROM tags WHERE uuid IN ({placeholders})"
    cursor.execute(query, tags_data)
    tags_from_db = cursor.fetchall()

    contact = json.loads(contact)

    return get_lecturer_as_json({
        "uuid": uuid,
        "title_before": title_before,
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "title_after": title_after,
        "picture_url": picture_url,
        "location": location,
        "claim": claim,
        "bio": bio,
        "tags": tags,
        "price_per_hour": price_per_hour,
        "contact": contact
    }, uuid, tags_from_db)


@app.route("/api/lecturers/<uuid>", methods=["GET", "PUT", "DELETE"])
@app.route("/api/lecturers", methods=["GET", "POST"], defaults={"uuid": 0})
def api_lecturers(uuid):
    database = db.get_db()
    cursor = database.cursor()
    match request.method:
        case "GET":
            if not uuid:
                cursor.execute("SELECT * FROM lecturers")
                lecturers = cursor.fetchall()
                all_lecturers = []
                for lect in lecturers:
                    all_lecturers.append(parse_db_data_to_json(lect, cursor))
                return jsonify(all_lecturers), 200
            else:
                cursor.execute("SELECT * FROM lecturers WHERE uuid=:uuid", {"uuid": uuid})
                fetch = cursor.fetchall()
                if not fetch:
                    return {"code": 404, "message": "User not found"}, 404
                return jsonify(parse_db_data_to_json(fetch[0], cursor)), 200
        case "POST":
            data = request.json
            if not data:
                return {"code": 403, "message": "Cannot add lecturer without any data"}, 403
            if not check_keys(data):
                return {"code": 403, "message": "Cannot add lecturer. Json dose not have all the needed keys"}, 403
            if uuid or uuid != 0 or data["uuid"]:
                if not uuid or uuid != 0:
                    uuid = data["uuid"]
                cursor.execute("SELECT * FROM lecturers WHERE uuid=:uuid", {"uuid": uuid})
                fetch = cursor.fetchall()
                if fetch:
                    return {"code": 403, "message": "Lecturer with this uuid already exists"}, 403
            else:
                uuid = str(uuid4())
            data["tags"] = [tag["name"].capitalize() for tag in data["tags"]]
            placeholders = ",".join("?" for _ in data["tags"])
            query = f"SELECT * FROM tags WHERE name IN ({placeholders})"
            cursor.execute(query, data["tags"])
            tags_in_db = cursor.fetchall()

            tags_not_in_db = [tag for tag in data["tags"] if tag not in tags_in_db]

            tags_to_db = []
            for tag in tags_not_in_db:
                tags_to_db.append((str(uuid4()), tag))

            cursor.executemany("INSERT INTO tags VALUES (?, ?)", tags_to_db)

            tags = tags_in_db + tags_to_db

            value = get_lecturer_db_insert_value(data, uuid, tags)
            return_value = get_lecturer_as_json(data, uuid, tags)

            cursor.execute("INSERT INTO lecturers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", value)
            database.commit()
            return return_value, 200
        case "PUT":
            pass
        case "DELETE":
            pass
        case _:
            return {"message": "Unsupported method", "code": 405}, 405


@app.route("/lecturer")
def lecturer():
    return render_template("lecturer.html"), 200


@app.route("/logs")
def logs():
    return {"logs": str(output_buffer.getvalue())}


if __name__ == '__main__':
    app.run(debug=True)
