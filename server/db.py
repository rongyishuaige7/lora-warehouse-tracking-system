"""数据库连接与初始化。"""
import sqlite3
from config_loader import DB_PATH


def configure_db(conn: sqlite3.Connection) -> None:
    """为 SQLite 连接设置 WAL、超时等参数。"""
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")
    except Exception:
        pass


def get_db_connection(*, row_factory: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    configure_db(conn)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """创建表与索引。"""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            name TEXT,
            region TEXT,
            status TEXT,
            temperature REAL,
            humidity REAL,
            battery REAL,
            rssi INTEGER,
            gateway_id TEXT,
            last_update INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            status TEXT,
            temperature REAL,
            humidity REAL,
            battery REAL,
            rssi INTEGER,
            gateway_id TEXT,
            timestamp INTEGER,
            FOREIGN KEY (device_id) REFERENCES devices (device_id)
        )''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_devices_region ON devices(region)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_devices_last_update ON devices(last_update)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_history_device_timestamp ON history(device_id, timestamp)")
        conn.commit()
        print(f"Database initialized: {DB_PATH}")
    finally:
        conn.close()
