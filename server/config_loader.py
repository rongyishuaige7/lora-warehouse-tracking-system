"""配置加载：DB 路径、网关 IP 映射，支持 config.json 与环境变量。"""
import os
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_GATEWAY_IPS = {}
GATEWAY_IPS = dict(DEFAULT_GATEWAY_IPS)
DB_PATH = str(BASE_DIR / "warehouse.db")


def _log(level: str, msg: str, *args) -> None:
    line = f"[{level}] {msg % args}" if args else f"[{level}] {msg}"
    print(line, file=sys.stderr, flush=True)


def _normalize_path(path_str: str) -> str:
    path = Path(path_str)
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    return str(path)


def load_config() -> None:
    """加载可选配置文件/环境变量。"""
    global DB_PATH, GATEWAY_IPS
    GATEWAY_IPS = dict(DEFAULT_GATEWAY_IPS)

    config_path = Path(os.environ.get("WAREHOUSE_CONFIG_PATH", str(BASE_DIR / "config.json")))
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            _log("WARN", "Failed to parse config file: %s (%s)", config_path, e)
            config = {}

    if isinstance(config, dict):
        cfg_db_path = config.get("db_path")
        if isinstance(cfg_db_path, str) and cfg_db_path.strip() and not os.environ.get("WAREHOUSE_DB_PATH"):
            DB_PATH = _normalize_path(cfg_db_path.strip())
        cfg_gateway_ips = config.get("gateway_ips")
        if isinstance(cfg_gateway_ips, dict):
            sanitized = {}
            for k, v in cfg_gateway_ips.items():
                if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                    sanitized[k.strip()] = v.strip()
            GATEWAY_IPS = sanitized

    env_db_path = os.environ.get("WAREHOUSE_DB_PATH")
    if env_db_path and env_db_path.strip():
        DB_PATH = _normalize_path(env_db_path.strip())
