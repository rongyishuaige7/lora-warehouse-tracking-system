#pragma once

// The tag normally uses LoRa only. These placeholders are retained for the
// optional ENABLE_WIFI development path in esp32_tag.ino.
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Give every physical tag a unique ID. The region is only a local hint; the
// server records the receiving gateway's region as authoritative.
#define DEVICE_ID "TAG001"
#define DEVICE_REGION "A"
