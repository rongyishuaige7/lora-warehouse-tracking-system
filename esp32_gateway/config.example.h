#pragma once

#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Replace the documentation-only address with the Flask host on your trusted
// LAN. Do not expose this unauthenticated prototype directly to the internet.
#define SERVER_URL_BASE "http://192.0.2.10:5000"
#define SERVER_URL (SERVER_URL_BASE "/api/report")

#define GATEWAY_ID "GW001"
#define GATEWAY_REGION "A"
