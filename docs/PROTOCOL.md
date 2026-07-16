# Protocol and API

## Trust boundary

All current transports are prototype-grade:

- tag ↔ gateway: plaintext LoRa, no authentication/encryption/replay protection;
- gateway ↔ Flask: plaintext HTTP on a trusted LAN;
- Flask API: no authentication/authorization;
- Android: HTTPS accepted; HTTP limited in app logic to loopback/emulator/RFC1918 hosts.

Do not expose the gateway or Flask service directly to the public internet.

## LoRa configuration

Both endpoints currently use:

```text
frequency: 433 MHz
spreading factor: 7
bandwidth: 125 kHz
coding rate: 4/5
preamble: 8
sync word: 0x12
```

Actual module band and legal operation still require physical and regional confirmation.

## Tag report

Example with valid DHT data:

```json
{"device_id":"TAG001","region":"A","status":"OK","temp":25.4,"humidity":60.0,"battery":null,"timestamp":12}
```

Example when DHT is unavailable:

```json
{"device_id":"TAG001","region":"A","status":"OK","temp":null,"humidity":null,"battery":null,"timestamp":12}
```

Fields:

| Field | Meaning |
|---|---|
| `device_id` | tag identifier configured locally |
| `region` | tag-local hint, not authoritative when gateway region is known |
| `status` | `OK`, `MOVING` or `REMOVED` in current firmware |
| `temp` / `humidity` | DHT11 values or JSON `null` |
| `battery` | always `null` until real ADC hardware/firmware is implemented |
| `timestamp` | tag uptime seconds, not wall-clock time |

The server uses its own receive time for `last_update`.

## LoRa commands

```text
PLAY_VOICE:<device_id>
QUERY:<device_id>
```

An empty target or `*` is broadcast. `QUERY` asks a tag that is already awake to report immediately. Neither command can wake the current deep-sleep implementation. There is no tag ACK, so transmission is not proof of execution.

## Gateway HTTP

### Gateway to Flask

`POST /api/report`:

```json
{
  "gateway_id": "GW001",
  "region": "A",
  "rssi": -67,
  "data": {
    "device_id": "TAG001",
    "region": "B",
    "status": "OK",
    "temp": 25.4,
    "humidity": 60.0,
    "battery": null,
    "timestamp": 12
  }
}
```

The server records gateway region `A` as authoritative. `data` may also be a JSON string; a `tags` array is accepted for compatibility.

### Flask to gateway

```text
GET /control?cmd=PLAY_VOICE&target=TAG001
GET /control?cmd=QUERY&target=TAG001
GET /status
```

Gateway HTTP 200 means it accepted and transmitted a command. It does not prove tag receipt or playback.

## Flask API

| Method | Route | Notes |
|---|---|---|
| `POST` | `/api/report` | gateway report; `device_id` required |
| `GET` | `/api/devices` | all devices ordered by server receive time |
| `GET` | `/api/devices/<device_id>` | one device or 404 |
| `GET` | `/api/search?q=` | SQL parameterized substring search |
| `GET` | `/api/regions` | counts by region; ensures A/B keys for current App |
| `POST` | `/api/locate` | recent region plus gateway dispatch result |
| `GET` | `/api/history/<device_id>?limit=50` | 1–500 rows |
| `GET` | `/api/health` | Flask/config self-report only |

Locate response example:

```json
{
  "region": "A",
  "device_id": "TAG001",
  "message": "最近一次上报位于区域A；语音指令已下发到网关，但未确认标签收到或播放。若标签正在深睡，请在下一次心跳后重试。",
  "gateway_command_sent": true,
  "gateway_error": null,
  "tag_delivery_confirmed": false,
  "last_report_age_seconds": 8
}
```

`last_report_age_seconds` is derived from server receive time. `/api/health` returning `status=ok` is not evidence that any gateway or tag is online.
