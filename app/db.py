import json
import sqlite3
import time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, role TEXT, token TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY, ts REAL, user TEXT, action TEXT, ref TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS posts(
  id INTEGER PRIMARY KEY, title TEXT, bucket TEXT, hero TEXT, format TEXT, caption TEXT, cta TEXT,
  hashtags TEXT, flags TEXT, status TEXT, is_paid INTEGER DEFAULT 0, is_creator INTEGER DEFAULT 0,
  scheduled_for REAL, published_at REAL, platform_ids TEXT, created_by TEXT, created_at REAL,
  reviewer TEXT, review_note TEXT);
CREATE TABLE IF NOT EXISTS post_metrics(id INTEGER PRIMARY KEY, post_id INTEGER, ts REAL,
  reach INTEGER, views INTEGER, likes INTEGER, comments INTEGER, saves INTEGER, shares INTEGER,
  profile_visits INTEGER, link_clicks INTEGER, wa_clicks INTEGER, followers INTEGER);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY, channel TEXT, ext_id TEXT, sender TEXT, body TEXT, ts REAL, post_id INTEGER,
  category TEXT, status TEXT, reply TEXT, replied_at REAL, auto INTEGER DEFAULT 0, escalate_to TEXT);
CREATE TABLE IF NOT EXISTS leads(
  id INTEGER PRIMARY KEY, name TEXT, phone TEXT, source TEXT, interest TEXT, stage TEXT, score INTEGER,
  value REAL, owner TEXT, notes TEXT, created_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS calls(id INTEGER PRIMARY KEY, caller TEXT, ts REAL, transcript TEXT,
  answer TEXT, language TEXT, duration REAL, lead_id INTEGER, handled_by TEXT);
CREATE TABLE IF NOT EXISTS site_checks(id INTEGER PRIMARY KEY, ts REAL, url TEXT, ok INTEGER,
  status INTEGER, ms REAL, ssl_days INTEGER, error TEXT);
CREATE TABLE IF NOT EXISTS automation_events(id INTEGER PRIMARY KEY, ts REAL, kind TEXT, ref TEXT);
"""


class DB:
    def __init__(self, path):
        self.path = path
        with self.conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def q(self, sql, args=()):
        with self.conn() as c:
            return [dict(r) for r in c.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        r = self.q(sql, args)
        return r[0] if r else None

    def x(self, sql, args=()):
        with self.conn() as c:
            return c.execute(sql, args).lastrowid

    def audit(self, user, action, ref="", detail=None):
        self.x("INSERT INTO audit_log(ts,user,action,ref,detail) VALUES(?,?,?,?,?)",
               (time.time(), user, action, str(ref), json.dumps(detail or {})))

    def automation(self, kind, ref=""):
        self.x("INSERT INTO automation_events(ts,kind,ref) VALUES(?,?,?)", (time.time(), kind, str(ref)))
