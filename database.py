import sqlite3
from datetime import datetime

DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        category INTEGER,
        activation_date TEXT,
        last_checkin TEXT,
        total_earned REAL DEFAULT 0.0,
        total_penalty REAL DEFAULT 0.0,
        active INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    )''')
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str, category: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""INSERT OR REPLACE INTO users 
                 (user_id, username, category, activation_date, last_checkin, total_earned, total_penalty, active)
                 VALUES (?, ?, ?, ?, ?, 0.0, 0.0, 1)""",
              (user_id, username, category, now, now))
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()

    if res:
        return {
            "user_id": res[0],
            "username": res[1],
            "category": res[2],
            "activation_date": res[3],
            "last_checkin": res[4],
            "total_earned": res[5],
            "total_penalty": res[6],
            "active": bool(res[7])
        }
    return None

def update_checkin(user_id: int, date_iso: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET last_checkin = ? WHERE user_id = ?", (date_iso, user_id))
    conn.commit()
    conn.close()

def add_penalty(user_id: int, amount: float):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET total_penalty = total_penalty + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def add_earnings(user_id: int, amount: float):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def deactivate_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET active = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_active_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE active = 1")
    res = c.fetchall()
    conn.close()
    return [r[0] for r in res]

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, username, category, total_earned, total_penalty, active FROM users")
    res = c.fetchall()
    conn.close()
    return res
