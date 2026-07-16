/*
 * ESP32 网关 - 主程序
 * 功能：监听LoRa接收标签数据，转发到服务器，响应服务器指令
 *
 * 引脚连接：
 * LoRa: NSS=5, RST=4, DIO0=26, SCK=18, MISO=19, MOSI=23
 */

#include <WiFi.h>
#include <LoRa.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ArduinoJson.h>

#include "config.h"

// ============== LoRa引脚 ==============
#define NSS 5
#define RST 4
#define DIO0 26

// ============== HTTP服务器 ==============
WebServer server(80);

// ============== 状态LED ==============
#define LED_BUILTIN 2

void setup() {
  Serial.begin(115200);
  while (!Serial);

  // 初始化LED
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  // 连接WiFi
  connectWiFi();

  // 测试网络连接
  testNetwork();

  // 初始化LoRa
  initLoRa();

  // 初始化HTTP服务器
  initServer();

  Serial.println("Gateway setup complete!");

  // 闪灯表示就绪
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(200);
    digitalWrite(LED_BUILTIN, LOW);
    delay(200);
  }
}

void loop() {
  // 处理HTTP请求
  server.handleClient();

  // WiFi断线自动重连（避免长期断线导致不上报）
  static unsigned long lastReconnectAttempt = 0;
  if (WiFi.status() != WL_CONNECTED && millis() - lastReconnectAttempt > 10000) {
    lastReconnectAttempt = millis();
    connectWiFi();
  }

  // 监听LoRa数据
  receiveLoRa();

  delay(10);
}

// ============== WiFi连接 ==============
void connectWiFi() {
  Serial.print("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi Connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(LED_BUILTIN, HIGH);
  } else {
    Serial.println("WiFi Failed!");
  }
}

// ============== 测试网络 ==============
void testNetwork() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skip test");
    return;
  }

  HTTPClient http;
  Serial.println("Testing network to server...");

  // 先尝试GET请求
  http.begin(SERVER_URL_BASE "/api/health");
  http.setTimeout(5000);

  int httpCode = http.GET();
  Serial.print("GET /api/health: ");
  Serial.println(httpCode);

  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("Response: " + response);
  } else {
    Serial.print("Error: ");
    Serial.println(http.errorToString(httpCode).c_str());
  }

  http.end();
}

// ============== LoRa初始化 ==============
void initLoRa() {
  LoRa.setPins(NSS, RST, DIO0);

  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1);
  }

  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.setPreambleLength(8);
  LoRa.setSyncWord(0x12);

  // 设置接收模式
  LoRa.receive();

  Serial.println("LoRa init OK! 433MHz");
}

// ============== 接收LoRa数据 ==============
void receiveLoRa() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String data = "";
    while (LoRa.available()) {
      data += (char)LoRa.read();
    }

    Serial.print("LoRa received: ");
    Serial.println(data);

    // 获取信号强度
    int rssi = LoRa.packetRssi();
    Serial.print("RSSI: ");
    Serial.println(rssi);

    // 解析并转发到服务器
    forwardToServer(data, rssi);
  }
}

// ============== 转发到服务器 ==============
void forwardToServer(String payload, int rssi) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected!");
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);

  // 构建转发数据（避免字符串拼接导致的JSON格式问题）
  JsonDocument rootDoc;
  rootDoc["gateway_id"] = GATEWAY_ID;
  rootDoc["region"] = GATEWAY_REGION;
  rootDoc["rssi"] = rssi;

  // 尝试把标签上报解析成JSON对象；失败则按字符串透传（服务端会兼容解析）
  JsonDocument tagDoc;
  DeserializationError err = deserializeJson(tagDoc, payload);
  if (!err && tagDoc.is<JsonObject>()) {
    rootDoc["data"] = tagDoc.as<JsonObject>();
  } else {
    rootDoc["data"] = payload;
  }

  String forwardingData;
  serializeJson(rootDoc, forwardingData);

  int httpCode = http.POST(forwardingData);

  Serial.print("HTTP Response: ");
  Serial.println(httpCode);

  if (httpCode > 0) {
    String response = http.getString();
    Serial.println(response);
  }

  http.end();

  // 继续监听
  LoRa.receive();
}

// ============== HTTP服务器初始化 ==============
void initServer() {
  server.on("/control", HTTP_GET, handleControl);
  server.on("/status", HTTP_GET, handleStatus);
  server.begin();
  Serial.println("HTTP server started on port 80");
}

// ============== 处理控制指令 ==============
void handleControl() {
  String cmd = server.arg("cmd");
  String target = server.arg("target");

  Serial.print("Control cmd: ");
  Serial.println(cmd);

  if (cmd == "PLAY_VOICE") {
    // 发送指令给标签
    LoRa.beginPacket();
    LoRa.print("PLAY_VOICE:" + target);
    LoRa.endPacket();

    Serial.println("Sent PLAY_VOICE command to tag");

    server.send(200, "text/plain", "OK");
  } else if (cmd == "QUERY") {
    // 请求处于清醒窗口内的标签立即上报；不能唤醒深睡标签
    LoRa.beginPacket();
    LoRa.print("QUERY:" + target);
    LoRa.endPacket();

    server.send(200, "text/plain", "OK");
  } else {
    server.send(400, "text/plain", "Unknown command");
  }

  // 恢复接收模式
  LoRa.receive();
}

// ============== 处理状态查询 ==============
void handleStatus() {
  String status = "{\"gateway_id\":\"" + String(GATEWAY_ID) + "\",";
  status += "\"region\":\"" + String(GATEWAY_REGION) + "\",";
  status += "\"wifi_rssi\":" + String(WiFi.RSSI()) + ",";
  status += "\"uptime\":" + String(millis()/1000) + "}";

  server.send(200, "application/json", status);
}
