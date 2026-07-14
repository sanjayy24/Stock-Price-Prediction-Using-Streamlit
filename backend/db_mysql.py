# backend/db_mysql.py
import pymysql

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "root",
    "database": "stock_db",
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def fetch_one(sql, params=()):
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        con.close()

def execute(sql, params=()):
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount
    finally:
        con.close()
