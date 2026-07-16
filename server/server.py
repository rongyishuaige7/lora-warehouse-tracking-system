"""
仓库物品追踪系统 - Flask 服务器
功能：接收网关数据，提供 REST API 给 APP。
配置、DB、网关客户端已拆至 config_loader / db / gateway_client。
"""
import os
import json
import sys
import time
import sqlite3
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify

import config_loader

config_loader.load_config()
from config_loader import DB_PATH, GATEWAY_IPS
import db
import gateway_client


def _log(level: str, msg: str, *args) -> None:
    line = f"[{level}] {msg % args}" if args else f"[{level}] {msg}"
    print(line, file=sys.stderr, flush=True)


def _error_response(message: str, status_code: int = 500, code: Optional[str] = None) -> tuple:
    body = {"status": "error", "message": message}
    if code:
        body["code"] = code
    return jsonify(body), status_code


app = Flask(__name__)
try:
    from flask_cors import CORS  # type: ignore
except ImportError:
    CORS = None

cors_origins = [
    origin.strip()
    for origin in os.environ.get("WAREHOUSE_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if CORS and cors_origins:
    CORS(app, origins=cors_origins)
    CORS_MODE = "restricted"
else:
    # The Android client does not need browser CORS. Browser access is disabled
    # by default; explicitly list trusted origins through WAREHOUSE_CORS_ORIGINS.
    CORS_MODE = "disabled"


@app.route('/api/report', methods=['POST'])
def report():
    """网关上报设备数据"""
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"status": "error", "message": "Invalid JSON body"}), 400

        _log("DEBUG", "Report: gateway=%s region=%s", data.get("gateway_id"), data.get("region"))

        gateway_id = data.get('gateway_id', 'UNKNOWN')
        region = data.get('region', 'UNKNOWN')
        rssi = data.get('rssi', 0)

        def normalize_device_data(raw):
            """兼容网关上报的dict或JSON字符串，返回规范化dict"""
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:
                    raise ValueError("Invalid tag JSON string")

            if not isinstance(raw, dict):
                raise ValueError("Invalid tag data type")

            device_id = raw.get('device_id')
            if not device_id:
                raise ValueError("device_id required")

            return {
                "device_id": device_id,
                "status": raw.get('status', 'OK'),
                "temperature": raw.get('temp'),
                "humidity": raw.get('humidity'),
                "battery": raw.get('battery'),
                "tag_timestamp": raw.get('timestamp', 0),
                "region": raw.get('region'),
            }

        # 支持两种格式：
        # 1) 单设备：{"data": {...}}
        # 2) 多设备：{"tags": [{...}, {...}]}
        raw_tags = data.get('tags')
        if isinstance(raw_tags, list):
            tag_payloads = raw_tags
        else:
            tag_payloads = [data.get('data', {})]

        # 使用服务器接收时间作为last_update，避免标签重启后millis()/1000回到0导致排序错乱
        timestamp = int(time.time())

        # 先规范化并收集 device_id，再一次性查询现有位置，减少 N 次 SELECT
        tags = []
        device_ids = []
        for raw_tag in tag_payloads:
            tag = normalize_device_data(raw_tag)
            tags.append(tag)
            device_ids.append(tag["device_id"])

        existing = {}
        conn = db.get_db_connection()
        try:
            c = conn.cursor()
            if device_ids:
                placeholders = ",".join("?" * len(device_ids))
                c.execute(
                    f"""SELECT device_id, region, rssi, last_update, gateway_id
                        FROM devices WHERE device_id IN ({placeholders})""",
                    device_ids,
                )
                for row in c.fetchall():
                    existing[row[0]] = (row[1], row[2], row[3], row[4])

            processed = []
            for tag in tags:
                row = existing.get(tag["device_id"])
                # Receiving gateway is authoritative for location. The tag's
                # region is only a fallback when the gateway cannot identify
                # its own region.
                tag_declared_region = tag.get("region")
                gateway_region_known = (
                    isinstance(region, str)
                    and bool(region.strip())
                    and region.strip().upper() != "UNKNOWN"
                )
                final_region = region.strip() if gateway_region_known else tag_declared_region
                if not final_region:
                    final_region = "UNKNOWN"
                final_rssi = rssi
                final_gateway_id = gateway_id
                if row:
                    old_region, old_rssi, old_time, old_gateway_id = row
                    if timestamp - old_time < 3 and (old_rssi is not None) and rssi < old_rssi:
                        final_region = old_region
                        final_rssi = old_rssi
                        final_gateway_id = old_gateway_id
                        _log("DEBUG", "Skip region for %s: stronger at %s", tag["device_id"], old_region)

                # 更新设备主表
                c.execute('''INSERT INTO devices
                             (device_id, name, region, status, temperature, humidity, battery, rssi, gateway_id, last_update)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                             ON CONFLICT(device_id) DO UPDATE SET
                             region=excluded.region,
                             status=excluded.status,
                             temperature=excluded.temperature,
                             humidity=excluded.humidity,
                             battery=excluded.battery,
                             rssi=excluded.rssi,
                             gateway_id=excluded.gateway_id,
                             last_update=excluded.last_update''',
                          (tag["device_id"], tag["device_id"], final_region, tag["status"],
                           tag["temperature"], tag["humidity"], tag["battery"], final_rssi,
                           final_gateway_id, timestamp))

                # 插入历史记录
                c.execute('''INSERT INTO history
                             (device_id, status, temperature, humidity, battery, rssi, gateway_id, timestamp)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                          (tag["device_id"], tag["status"], tag["temperature"], tag["humidity"],
                           tag["battery"], rssi, gateway_id, timestamp))

                processed.append(tag)

            conn.commit()
        finally:
            conn.close()

        return jsonify({
            "status": "ok",
            "message": "Data saved",
            "count": len(processed),
            "gateway_id": gateway_id,
            "region": region,
            "rssi": rssi,
            "server_timestamp": timestamp,
            "processed": processed[:20],
        })

    except ValueError as e:
        _log("WARN", "Report validation: %s", e)
        return _error_response(str(e), 400)
    except Exception as e:
        _log("ERROR", "Report failed: %s", e)
        return _error_response(str(e), 500)


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """获取所有设备列表"""
    try:
        conn = db.get_db_connection(row_factory=True)
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM devices ORDER BY last_update DESC")
            rows = c.fetchall()
        finally:
            conn.close()

        devices = []
        for row in rows:
            devices.append(dict(row))

        return jsonify(devices)

    except sqlite3.Error as e:
        _log("ERROR", "get_devices: %s", e)
        return _error_response("Database error", 500, "db_error")
    except Exception as e:
        _log("ERROR", "get_devices: %s", e)
        return _error_response(str(e), 500)


@app.route('/api/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    """获取单个设备信息"""
    try:
        conn = db.get_db_connection(row_factory=True)
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
            row = c.fetchone()
        finally:
            conn.close()

        if row:
            return jsonify(dict(row))
        return _error_response("Device not found", 404, "not_found")

    except sqlite3.Error as e:
        _log("ERROR", "get_device: %s", e)
        return _error_response("Database error", 500, "db_error")
    except Exception as e:
        _log("ERROR", "get_device: %s", e)
        return _error_response(str(e), 500)


@app.route('/api/search', methods=['GET'])
def search_devices():
    """搜索设备"""
    keyword = request.args.get('q', '')

    try:
        conn = db.get_db_connection(row_factory=True)
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM devices WHERE device_id LIKE ? OR name LIKE ?",
                      (f'%{keyword}%', f'%{keyword}%'))
            rows = c.fetchall()
        finally:
            conn.close()

        devices = [dict(row) for row in rows]
        return jsonify(devices)

    except sqlite3.Error as e:
        _log("ERROR", "search_devices: %s", e)
        return _error_response("Database error", 500, "db_error")
    except Exception as e:
        _log("ERROR", "search_devices: %s", e)
        return _error_response(str(e), 500)


@app.route('/api/regions', methods=['GET'])
def get_regions():
    """获取区域统计"""
    try:
        conn = db.get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT region, COUNT(*) as count FROM devices GROUP BY region")
            rows = c.fetchall()
        finally:
            conn.close()

        result = {}
        for row in rows:
            if row[0]:
                result[row[0]] = row[1]

        # 确保A和B区域都有返回值
        if 'A' not in result:
            result['A'] = 0
        if 'B' not in result:
            result['B'] = 0

        return jsonify(result)

    except sqlite3.Error as e:
        _log("ERROR", "get_regions: %s", e)
        return _error_response("Database error", 500, "db_error")
    except Exception as e:
        _log("ERROR", "get_regions: %s", e)
        return _error_response(str(e), 500)


@app.route('/api/locate', methods=['POST'])
def locate():
    """返回最近区域并尝试下发语音；不声称标签已收到或实际播放。"""
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return _error_response("Invalid JSON body", 400, "bad_request")

        device_id = data.get('device_id')
        if not device_id:
            return _error_response("device_id required", 400, "bad_request")

        conn = db.get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT region, last_update FROM devices WHERE device_id = ?", (device_id,))
            row = c.fetchone()
        finally:
            conn.close()

        if not row or not row[0]:
            return _error_response("Device not found", 404, "not_found")

        region = row[0]
        last_update = row[1] if row[1] is not None else 0
        gateway_command_sent, gateway_error = gateway_client.send_play_voice(region, device_id)
        if not gateway_command_sent and gateway_error:
            _log("WARN", "Locate gateway: %s", gateway_error)

        age_seconds = max(0, int(time.time()) - last_update) if last_update else None
        if gateway_command_sent:
            message = (
                f"最近一次上报位于区域{region}；语音指令已下发到网关，"
                "但未确认标签收到或播放。若标签正在深睡，请在下一次心跳后重试。"
            )
        else:
            message = f"最近一次上报位于区域{region}；语音指令未下发：{gateway_error}"

        return jsonify({
            "region": region,
            "device_id": device_id,
            "message": message,
            "gateway_command_sent": gateway_command_sent,
            "gateway_error": gateway_error,
            "tag_delivery_confirmed": False,
            "last_report_age_seconds": age_seconds,
        })

    except sqlite3.Error as e:
        _log("ERROR", "locate db: %s", e)
        return _error_response("Database error", 500, "db_error")
    except Exception as e:
        _log("ERROR", "locate: %s", e)
        return _error_response(str(e), 500)


@app.route('/api/history/<device_id>', methods=['GET'])
def get_history(device_id):
    """获取设备历史记录"""
    try:
        limit_raw = request.args.get('limit', '50')
        try:
            limit = int(limit_raw)
        except Exception:
            limit = 50
        limit = max(1, min(limit, 500))

        conn = db.get_db_connection(row_factory=True)
        try:
            c = conn.cursor()
            c.execute("""SELECT * FROM history
                         WHERE device_id = ?
                         ORDER BY timestamp DESC
                         LIMIT ?""",
                      (device_id, limit))
            rows = c.fetchall()
        finally:
            conn.close()

        history = [dict(row) for row in rows]
        return jsonify(history)

    except sqlite3.Error as e:
        _log("ERROR", "get_history: %s", e)
        return _error_response("Database error", 500, "db_error")
    except Exception as e:
        _log("ERROR", "get_history: %s", e)
        return _error_response(str(e), 500)


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "database_configured": bool(DB_PATH),
        "cors_mode": CORS_MODE,
        "gateway_regions": sorted(GATEWAY_IPS.keys()),
    })


if __name__ == '__main__':
    db.init_db()
    print("Starting Warehouse Tracker Server...")
    host = os.environ.get("WAREHOUSE_HOST", "0.0.0.0")
    port_raw = os.environ.get("WAREHOUSE_PORT", "5000")
    try:
        port = int(port_raw)
    except Exception:
        port = 5000

    debug_raw = os.environ.get("WAREHOUSE_DEBUG", "0").strip().lower()
    debug = debug_raw not in {"0", "false", "no", "off"}

    print(f"Server running on http://{host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)
