"""FastAPI dependency: the framework drives the generator to completion."""

import sqlite3

from fastapi import Depends, FastAPI

app = FastAPI()


def get_db():
    connection = sqlite3.connect("app.db")
    try:
        yield connection
    finally:
        connection.close()


@app.get("/people")
def list_people(db=Depends(get_db)):
    return [row[0] for row in db.execute("SELECT name FROM people")]
