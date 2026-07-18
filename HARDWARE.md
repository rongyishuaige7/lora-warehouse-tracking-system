# Hardware and wiring notes

本文件按当前可构建源码记录接线边界，不是电气审查后的 PCB 原理图。

## 1. 标签端引脚

| 模块/信号 | ESP32 引脚 | 当前源码语义 |
|---|---:|---|
| SX1278 NSS / RST / DIO0 | GPIO5 / GPIO4 / GPIO26 | SPI 默认 SCK18、MISO19、MOSI23；433 MHz |
| I²C SDA / SCL | GPIO21 / GPIO22 | MPU6050 与 SSD1306 共用 |
| MPU6050 INT | GPIO33 | EXT1 深睡唤醒 |
| 霍尔传感器 | GPIO13 | EXT1 深睡唤醒；源码按 HIGH=移除 |
| DHT11 DATA | GPIO15 | 温湿度；失败报告 `null` |
| JQ6500 RX / TX | GPIO16 / GPIO17 | ESP32 UART2；GPIO16 接模块 TX，GPIO17 接模块 RX |
| OLED | I²C `0x3C` | 128×64 SSD1306 |
| 板载 LED | GPIO2 | 状态输出 |

标签本地 `DEVICE_REGION` 只是提示，服务端以接收网关区域为权威。

## 2. 网关端引脚

| 模块/信号 | ESP32 引脚 | 当前源码语义 |
|---|---:|---|
| SX1278 NSS / RST / DIO0 | GPIO5 / GPIO4 / GPIO26 | SPI 默认 SCK18、MISO19、MOSI23；433 MHz |
| 板载 LED | GPIO2 | Wi-Fi/启动状态 |
| Wi-Fi | 板载射频 | 把 LoRa 数据通过 HTTP 转发给 Flask |

## 3. 电源与无线边界

- 不能仅凭源码确定实际 ESP32 开发板、SX1278 模块稳压方式或连接器；
- SX1278 和 ESP32 逻辑通常为 3.3 V，禁止把未知 5 V 信号直接送入 GPIO；
- 标签端所有模块必须共地，并为 JQ6500、OLED、传感器和无线发射预留足够的供电裕量；
- JQ6500 音频输出、扬声器阻抗与供电方式须按实际模块手册核对；
- 当前没有电池电压分压/ADC 采样实现，因此 BOM 中的电池、电源管理与充电链路都标为待确认；
- 433 MHz 只是源码配置。实际 SX1278 模块频段、天线匹配、发射功率与当地合规要求必须逐项确认；
- 不要在没有匹配天线的情况下长时间发射。

## 4. 深睡和查找限制

标签深睡唤醒源是 GPIO33、GPIO13 和定时器。LoRa DIO0（GPIO26）没有进入深睡唤醒掩码，因此网关发出的 `QUERY` 或 `PLAY_VOICE` 不能唤醒已经深睡的标签。它们只可能在标签约 10 秒清醒窗口内被接收。

## 5. BOM 证据层级

[`hardware/BOM.csv`](hardware/BOM.csv) 使用：

- `source-confirmed`：源码直接引用；
- `document-confirmed`：既有文档/配置明确出现，但无当前实物确认；
- `hardware-pending`：需要照片、铭牌、原理图或实测确认。

## 6. 当前未提供

- 实物照片和 App 截图；
- 演示视频；
- 原理图、PCB Layout、Gerber；
- 电源/充电原理与深睡电流；
- JQ6500 音频文件及来源；
- 当前提交的烧录和端到端真机记录。

因此本仓库不会使用“硬件已验证”“定位准确”“低功耗已验证”或“系统在线”等表述。
