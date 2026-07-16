# Verification record

Status date: 2026-07-17

## Local candidate verification

The release candidate was tested without using the original dirty repository as a build/output target. Local real configuration files are temporary and are removed after verification.

Observed results before first publication:

```text
Repository structure / secret gates: PASS
Tag PlatformIO build: PASS
  RAM:   23,520 bytes / 327,680 bytes (7.2%)
  Flash: 339,741 bytes / 1,310,720 bytes (25.9%)
Gateway PlatformIO build: PASS
  RAM:   47,316 bytes / 327,680 bytes (14.4%)
  Flash: 964,237 bytes / 1,310,720 bytes (73.6%)
Flask pytest: 11 passed
Python py_compile: PASS
Android testDebugUnitTest + assembleDebug: PASS (40 tasks)
```

Exact sizes and task counts may change after source or dependency updates. The GitHub Actions run bound to the final public HEAD is the remote build evidence.

## Reproduce locally

Prerequisites:

- Python 3.10+;
- PlatformIO Core 6.1.19;
- JDK 17;
- Android SDK platform 34 configured through `ANDROID_HOME` or `ANDROID_SDK_ROOT`.

Run:

```bash
bash scripts/verify.sh
```

The script:

1. runs Secret scan and repository-contract checks;
2. copies example ESP32 configuration into an isolated temporary tree;
3. builds PlatformIO `tag` and `gateway` environments;
4. syntax-checks the Python server files;
5. runs all Flask tests against temporary databases;
6. runs Android JVM tests and builds the Debug APK;
7. verifies no tracked file changed.

It does not flash or operate hardware.

## What this proves

- The indexed candidate has the required documentation and safety contracts.
- Both ESP32 sources compile for the pinned `esp32dev` target.
- Server behavior covered by 11 tests works, including gateway-authoritative region and nullable sensor data.
- Android URL-policy tests and Debug build pass.
- Generated firmware and APK files can be uploaded as 14-day CI Artifacts.

## What this does not prove

- exact ESP32/SX1278 board identity;
- flash/upload, boot or reset behavior;
- radio frequency, range, antenna or regulatory compliance;
- sensor wiring or measurements;
- motion/removal wake behavior;
- DHT11 availability rate;
- deep-sleep current or battery life;
- gateway Wi-Fi/HTTP behavior on physical hardware;
- end-to-end database/App refresh;
- JQ6500 storage, audio license, speaker output or playback;
- Android physical-device compatibility;
- authentication, encryption, delivery ACK or production safety.

## End-to-end hardware re-test checklist

### Identity and setup

- [ ] Record exact Git commit, date, tester and physical unit labels.
- [ ] Confirm both ESP32 board models, flash size and USB/UART interface.
- [ ] Confirm both SX1278 module models, 433 MHz marking, antenna and wiring.
- [ ] Confirm tag MPU6050, Hall, DHT11, OLED, JQ6500 and speaker modules.
- [ ] Confirm tag power, charging/protection/regulator path and common ground.
- [ ] Confirm JQ6500 audio file source is legally publishable or keep it excluded.

### Firmware and sensors

- [ ] Build and flash the exact commit to tag and gateway.
- [ ] Confirm serial startup without reset loops.
- [ ] Confirm DHT values or `null` behavior without false zero.
- [ ] Confirm motion and Hall state transitions.
- [ ] Confirm GPIO33/GPIO13/timer wake and measure deep-sleep current.
- [ ] Confirm `QUERY` works only in the awake window and cannot wake deep sleep.

### Radio, service and App

- [ ] Observe tag LoRa report at the gateway and record RSSI.
- [ ] Observe gateway HTTP report and SQLite device/history rows.
- [ ] Confirm receiving gateway region overrides a conflicting tag hint.
- [ ] Test two gateways and stronger-RSSI selection under a controlled layout.
- [ ] Open the Android App on a real device, configure the trusted-LAN server, refresh and search.
- [ ] Confirm lists and A/B counts update from the same report.
- [ ] Tap Locate while tag is awake; confirm gateway dispatch and actual JQ6500 playback separately.
- [ ] Tap Locate while tag sleeps; confirm the App does not falsely report delivery/playback.
- [ ] Capture redacted logs, screenshots, photos and a 20–60 second demo.

Only after the applicable checklist passes may `PROJECT_STATUS.md` say `Hardware re-verified` and name the exact tested commit/date.
