"""
SQLite storage for CryptoAI dashboard
Stores price snapshots and predictions for auditability
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime

DB_PATH = "cryptoai.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                coin_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                change_24h REAL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                coin_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                predicted_price REAL NOT NULL,
                predicted_change_pct REAL NOT NULL,
                confidence REAL NOT NULL,
                direction TEXT NOT NULL,
                model TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_price_snapshot(
    coin_id: str,
    symbol: str,
    price: float,
    change_24h: float = 0.0,
    timestamp: Optional[str] = None,
) -> None:
    ts = timestamp or datetime.now().isoformat()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO price_snapshots (timestamp, coin_id, symbol, price, change_24h)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, coin_id, symbol, float(price), float(change_24h)),
        )
        conn.commit()
    finally:
        conn.close()


def log_prediction(
    coin_id: str,
    symbol: str,
    predicted_price: float,
    predicted_change_pct: float,
    confidence: float,
    direction: str,
    model: str,
    timestamp: Optional[str] = None,
) -> None:
    ts = timestamp or datetime.now().isoformat()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO predictions (
                timestamp, coin_id, symbol, predicted_price,
                predicted_change_pct, confidence, direction, model
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                coin_id,
                symbol,
                float(predicted_price),
                float(predicted_change_pct),
                float(confidence),
                direction,
                model,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_prices(limit: int = 25) -> List[Dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp, coin_id, symbol, price, change_24h
            FROM price_snapshots
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "timestamp": r[0],
                "coin_id": r[1],
                "symbol": r[2],
                "price": r[3],
                "change_24h": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_recent_predictions(limit: int = 25) -> List[Dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp, coin_id, symbol, predicted_price,
                   predicted_change_pct, confidence, direction, model
            FROM predictions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "timestamp": r[0],
                "coin_id": r[1],
                "symbol": r[2],
                "predicted_price": r[3],
                "predicted_change_pct": r[4],
                "confidence": r[5],
                "direction": r[6],
                "model": r[7],
            }
            for r in rows
        ]
    finally:
        conn.close()
