#include <Arduino.h>

void setupMPU6050MotionInterrupt();
void readSensors();
void goToSleep();
void initWiFi();
void initLoRa();
void receiveLoRa();
void reportStatus();
void handleDisplay();
void displayStatus();
void checkAlerts();
void playVoice();

#include "../esp32_tag/esp32_tag.ino"
