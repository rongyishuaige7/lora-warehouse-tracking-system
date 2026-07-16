# Third-party notices

The repository's own source files are released under the MIT License in
[`LICENSE`](LICENSE). Third-party build tools, frameworks and libraries keep
their own licenses. Most are downloaded during build; this repository does not
relicense or redistribute their source.

## ESP32 firmware

| Dependency | Pinned version | Upstream | License declared upstream |
|---|---|---|---|
| PlatformIO Core | 6.1.19 | <https://github.com/platformio/platformio-core> | Apache-2.0 |
| PlatformIO Espressif 32 | 6.13.0 | <https://github.com/platformio/platform-espressif32> | Apache-2.0 |
| Arduino-ESP32 | resolved 2.0.17 package | <https://github.com/espressif/arduino-esp32> | LGPL-2.1 |
| LoRa | 0.8.0 | <https://github.com/sandeepmistry/arduino-LoRa> | MIT |
| DHT sensor library | 1.4.6 | <https://github.com/adafruit/DHT-sensor-library> | MIT |
| MPU6050 | 1.4.4 | <https://github.com/ElectronicCats/mpu6050> | MIT |
| Adafruit SSD1306 | 2.5.16 | <https://github.com/adafruit/Adafruit_SSD1306> | BSD-3-Clause |
| Adafruit GFX | 1.12.5 | <https://github.com/adafruit/Adafruit-GFX-Library> | BSD-3-Clause |
| Adafruit BusIO | 1.17.4 | <https://github.com/adafruit/Adafruit_BusIO> | MIT |
| ArduinoJson | 7.4.3 | <https://github.com/bblanchon/ArduinoJson> | MIT |
| JQ6500_Serial | commit `7a5f53f54a9e66579582e12d1d0495572220e877` | <https://github.com/sleemanj/JQ6500_Serial> | LGPL-3.0 |

`JQ6500_Serial` is pinned to a Git commit because the PlatformIO Registry
package did not expose the HardwareSerial constructor used by this source.
Generated firmware binaries can include or link third-party components; comply
with all applicable licenses when redistributing binaries.

## Flask server

Declared ranges:

- Flask `>=3.0,<4.0` — BSD-3-Clause;
- Flask-Cors `>=4.0,<6.0` — MIT;
- Requests `>=2.31,<3.0` — Apache-2.0;
- pytest `>=7.0,<9` for development — MIT.

These Python dependencies are range-bounded rather than fully locked. Record
resolved versions if publishing a reproducible deployment image.

## Android app

The Gradle build downloads Android Gradle Plugin 8.2.2, Kotlin Gradle Plugin
1.9.22, AndroidX, Material Components, Retrofit 2.9.0, OkHttp 4.12.0, Gson
converter and Kotlin Coroutines. See [`android_app/app/build.gradle`](android_app/app/build.gradle)
for exact declarations and each upstream project for its license. The checked-in
Gradle Wrapper JAR and wrapper scripts are distributed under Apache-2.0; the
Gradle 8.2 distribution is downloaded separately and SHA-256 pinned.

## Hardware, trademarks and media

ESP32, SX1278, MPU6050, JQ6500, Android and other names identify compatible
components; no endorsement is implied. No third-party datasheet, logo, audio
file, font, EDA file, Android SDK, compiler, framework source or firmware binary
is intentionally redistributed here.
