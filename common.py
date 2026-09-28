import os

import mysql.connector
from pymongo import MongoClient


def get_mysql_connection(database=None):
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ["MYSQL_PASSWORD"],  # obrigatório via env
        database=database or os.environ.get("MYSQL_DATABASE", "cp2_seguranca"),
    )


def get_mongo_client():
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    return MongoClient(uri)


def get_mongo_db(client=None):
    client = client or get_mongo_client()
    return client[os.environ.get("MONGO_DATABASE", "cp2_seguranca")]
