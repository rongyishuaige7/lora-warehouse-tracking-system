#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>

void connectWiFi();
void testNetwork();
void initLoRa();
void receiveLoRa();
void forwardToServer(String payload, int rssi);
void initServer();
void handleControl();
void handleStatus();

#include "../esp32_gateway/esp32_gateway.ino"
