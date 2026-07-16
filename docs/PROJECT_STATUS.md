# Project status

Status date: 2026-07-17

## Evidence levels

| Level | Status | Meaning |
|---|---|---|
| Source-confirmed | PASS | Desktop source was selected as the latest candidate and compared with the historical ZIP baseline |
| Tag firmware build-verified | PASS | PlatformIO `tag` environment builds from example configuration |
| Gateway firmware build-verified | PASS | PlatformIO `gateway` environment builds from example configuration |
| Server tests | PASS | Flask server has 11 passing pytest tests |
| Android build-verified | PASS | JVM unit tests and Debug APK assembly pass |
| Historically demonstrated | UNKNOWN | No public-ready photo, screenshot or video was found in the reviewed source/archive |
| Hardware re-verified | NOT RUN | The candidate commit has not been flashed and tested end to end on the physical prototype |
| EDA/manufacturing available | NO | No schematic, PCB, Gerber, enclosure or manufacturing source was found |

## What is confirmed

- Source contains an ESP32 tag, ESP32 LoRa/Wi-Fi gateway, Flask/SQLite server and Kotlin Android app.
- Both firmware targets build with the pinned `espressif32@6.13.0` PlatformIO environment.
- The server stores the **receiving gateway region** as authoritative, with tag region only as an unknown-gateway fallback.
- Multi-gateway reports received within three seconds retain the stronger RSSI observation.
- Battery measurement is not implemented and now reports `null`; failed DHT reads also report `null` rather than a fabricated zero.
- `/api/locate` no longer blocks for a false QUERY wake flow and does not claim the tag received or played audio.
- Android uses `minSdk 23`, defaults to emulator host `10.0.2.2`, and restricts cleartext HTTP URLs to loopback/emulator/RFC1918 hosts.
- Real Wi-Fi and LAN configuration is absent from the release candidate.

## Source-level corrections made for publication

### Location authority

Historical code preferred the tag's self-declared region. The public candidate follows the product mechanism: the receiving gateway region is authoritative. This is verified by an automated server test, not by current radio-range hardware testing.

### Deep-sleep command semantics

Historical documentation claimed `QUERY` could wake a sleeping tag. Current firmware only enables timer, GPIO33 and GPIO13 wake sources; LoRa DIO0 is not included. The candidate now states that `QUERY` requests a report only while a tag is already awake.

### Sensor unavailable semantics

Historical firmware reported a fixed 3.7 V battery value and converted DHT failures to zero. The candidate reports JSON `null` and displays `N/A`. This is a truthfulness fix; no battery sensing circuit was added.

### Configuration and transport boundary

Historical private LAN addresses were removed. Flask browser CORS is disabled by default. The Android client accepts public hosts only over HTTPS and limits HTTP to local/private hosts. None of these changes adds API or LoRa authentication.

## Known limitations

- Current end-to-end hardware re-test not run.
- No photos, video, App screenshots, EDA or manufacturing sources.
- No API authentication, gateway-control authentication, TLS, LoRa encryption or replay protection.
- `/api/locate` only confirms HTTP dispatch to a configured gateway; tag delivery/playback is unconfirmed.
- Deep-sleep tags cannot receive LoRa commands until another configured wake source activates them.
- Battery sensing, charging circuit, deep-sleep current and power budget are unknown.
- DHT11 is slow and can return unavailable data; `null` must remain distinct from a real zero.
- Android A/B cards are static even though the backend can store other region strings.
- `esp32dev` is a reproducible build target, not a confirmed physical board identity.
- 433 MHz regulatory compliance, actual module frequency and antenna match are not verified.
- Python dependency ranges and Android Maven dependencies are not a complete offline lockfile.

## Status wording rule

Until current physical evidence is added, public descriptions must use:

```text
Source-confirmed · Tag firmware build-verified · Gateway firmware build-verified · Server tests passed · Android unit test and debug build passed · Current end-to-end hardware re-test not run
```

Do not use “hardware verified”, “production ready”, “industrial grade”, “secure tracking”, “accurate positioning” or an online-status badge.
