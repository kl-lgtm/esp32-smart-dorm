# 基于 ESP32 与 AIoT 的智能宿舍感知与安防系统

基于 ESP32、MicroPython 与 Coze AI 智能体的智能宿舍综合控制系统，覆盖环境感知、自动照明、自适应窗帘、AI 场景控制、安防报警、矩阵键盘认证、OLED 状态显示与局域网 Web 监控。架构上由 ESP32 完成传感器采集与硬件控制，电脑端 Python 桥接程序调用 Coze 解析自然语言意图并转为标准场景指令，经 WiFi/HTTP 下发执行，实现 AUTO、SLEEP、SECURITY、ALERT 多模式联动。

## 功能

- 光照、人体活动、温度实时采集
- OLED 实时状态显示
- AUTO 自动照明
- 基于人体、温度和光照的自适应窗帘
- Coze AI 自然语言场景控制
- SLEEP 睡眠模式
- SECURITY 安防模式
- ALERT 入侵报警模式
- RGB 灯与蜂鸣器报警
- 矩阵键盘密码认证
- WiFi / HTTP 通信
- Web 状态查看与基础模式控制

## 系统架构

```text
用户自然语言
    ↓
Coze AI 智能体
    ↓
标准场景指令
    ↓
电脑端 Python 桥接程序
    ↓
WiFi / HTTP
    ↓
ESP32
    ├─ 光敏传感器
    ├─ PIR 人体红外
    ├─ DS18B20
    ├─ OLED
    ├─ RGB 灯
    ├─ 舵机
    ├─ 蜂鸣器
    └─ 矩阵键盘
```

ESP32 负责传感器采集、状态判断和硬件控制；电脑端 Python 程序负责调用 Coze、解析自然语言意图并向 ESP32 发送标准场景命令。

## 运行模式

| 模式         | 功能                                   |
| ------------ | -------------------------------------- |
| `AUTO`     | 自动照明、环境感知、自适应窗帘         |
| `SLEEP`    | 关闭照明、关闭窗帘，不触发安防报警     |
| `SECURITY` | 进入安防状态，等待异常人体活动         |
| `ALERT`    | 红灯闪烁、蜂鸣器报警，等待密码认证解除 |

AI 标准指令：

```text
AUTO_MODE
SCENE_SLEEP
SCENE_SECURITY
```

示例：

```text
“我要休息了”   → SLEEP
“我睡醒了”     → AUTO
“我要去上课了” → SECURITY
```

## 硬件连接

| 模块             | GPIO / 接口        |
| ---------------- | ------------------ |
| 光敏传感器 AO    | D34                |
| PIR 人体红外 OUT | D27                |
| DS18B20 DQ       | D25                |
| RGB R            | D4                 |
| RGB G            | D16                |
| RGB B            | D17                |
| 有源蜂鸣器 IO    | D13                |
| 舵机信号         | D19                |
| OLED SDA         | D21                |
| OLED SCL         | D22                |
| 键盘 Row 1~4     | D2、D5、D18、D23   |
| 键盘 Col 1~4     | D14、D26、D33、D32 |

矩阵键盘：

```text
密码：1234
A：确认
B：清空
```

## 软件环境

### ESP32 端

- ESP32-WROOM-32
- MicroPython
- Thonny
- `ssd1306.py`
- `onewire`
- `ds18x20`

### PC 端

- Python 3
- `requests`
- Coze AI 智能体

安装依赖：

```bash
pip install requests
```

## 项目结构

```text
smart-dorm-esp32-aiot/
├─ README.md
├─ .gitignore
├─ dorm_bridge.py      # 电脑端桥接程序（调用 Coze、解析指令并下发）
└─ esp32/
   ├─ dorm_main.py     # ESP32 主控程序（传感器采集、状态机、Web Server）
   └─ ssd1306.py       # OLED 显示驱动
```

## 配置

### 1. ESP32 WiFi

在 `esp32/dorm_main.py` 中填写网络信息：

```python
SSID = "YOUR_WIFI_SSID"
PASSWORD = "YOUR_WIFI_PASSWORD"
```

### 2. ESP32 IP

ESP32 启动后会在 Thonny Shell 中输出当前 IP 地址，将其填写到电脑端桥接程序：

```python
ESP32_IP = "YOUR_ESP32_IP"
```

### 3. Coze Token

运行电脑端桥接程序后，按提示在本地输入 Coze Token。Token 不写入源码。

## 运行方法

### 1. 启动 ESP32

将 `esp32/` 目录下的 `dorm_main.py`、`ssd1306.py` 上传到 ESP32：

```text
dorm_main.py
ssd1306.py
```

在 Thonny 中运行主程序，确认 WiFi 连接成功并记录 IP 地址。

### 2. 启动电脑端桥接程序

```bash
python dorm_bridge.py
```

输入 Coze Token 后，即可输入自然语言控制系统。

### 3. 测试场景

```text
我要休息了
我睡醒了
我要去上课了
```

### 4. 解除安防

进入 `SECURITY` 或 `ALERT` 后，通过矩阵键盘输入：

```text
1234 + A
```

密码正确后解除报警并返回 `AUTO`。

## 主要参数

```python
DARK_ON = 2300
BRIGHT_OFF = 1550

PERSON_HOLD_MS = 10000

TEMP_HIGH = 30
TEMP_NORMAL = 28

SECURITY_GRACE_MS = 5000   # 安防离开缓冲（默认 5 秒）
```

> 以上参数均为默认值，定义在 `esp32/dorm_main.py` 开头，可按实际使用环境修改：
> 人体检测保持时间（10 秒）、安防离开缓冲（5 秒）、自动照明双光照阈值、
> 窗帘温度上下阈值等。

- `DARK_ON`：环境较暗时的开灯阈值
- `BRIGHT_OFF`：环境较亮时的关灯阈值
- `PERSON_HOLD_MS`：人体状态保持时间（默认 10 秒）
- `TEMP_HIGH`：高温触发阈值（30℃）
- `TEMP_NORMAL`：温度恢复阈值（28℃）
- `SECURITY_GRACE_MS`：进入安防后的离开缓冲时间（默认 5 秒）

## 核心逻辑

### 自动照明

```text
无人 → 关灯

有人：
light > DARK_ON    → 开灯
light < BRIGHT_OFF → 关灯
中间区间           → 保持原状态
```

### 自适应窗帘

```text
有人 + 高温 + 强光
        ↓
     关闭窗帘
```

### 安防

```text
SECURITY
   ↓
离开缓冲
   ↓
PIR 检测到人体
   ↓
ALERT
   ↓
红灯 + 蜂鸣器报警
   ↓
矩阵键盘密码认证
   ↓
正确密码
   ↓
AUTO
```

## Web 页面

ESP32 运行后，在同一局域网内访问：

```text
http://ESP32_IP
```

页面可查看当前模式、温度、光照、PIR、人员、灯光、窗帘和锁定状态，并提供 `AUTO`、`SLEEP`、`SECURITY` 模式控制入口。

