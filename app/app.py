import json
import os
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
from . import db

from bs4 import BeautifulSoup

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


def sanitize_html(input_string):
    soup = BeautifulSoup(input_string, "html.parser")
    allowed_tags = ["b", "i", "u", "br"]
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.replace_with(tag.text)
    return str(soup)


def save_conv(value, conv_to):
    try:
        return conv_to(value)
    except Exception as e:
        print(f"exception when converting {value} to {conv_to}: {e}")
        # return default value if error
        return conv_to()


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
        "telephone_numbers": json.loads(sanitize_html(json.dumps(data["contact"]["telephone_numbers"]))),
        "emails": json.loads(sanitize_html(json.dumps(data["contact"]["emails"])))
    }

    return {
        "uuid": sanitize_html(uuid) if uuid else str(uuid4()),
        "title_before": sanitize_html(data.get("title_before")),
        "first_name": sanitize_html(data.get("first_name")),
        "middle_name": sanitize_html(data.get("middle_name")),
        "last_name": sanitize_html(data.get("last_name")),
        "title_after": sanitize_html(data.get("title_after")),
        "picture_url": sanitize_html(data.get("picture_url")),
        "location": sanitize_html(data.get("location")),
        "claim": sanitize_html(data.get("claim")),
        "bio": sanitize_html(data.get("bio")),
        "tags": [{"uuid": sanitize_html(tag["uuid"]), "name": sanitize_html(tag["name"])} for tag in tags],
        "price_per_hour": save_conv(data.get("price_per_hour"), int),
        "contact": contact
    }


def get_lecturer_db_insert_value(data, uuid, tags):
    contact = {
        "telephone_numbers": json.loads(sanitize_html(json.dumps(data["contact"]["telephone_numbers"]))),
        "emails": json.loads(sanitize_html(json.dumps(data["contact"]["emails"]))),
    }
    data = [
        sanitize_html(uuid) if uuid else str(uuid4()),
        sanitize_html(data.get("title_before")),
        sanitize_html(data.get("first_name")),
        sanitize_html(data.get("middle_name")),
        sanitize_html(data.get("last_name")),
        sanitize_html(data.get("title_after")),
        sanitize_html(data.get("picture_url")),
        sanitize_html(data.get("location")),
        sanitize_html(data.get("claim")),
        sanitize_html(data.get("bio")),
        "|".join([sanitize_html(tag["uuid"]) for tag in tags]),
        save_conv(data.get("price_per_hour"), int),
        json.dumps(contact)
    ]
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
@app.route("/api/lecturers", methods=["GET", "POST"], defaults={"uuid": None})
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
                # TODO: Expected 404
                fetch = cursor.fetchall()
                if not fetch:
                    return {"code": 404, "message": "User not found"}, 404
                return jsonify(parse_db_data_to_json(fetch[0], cursor)), 200
        case "POST":
            data = request.json
            if "tags" not in data:
                return "?"
            data["tags"] = [{"name": tag["name"].capitalize()} for tag in data["tags"]]
            placeholders = ",".join("?" for _ in data["tags"])
            query = f"SELECT * FROM tags WHERE name IN ({placeholders})"
            cursor.execute(query, [tag["name"] for tag in data["tags"]])
            tags_in_db = [{"uuid": tag["uuid"], "name": tag["name"]} for tag in cursor.fetchall()]
            tags_not_in_db = [user_tag for user_tag in data["tags"] if
                              user_tag["name"] not in [tag["name"] for tag in tags_in_db]]
            tags_to_db = []
            for tag in tags_not_in_db:
                tags_to_db.append((str(uuid4()), tag["name"]))

            cursor.executemany("INSERT INTO tags VALUES (?, ?)", tags_to_db)

            tags = tags_in_db + [{"uuid": tag[0], "name": tag[1]} for tag in tags_to_db]

            value = get_lecturer_db_insert_value(data, uuid, tags)
            return_value = get_lecturer_as_json(data, uuid, tags)

            cursor.execute("INSERT INTO lecturers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", value)
            database.commit()
            return return_value, 200
        case "PUT":
            pass
        case "DELETE":
            if not uuid:
                return jsonify({"code": 404, "message": "User not found"}), 404
            cursor.execute("SELECT * FROM lecturers WHERE uuid=:uuid", {"uuid": uuid})
            fetch = cursor.fetchall()
            if not fetch:
                return {"code": 404, "message": "User not found"}, 404
            cursor.execute("DELETE FROM lecturers WHERE uuid=:uuid", {"uuid": uuid})
            return {}, 200
        case _:
            return {"message": "Unsupported method", "code": 405}, 405


@app.route("/lecturer")
def lecturer():
    return render_template("lecturer.html"), 200


if __name__ == '__main__':
    app.run(debug=True)
