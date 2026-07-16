/*
 * ESP32 仓库标签 - 主程序
 * 功能：运动检测、霍尔传感器、温湿度监测、OLED显示、语音播放、LoRa通信
 *
 * 引脚连接：
 * LoRa: NSS=5, RST=4, DIO0=26, SCK=18, MISO=19, MOSI=23
 * I2C: SDA=21, SCL=22
 * 霍尔传感器: GPIO13 (RTC唤醒源)
 * MPU6050 INT: GPIO33 (RTC唤醒源)
 * DHT11: GPIO15
 * JQ6500: RX=16, TX=17
 */

// 标签端一般不需要WiFi（只用LoRa即可）；如需WiFi调试/扩展功能，将其置为1
#define ENABLE_WIFI 0
#if ENABLE_WIFI
#include <WiFi.h>
#endif
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <MPU6050.h>
#include <DHT.h>
#include <JQ6500_Serial.h>
#include <driver/rtc_io.h>

// JQ6500 语音模块 (硬件串口 UART2)
#define JQ6500_RX 16  // ESP32 GPIO16 接 JQ6500 TX
#define JQ6500_TX 17  // ESP32 GPIO17 接 JQ6500 RX
HardwareSerial jqSerial(2);
JQ6500_Serial mp3(jqSerial);

#define REPORT_INTERVAL_MS 30000
#define MOTION_THRESHOLD 20000

#include "config.h"

// ============== LoRa引脚 ==============
#define NSS 5
#define RST 4
#define DIO0 26

// ============== 传感器引脚 ==============
#define HALL_SENSOR GPIO_NUM_13
#define MPU_INT_PIN GPIO_NUM_33
#define DHT_PIN 15

// ============== OLED配置 ==============
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ============== 传感器对象 ==============
MPU6050 mpu;
DHT dht(DHT_PIN, DHT11);


// ============== 状态变量 ==============
RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR String statusStr = "OK";
// No battery ADC divider is implemented in this prototype. Keep the public
// protocol honest by reporting null instead of a fabricated voltage.
float temperature = NAN;
float humidity = NAN;
bool isMoving = false;
bool isRemoved = false;

// OLED 电源管理
unsigned long startWakeTime = 0;
const unsigned long WAKE_TIME_MS = 10000;  // 每次唤醒保持清醒10秒，监听潜在指令
// LoRa DIO0 (GPIO26) is intentionally not a deep-sleep wake source.
bool isOledOn = true;
unsigned long lastInteractionTime = 0;
unsigned long lastDisplayRefresh = 0;      // 节流：避免每 10ms 重绘
#define OLED_TIMEOUT 5000
#define OLED_REFRESH_INTERVAL_MS 500       // 亮屏时最多每 500ms 刷新一次


// ============== WiFi状态LED ==============
#define LED_BUILTIN 2

void setup() {
  Serial.begin(115200);
  bootCount++;
  startWakeTime = millis();
  lastInteractionTime = millis();


  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(HALL_SENSOR, INPUT_PULLUP);
  pinMode(MPU_INT_PIN, INPUT_PULLUP);

  Wire.begin(21, 22);

  // 判断唤醒原因（提前读取，用于决定是否完整初始化 MPU）
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  Serial.printf("Wakeup reason: %d\n", wakeup_reason);

  // 初始化 JQ6500 语音模块（硬件串口，复位->选Flash->设音量）
  jqSerial.begin(9600, SERIAL_8N1, JQ6500_RX, JQ6500_TX);
  mp3.reset();
  delay(3000);
  mp3.setSource(MP3_SRC_BUILTIN);
  delay(500);
  mp3.setVolume(20);
  if (bootCount == 1) {
    mp3.playFileByIndexNumber(1);
    delay(100);
  }

  // 初始化传感器（仅首次上电时完整初始化 MPU，避免覆盖 Cycle/中断配置）
  dht.begin();
  if (wakeup_reason == ESP_SLEEP_WAKEUP_UNDEFINED) {
    mpu.initialize();
  }
  setupMPU6050MotionInterrupt();

  // 初始化LoRa
  initLoRa();

  // 读取传感器并确定当前状态
  readSensors();
  checkAlerts();

  // 如果是因为运动或拆卸唤醒，立即上报
  // 霍尔传感器和MPU中断现在都走 EXT1（均已合并到同一 wakeupMask）
  if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT1) {
    uint64_t wakeupPins = esp_sleep_get_ext1_wakeup_status();
    if (wakeupPins & (1ULL << HALL_SENSOR)) {
      Serial.println("Hall Sensor Wakeup! (REMOVED)");
    } else if (wakeupPins & (1ULL << MPU_INT_PIN)) {
      Serial.println("MPU Motion Wakeup!");
    } else {
      Serial.println("External Triggered Wakeup!");
    }
    reportStatus();
  } else if (wakeup_reason == ESP_SLEEP_WAKEUP_TIMER) {
    Serial.println("Timer Heartbeat Wakeup!");
    reportStatus();
  } else {
    // 首次启动上报
    reportStatus();
  }

  // 初始化显示（用于指令响应）
  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    displayStatus();
  }

  lastInteractionTime = millis();

  Serial.println("Setup complete, listening for commands...");
}

void loop() {
  // 保持清醒一段时间监听LoRa指令（如PLAY_VOICE）
  receiveLoRa();

  // DHT11 周期读取（约 2s 间隔，避免过于频繁）
  {
    static unsigned long lastDhtRead = 0;
    if (millis() - lastDhtRead >= 2000) {
      lastDhtRead = millis();
      float t = dht.readTemperature();
      float h = dht.readHumidity();
      if (!isnan(t) && !isnan(h)) {
        temperature = t;
        humidity = h;
      }
    }
  }

  // 运动检测：硬件中断 + 软件加速度变化量，任一触发都视为运动
  {
    static unsigned long lastMotionTime = 0;
    const unsigned long MOTION_HOLD_MS = 3000;  // 停止晃动后保持 MOVING 状态3秒
    bool motionDetected = false;

    // 硬件中断检测
    if (digitalRead(MPU_INT_PIN) == HIGH) {
      motionDetected = true;
      Wire.beginTransmission(0x68);
      Wire.write(0x3A);
      Wire.endTransmission(false);
      Wire.requestFrom((uint16_t)0x68, (uint8_t)1, (uint8_t)1);
      if (Wire.available()) Wire.read();
    }

    // 软件加速度变化量检测
    {
      static int16_t _pAx = 0, _pAy = 0, _pAz = 0;
      static bool _swInitDone = false;
      int16_t ax, ay, az;
      mpu.getAcceleration(&ax, &ay, &az);
      if (_swInitDone) {
        int32_t delta = abs((int32_t)ax - _pAx) + abs((int32_t)ay - _pAy) + abs((int32_t)az - _pAz);
        if (delta > 2000) {
          motionDetected = true;
        }
      }
      _pAx = ax; _pAy = ay; _pAz = az;
      _swInitDone = true;
    }

    if (motionDetected) {
      lastMotionTime = millis();
      lastInteractionTime = millis();
    }

    bool wasMoving = isMoving;
    isMoving = (millis() - lastMotionTime < MOTION_HOLD_MS) && (lastMotionTime > 0);

    if (isMoving != wasMoving) {
      Serial.println(isMoving ? "Motion started" : "Motion stopped");
      checkAlerts();
      if (isMoving) {
        reportStatus();
      }
    }
  }

  // 霍尔传感器轮询：状态变化时更新 isRemoved、checkAlerts、唤醒 OLED、串口日志
  {
    bool curRemoved = (digitalRead(HALL_SENSOR) == HIGH);
    if (curRemoved != isRemoved) {
      isRemoved = curRemoved;
      Serial.println(isRemoved ? "Hall: REMOVED" : "Hall: IN PLACE");
      checkAlerts();
      lastInteractionTime = millis();
      startWakeTime = millis();
      reportStatus();
    }
  }

  if (millis() - startWakeTime > WAKE_TIME_MS && statusStr == "OK") {
    goToSleep();
  }

  handleDisplay();

  delay(10);
}

void goToSleep() {
  Serial.println("Entering Deep Sleep...");

  display.ssd1306_command(SSD1306_DISPLAYOFF);

  // 入睡前读清 MPU6050 INT_STATUS 锁存，防止 GPIO33 仍为 HIGH 导致立即唤醒
  Wire.beginTransmission(0x68);
  Wire.write(0x3A);
  Wire.endTransmission(false);
  Wire.requestFrom((uint16_t)0x68, (uint8_t)1, (uint8_t)1);
  if (Wire.available()) Wire.read();

  // 等待引脚电平稳定，避免总线操作结束时的毛刺误触发
  delay(50);

  // 检查霍尔传感器：若磁铁已离开（HIGH），不进入深睡，留在 loop 处理告警
  if (digitalRead(HALL_SENSOR) == HIGH) {
    Serial.println("Hall still REMOVED, skip sleep.");
    lastInteractionTime = millis();
    startWakeTime = millis();
    return;
  }

  // 检查 MPU INT 引脚：若仍为 HIGH（锁存未清），不进入深睡，下一轮 loop 会再次清除
  if (digitalRead(MPU_INT_PIN) == HIGH) {
    Serial.println("MPU INT still HIGH, skip sleep.");
    lastInteractionTime = millis();
    startWakeTime = millis();
    return;
  }

  // RTC GPIO 上拉：深睡期间保持有效，霍尔/MPU INT 为开漏输出，需上拉才能拉到 HIGH 触发 EXT1
  rtc_gpio_init(HALL_SENSOR);
  rtc_gpio_set_direction(HALL_SENSOR, RTC_GPIO_MODE_INPUT_ONLY);
  rtc_gpio_pulldown_dis(HALL_SENSOR);
  rtc_gpio_pullup_en(HALL_SENSOR);

  rtc_gpio_init(MPU_INT_PIN);
  rtc_gpio_set_direction(MPU_INT_PIN, RTC_GPIO_MODE_INPUT_ONLY);
  rtc_gpio_pulldown_dis(MPU_INT_PIN);
  rtc_gpio_pullup_en(MPU_INT_PIN);

  // EXT1 同时监听霍尔传感器(GPIO13)和MPU中断(GPIO33)，任意引脚 HIGH 时唤醒
  uint64_t wakeupMask = (1ULL << MPU_INT_PIN) | (1ULL << HALL_SENSOR);
  esp_sleep_enable_ext1_wakeup(wakeupMask, ESP_EXT1_WAKEUP_ANY_HIGH);

  // 心跳包定时唤醒
  esp_sleep_enable_timer_wakeup((uint64_t)REPORT_INTERVAL_MS * 1000);

  Serial.flush();
  esp_deep_sleep_start();
}

void setupMPU6050MotionInterrupt() {
  // 设置 MPU6050 进入低功耗运动监测模式
  Wire.beginTransmission(0x68);
  Wire.write(0x1C); // ACCEL_CONFIG
  Wire.write(0x04); // ACCEL_HPF = 0.63Hz，允许 >0.63Hz 的运动信号通过
  Wire.endTransmission();

  Wire.beginTransmission(0x68);
  Wire.write(0x1F); // MOT_THR (阈值)
  Wire.write(20);   // 设置灵敏度，越小越灵敏
  Wire.endTransmission();

  Wire.beginTransmission(0x68);
  Wire.write(0x20); // MOT_DUR (持续时间)
  Wire.write(1);    // 1ms
  Wire.endTransmission();

  Wire.beginTransmission(0x68);
  Wire.write(0x37); // INT_PIN_CFG
  Wire.write(0x20); // LATCH_INT_EN=1：INT保持HIGH直到读取INT_STATUS才清零
  Wire.endTransmission();

  Wire.beginTransmission(0x68);
  Wire.write(0x38); // INT_ENABLE
  Wire.write(0x40); // 开启运动中断
  Wire.endTransmission();

  // 加速度计上电延迟 + 使能运动检测
  Wire.beginTransmission(0x68);
  Wire.write(0x69); // MOT_DETECT_CTRL
  Wire.write(0x15); // ACCEL_ON_DELAY=1（4ms）+ MOT_COUNT=1
  Wire.endTransmission();

  // 关闭陀螺仪，节省功耗
  Wire.beginTransmission(0x68);
  Wire.write(0x6C); // PWR_MGMT_2
  Wire.write(0xC7); // STBY_XG=STBY_YG=STBY_ZG=1，加速度计保持工作
  Wire.endTransmission();

  // 进入 Cycle 低功耗模式（约5Hz采样率）
  Wire.beginTransmission(0x68);
  Wire.write(0x6B); // PWR_MGMT_1
  Wire.write(0x20); // CYCLE=1，SLEEP=0，TEMP_DIS=0
  Wire.endTransmission();
}

// ============== WiFi连接 ==============
#if ENABLE_WIFI
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
#endif

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

  Serial.println("LoRa init OK! 433MHz");

  // 进入持续接收模式，否则后续LoRa.parsePacket()不会收到数据
  LoRa.receive();
}

// ============== 读取传感器 ==============
void readSensors() {
  // 读取温湿度
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    temperature = NAN;
    humidity = NAN;
  }

  // 判断是否移除 (霍尔)：霍尔传感器和MPU中断现在都走 EXT1
  // 通过 GPIO 实际电平判断：HIGH = 磁铁离开（拆卸/告警），LOW = 磁铁在位（正常）
  esp_sleep_wakeup_cause_t wakeup = esp_sleep_get_wakeup_cause();
  uint64_t ext1Pins = (wakeup == ESP_SLEEP_WAKEUP_EXT1) ? esp_sleep_get_ext1_wakeup_status() : 0;
  isMoving = (wakeup == ESP_SLEEP_WAKEUP_EXT1) && (ext1Pins & (1ULL << MPU_INT_PIN));
  isRemoved = (digitalRead(HALL_SENSOR) == HIGH) ||
              ((wakeup == ESP_SLEEP_WAKEUP_EXT1) && (ext1Pins & (1ULL << HALL_SENSOR)));
}

// ============== 检测异常 ==============
void checkAlerts() {
  // 逻辑已在 readSensors 中处理核心状态，此处主要更新状态字符串
  if (isRemoved) {
    statusStr = "REMOVED";
  } else if (isMoving) {
    statusStr = "MOVING";
    startWakeTime = millis(); // 运动中重置清醒时间
  } else {
    statusStr = "OK";
  }
}

// ============== 接收LoRa指令 ==============
void receiveLoRa() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String cmd = "";
    while (LoRa.available()) {
      cmd += (char)LoRa.read();
    }

    Serial.print("LoRa received: ");
    Serial.println(cmd);

    // 指令格式：PLAY_VOICE:<device_id> / QUERY:<device_id>
    // QUERY only requests an immediate report while this tag is awake. LoRa
    // is not a configured ESP32 deep-sleep wake source in this prototype.
    // - device_id为空或为"*"表示广播
    int sepIndex = cmd.indexOf(':');
    String action = cmd;
    String target = "";
    if (sepIndex >= 0) {
      action = cmd.substring(0, sepIndex);
      target = cmd.substring(sepIndex + 1);
    }
    action.trim();
    target.trim();

    const String myId(DEVICE_ID);
    const bool targetedToMe = target.isEmpty() || target == "*" || target.equalsIgnoreCase(myId);
    if (!targetedToMe) {
      Serial.println("Command ignored (not my target).");
      LoRa.receive();
      return;
    }

    if (action == "PLAY_VOICE") {
      playVoice();
    } else if (action == "QUERY") {
      reportStatus();
      startWakeTime = millis();   // 重置清醒计时，给服务器发 PLAY_VOICE 的时间
      lastInteractionTime = millis();
    } else {
      Serial.println("Unknown command.");
    }

    // parsePacket()会把芯片置为standby，需要恢复接收
    LoRa.receive();
  }
}

// ============== 播放语音 ==============
void playVoice() {
  Serial.println("Playing voice...");
  mp3.playFileByIndexNumber(1);  // 播放第1首MP3
  delay(100);
}

// ============== 上报状态 ==============
void reportStatus() {
  // 构建JSON数据
  String data = "{\"device_id\":\"" + String(DEVICE_ID) + "\",";
  data += "\"region\":\"" + String(DEVICE_REGION) + "\",";
  data += "\"status\":\"" + statusStr + "\",";
  data += "\"temp\":";
  data += isnan(temperature) ? "null," : String(temperature) + ",";
  data += "\"humidity\":";
  data += isnan(humidity) ? "null," : String(humidity) + ",";
  data += "\"battery\":null,";
  data += "\"timestamp\":" + String(millis()/1000) + "}";

  // 通过LoRa发送
  LoRa.beginPacket();
  LoRa.print(data);
  LoRa.endPacket();

  Serial.println("Status reported via LoRa: " + data);

  // 发送完成后回到接收模式，避免错过网关下发指令
  LoRa.receive();
}

// ============== OLED电源与显示管理 ==============
void handleDisplay() {
  // 运动或 REMOVED 告警时刷新熄屏计时，保持 OLED 常亮以便查看
  if (isMoving || isRemoved) {
    lastInteractionTime = millis();
  }

  // 检查超时逻辑
  if (millis() - lastInteractionTime > OLED_TIMEOUT) {
    if (isOledOn) {
      display.ssd1306_command(SSD1306_DISPLAYOFF);
      isOledOn = false;
      Serial.println("OLED entered sleep mode.");
    }
  } else {
    if (!isOledOn) {
      display.ssd1306_command(SSD1306_DISPLAYON);
      isOledOn = true;
      Serial.println("OLED wakeup.");
    }
  }

  if (isOledOn) {
    if (millis() - lastDisplayRefresh >= OLED_REFRESH_INTERVAL_MS) {
      lastDisplayRefresh = millis();
      displayStatus();
    }
  }
}

void displayStatus() {
  display.clearDisplay();

  // 标题
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print("ID: ");
  display.println(DEVICE_ID);

  // 区域
  display.print("Region: ");
  display.println(DEVICE_REGION);

  // 状态
  display.print("Status: ");
  if (statusStr != "OK") {
    // 异常状态反色显示（提醒）
    display.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
  }
  display.println(statusStr);
  display.setTextColor(SSD1306_WHITE);

  // 温湿度
  display.print("Temp: ");
  if (isnan(temperature)) {
    display.println("N/A");
  } else {
    display.print(temperature);
    display.println("C");
  }

  display.print("Humi: ");
  if (isnan(humidity)) {
    display.println("N/A");
  } else {
    display.print(humidity);
    display.println("%");
  }

  // 电池
  display.println("Battery: N/A");

  display.display();
}
