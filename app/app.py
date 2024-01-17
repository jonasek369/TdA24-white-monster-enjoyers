import json
import os
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
from . import db
import re

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

replacable_keys = [
    ("uuid", True),
    ("title_before", True),
    ("first_name", False),
    ("middle_name", True),
    ("last_name", False),
    ("title_after", True),
    ("picture_url", True),
    ("location", True),
    ("claim", True),
    ("bio", True),
    ("tags", True),
    ("price_per_hour", True),
    ("contact", False)
]

telephone_regex = r"^(?:(?:\+|00)\d{1,3})?[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,10}[-.\s]?\d{1,10}$"
email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


def is_replacable_key(key) -> [bool, bool, str]:
    for rep_key, nullable in replacable_keys:
        if rep_key == key:
            return True, nullable, rep_key
    return False, False


@app.route('/')
def hello_tda():
    return "Hello TdA"


@app.route('/api')
def api():
    return jsonify({"secret": "The cake is a lie"}), 200


def sanitize_html(input_string):
    if input_string is None:
        return None
    if not isinstance(input_string, str):
        input_string = str(input_string)
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


def regex_check_list(_list, regex):
    for number in _list:
        if re.match(regex, number) is None:
            return False
    return True


def check_keys(data):
    for key in ["first_name", "last_name"]:
        if key not in data:
            return False
    for nested_keys in [["contact", "telephone_numbers"], ["contact", "emails"]]:
        if not data.get(nested_keys[0]) or nested_keys[1] not in data.get(nested_keys[0]):
            return False
    if len(data["contact"]["telephone_numbers"]) == 0 or not regex_check_list(data["contact"]["telephone_numbers"],
                                                                              telephone_regex):
        return False
    if len(data["contact"]["emails"]) == 0 or not regex_check_list(data["contact"]["emails"], email_regex):
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
@app.route("/api/lecturers", methods=["GET", "PUT", "POST"], defaults={"uuid": None})
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
                cursor.close()
                return jsonify(all_lecturers), 200
            else:
                cursor.execute("SELECT * FROM lecturers WHERE uuid=:uuid", {"uuid": uuid})
                fetch = cursor.fetchall()
                if not fetch:
                    return {"code": 404, "message": "User not found"}, 404
                json_data = parse_db_data_to_json(fetch[0], cursor)
                cursor.close()
                return jsonify(json_data), 200
        case "POST":
            data = request.json
            if not check_keys(data):
                cursor.close()
                return {"code": 403, "message": "bad data"}, 403
            uuid = str(uuid4())
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

            if tags_to_db:
                cursor.executemany("INSERT INTO tags VALUES (?, ?)", tags_to_db)

            tags = tags_in_db + [{"uuid": tag[0], "name": tag[1]} for tag in tags_to_db]

            value = get_lecturer_db_insert_value(data, uuid, tags)
            return_value = get_lecturer_as_json(data, uuid, tags)
            if value[2] is None or value[4] is None:
                cursor.close()
                return {"code": 403, "message": "missing values"}, 403
            cursor.execute("INSERT INTO lecturers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", value)
            database.commit()
            cursor.close()
            return return_value, 200
        case "PUT":
            data = request.json
            if not uuid:
                cursor.close()
                return jsonify({"code": 404, "message": "User not found"}), 404
            cursor.execute("SELECT * FROM lecturers WHERE uuid=:uuid", {"uuid": uuid})
            fetch = cursor.fetchall()
            if not fetch:
                return jsonify({"code": 404, "message": "User not found"}), 404
            for key, value in data.items():
                is_key, nullable, key_name = is_replacable_key(key)
                if not is_key:
                    continue
                if nullable and value is None:
                    continue

                if key == "contact":
                    if "telephone_numbers" not in data["contact"] or "emails" not in data["contact"]:
                        continue
                    if len(data["contact"]["telephone_numbers"]) == 0 or not regex_check_list(
                            data["contact"]["telephone_numbers"], telephone_regex):
                        continue
                    if len(data["contact"]["emails"]) == 0 or not regex_check_list(data["contact"]["emails"],
                                                                                   email_regex):
                        continue
                    to_db = json.dumps({
                        "telephone_numbers": json.loads(
                            sanitize_html(json.dumps(data["contact"]["telephone_numbers"]))),
                        "emails": json.loads(sanitize_html(json.dumps(data["contact"]["emails"]))),
                    })
                elif key == "tags":
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

                    if tags_to_db:
                        cursor.executemany("INSERT INTO tags VALUES (?, ?)", tags_to_db)

                    tags = tags_in_db + [{"uuid": tag[0], "name": tag[1]} for tag in tags_to_db]

                    to_db = "|".join([sanitize_html(tag["uuid"]) for tag in tags])
                else:
                    to_db = sanitize_html(value)
                cursor.execute(f"UPDATE lecturers SET {str(key_name)}=:data WHERE uuid=:uuid", {"data": to_db, "uuid": uuid})
            database.commit()
            json_data = parse_db_data_to_json(fetch[0], cursor)
            cursor.close()
            return json_data, 200
        case "DELETE":
            if not uuid:
                cursor.close()
                return jsonify({"code": 404, "message": "User not found"}), 404
            cursor.execute("SELECT * FROM lecturers WHERE uuid=:uuid", {"uuid": uuid})
            fetch = cursor.fetchall()
            if not fetch:
                cursor.close()
                return {"code": 404, "message": "User not found"}, 404
            cursor.execute("DELETE FROM lecturers WHERE uuid=:uuid", {"uuid": uuid})
            database.commit()
            cursor.close()
            return {}, 200
        case _:
            cursor.close()
            return {"message": "Unsupported method", "code": 405}, 405


@app.route("/lecturer")
def lecturer():
    return render_template("lecturer.html"), 200


if __name__ == '__main__':
    app.run(debug=True)
