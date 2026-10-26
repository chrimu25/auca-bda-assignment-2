"""Persistent connections and the two query wrappers used everywhere (Sections 4-7).

run_pg(query, params)  -> list of tuples (every result row)
run_neo(query, params) -> list of tuples (every result row, in RETURN order)
Values are normalised so results from both engines can be compared exactly.
"""
import os
from datetime import date, datetime
from decimal import Decimal

import psycopg
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

_pg = None
_neo = None


def pg_conn():
    global _pg
    if _pg is None or _pg.closed:
        _pg = psycopg.connect(
            host=os.getenv("PGHOST", "localhost"), port=os.getenv("PGPORT", "5432"),
            dbname=os.getenv("PGDATABASE", "mobile_money"), user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD"), autocommit=True)
    return _pg


def neo_driver():
    global _neo
    if _neo is None:
        _neo = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                                    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD")))
    return _neo


def normalise(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (list, tuple)):
        return tuple(normalise(v) for v in value)
    if hasattr(value, "to_native"):          # neo4j temporal types
        value = value.to_native()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def run_pg(query, params=None):
    with pg_conn().cursor() as cur:
        cur.execute(query, params or {})
        rows = cur.fetchall() if cur.description else []
    return [tuple(normalise(v) for v in row) for row in rows]


def run_neo(query, params=None):
    with neo_driver().session(database="neo4j") as session:
        result = session.run(query, params or {})
        rows = [tuple(normalise(v) for v in record.values()) for record in result]
    return rows


def close():
    global _pg, _neo
    if _pg is not None:
        _pg.close(); _pg = None
    if _neo is not None:
        _neo.close(); _neo = None
