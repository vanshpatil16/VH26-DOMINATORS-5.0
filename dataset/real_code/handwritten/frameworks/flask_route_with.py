"""A request handler on the hot path, handled correctly."""

import contextlib
import sqlite3

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/people")
def list_people():
    with contextlib.closing(sqlite3.connect("app.db")) as connection:
        rows = connection.execute("SELECT name FROM people").fetchall()
    return jsonify([row[0] for row in rows])
