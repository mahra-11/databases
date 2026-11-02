"""Database access: one PyMySQL connection per request, plus small query helpers.

Every query in the application goes through these helpers and passes user input
as parameters (%s placeholders), never by string formatting, so the driver
escapes all values and SQL injection is not possible.
"""
import pymysql
from flask import g

import config


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def query_all(sql, args=()):
    with get_db().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def query_one(sql, args=()):
    with get_db().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()


def execute(sql, args=()):
    """Run an INSERT/UPDATE/DELETE and commit. Returns the last inserted id."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            last_id = cur.lastrowid
        conn.commit()
        return last_id
    except Exception:
        conn.rollback()
        raise
