"""API 核心路径：health, report, devices, locate."""
import json
import pytest


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") == "ok"
    assert "timestamp" in data
    assert "gateway_regions" in data


def test_report_invalid_body(client):
    r = client.post("/api/report", data="not json", content_type="application/json")
    assert r.status_code in (400, 500)


def test_report_missing_device_id(client):
    r = client.post(
        "/api/report",
        data=json.dumps({"gateway_id": "GW001", "region": "A", "rssi": -70, "data": {}}),
        content_type="application/json",
    )
    assert r.status_code == 400
    data = r.get_json()
    assert data.get("status") == "error"
    assert "device_id" in data.get("message", "").lower() or "required" in data.get("message", "").lower()


def test_report_ok(client):
    r = client.post(
        "/api/report",
        data=json.dumps({
            "gateway_id": "GW001",
            "region": "A",
            "rssi": -70,
            "data": {
                "device_id": "TAG001",
                "status": "OK",
                "temp": 25,
                "humidity": 60,
                "battery": 3.7,
                "timestamp": 123,
            },
        }),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") == "ok"
    assert data.get("count") == 1


def test_receiving_gateway_region_is_authoritative(client):
    r = client.post(
        "/api/report",
        data=json.dumps({
            "gateway_id": "GW_B",
            "region": "B",
            "rssi": -55,
            "data": {
                "device_id": "TAG_REGION_AUTH",
                "region": "A",
                "status": "OK",
                "temp": None,
                "humidity": None,
                "battery": None,
                "timestamp": 123,
            },
        }),
        content_type="application/json",
    )
    assert r.status_code == 200
    device = client.get("/api/devices/TAG_REGION_AUTH").get_json()
    assert device["region"] == "B"
    assert device["gateway_id"] == "GW_B"
    assert device["temperature"] is None
    assert device["humidity"] is None
    assert device["battery"] is None


def test_tag_region_is_only_unknown_gateway_fallback(client):
    r = client.post(
        "/api/report",
        data=json.dumps({
            "gateway_id": "GW_UNKNOWN",
            "region": "UNKNOWN",
            "rssi": -65,
            "data": {"device_id": "TAG_FALLBACK", "region": "C", "status": "OK"},
        }),
        content_type="application/json",
    )
    assert r.status_code == 200
    device = client.get("/api/devices/TAG_FALLBACK").get_json()
    assert device["region"] == "C"


def test_devices_get_and_report_adds(client):
    r = client.get("/api/devices")
    assert r.status_code == 200
    devices_before = r.get_json()
    assert isinstance(devices_before, list)

    client.post(
        "/api/report",
        data=json.dumps({
            "gateway_id": "GW001",
            "region": "A",
            "rssi": -70,
            "data": {"device_id": "TAG_E2E", "status": "OK", "temp": 20, "humidity": 50, "battery": 3.8, "timestamp": 0},
        }),
        content_type="application/json",
    )
    r = client.get("/api/devices")
    assert r.status_code == 200
    devices = r.get_json()
    ids = [d["device_id"] for d in devices]
    assert "TAG_E2E" in ids


def test_regions(client):
    r = client.get("/api/regions")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, dict)
    assert "A" in data
    assert "B" in data


def test_locate_not_found(client):
    r = client.post(
        "/api/locate",
        data=json.dumps({"device_id": "NONEXISTENT"}),
        content_type="application/json",
    )
    assert r.status_code == 404
    data = r.get_json()
    assert data.get("status") == "error"


def test_locate_no_device_id(client):
    r = client.post("/api/locate", data=json.dumps({}), content_type="application/json")
    assert r.status_code == 400


def test_locate_found(client, monkeypatch):
    client.post(
        "/api/report",
        data=json.dumps({
            "gateway_id": "GW001",
            "region": "A",
            "rssi": -70,
            "data": {"device_id": "TAG_LOCATE", "status": "OK", "temp": 22, "humidity": 55, "battery": 3.7, "timestamp": 1},
        }),
        content_type="application/json",
    )
    calls = []

    def fake_send_play_voice(region, device_id):
        calls.append((region, device_id))
        return True, None

    monkeypatch.setattr("server.gateway_client.send_play_voice", fake_send_play_voice)
    r = client.post(
        "/api/locate",
        data=json.dumps({"device_id": "TAG_LOCATE"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("region") == "A"
    assert data.get("device_id") == "TAG_LOCATE"
    assert data.get("gateway_command_sent") is True
    assert data.get("tag_delivery_confirmed") is False
    assert "未确认标签收到或播放" in data.get("message", "")
    assert calls == [("A", "TAG_LOCATE")]
