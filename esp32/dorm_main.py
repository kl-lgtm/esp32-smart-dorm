from machine import Pin, ADC, I2C, PWM
import network
import socket
import time
import onewire
import ds18x20
import ssd1306


# ==================================================
# 1. WiFi
# ==================================================

SSID = "YOUR_WIFI_SSID"
PASSWORD = "YOUR_WIFI_PASSWORD"  # 演示占位：烧录前改为自己 WiFi 密码


# ==================================================
# 2. 系统参数
# ==================================================

# 光敏：
# 数值越大越暗
# 数值越小越亮

DARK_ON = 2300
BRIGHT_OFF = 1550


# PIR人体状态保持时间
PERSON_HOLD_MS = 10000


# ============ 主要参数（可按实际环境调整） ============
# 人体检测与安防缓冲时间、自动照明阈值、窗帘温度阈值等均为默认值，
# 可根据实际使用环境修改：
# - PERSON_HOLD_MS     人体状态保持时间，默认 10 秒
# - SECURITY_GRACE_MS  安防离开缓冲时间，默认 5 秒
# - DARK_ON/BRIGHT_OFF 自动照明双光照阈值（2300/1550），按环境实测标定调整
# - TEMP_HIGH/TEMP_NORMAL 窗帘温度上下阈值（30℃/28℃），按季节或空调设定调整
TEMP_HIGH = 30
TEMP_NORMAL = 28

SECURITY_GRACE_MS = 5000


# 舵机角度
SHADE_OPEN = 0
SHADE_CLOSE = 90


# 矩阵键盘密码
PASSWORD_CODE = "1234"


# ==================================================
# 3. 光敏传感器
# AO -> D34
# ==================================================

light_sensor = ADC(Pin(34))
light_sensor.atten(ADC.ATTN_11DB)


# ==================================================
# 4. PIR
# OUT -> D27
# ==================================================

pir = Pin(27, Pin.IN)


# ==================================================
# 5. RGB
#
# R -> D4
# G -> D16
# B -> D17
# ==================================================

red = Pin(4, Pin.OUT)
green = Pin(16, Pin.OUT)
blue = Pin(17, Pin.OUT)


# ==================================================
# 6. 蜂鸣器
# IO -> D13
# 低电平触发
# ==================================================

buzzer = Pin(13, Pin.OUT)
buzzer.value(1)


# ==================================================
# 7. OLED
#
# SDA -> D21
# SCL -> D22
# ==================================================

i2c = I2C(
    0,
    scl=Pin(22),
    sda=Pin(21)
)

oled = ssd1306.SSD1306_I2C(
    128,
    64,
    i2c
)


# ==================================================
# 8. DS18B20
# DQ -> D25
# ==================================================

ow = onewire.OneWire(Pin(25))

ds = ds18x20.DS18X20(ow)

roms = ds.scan()

print("DS18B20:", roms)


# ==================================================
# 9. 舵机
# signal -> D19
# ==================================================

servo = PWM(
    Pin(19),
    freq=50
)


# ==================================================
# 10. 4×4矩阵键盘
#
# 当前实际接线
#
# 左1 -> D2
# 左2 -> D5
# 左3 -> D18
# 左4 -> D23
#
# 左5 -> D14
# 左6 -> D26
# 左7 -> D33
# 左8 -> D32
#
# 密码：1234
# A：确认
# B：清空
# ==================================================

rows = [
    Pin(2, Pin.OUT),
    Pin(5, Pin.OUT),
    Pin(18, Pin.OUT),
    Pin(23, Pin.OUT)
]


cols = [
    Pin(14, Pin.IN, Pin.PULL_DOWN),
    Pin(26, Pin.IN, Pin.PULL_DOWN),
    Pin(33, Pin.IN, Pin.PULL_DOWN),
    Pin(32, Pin.IN, Pin.PULL_DOWN)
]


keys = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]


for row in rows:
    row.value(0)


last_key_down = None


# ==================================================
# 11. RGB
# ==================================================

def rgb(r, g, b):

    red.value(r)
    green.value(g)
    blue.value(b)


# ==================================================
# 12. 照明
# ==================================================

def lamp_on():

    # RGB三色同时亮
    # 模拟白色宿舍灯
    rgb(1, 1, 1)


def lamp_off():

    rgb(0, 0, 0)


# ==================================================
# 13. 蜂鸣器
# ==================================================

def buzzer_off():

    buzzer.value(1)


def beep(ms=100):

    buzzer.value(0)

    time.sleep_ms(ms)

    buzzer.value(1)


# ==================================================
# 14. 舵机
# ==================================================

def set_servo(angle):

    duty = 26 + angle * 102 // 180

    servo.duty(duty)


# ==================================================
# 15. 光照读取
# ==================================================

def read_light():

    total = 0

    for _ in range(5):

        total += light_sensor.read()

        time.sleep_ms(20)

    return total // 5


# ==================================================
# 16. 温度读取
# ==================================================

def read_temp():

    if not roms:

        return None

    try:

        ds.convert_temp()

        time.sleep_ms(750)

        return ds.read_temp(
            roms[0]
        )

    except:

        return None


# ==================================================
# 17. 键盘扫描
# ==================================================

def scan_key():

    global last_key_down

    detected = None


    for r in range(4):

        rows[r].value(1)

        time.sleep_us(100)


        for c in range(4):

            if cols[c].value() == 1:

                detected = keys[r][c]

                break


        rows[r].value(0)


        if detected is not None:

            break


    # 全部松开
    if detected is None:

        last_key_down = None

        return None


    # 防止长按重复输入
    if detected == last_key_down:

        return None


    last_key_down = detected

    return detected


# ==================================================
# 18. 系统状态
# ==================================================

mode = "AUTO"

lamp_state = False

shade_state = False

lock_state = "UNLOCKED"

security_started = None
security_ready = False

last_message = "READY"


last_motion = (
    time.ticks_ms()
    - PERSON_HOLD_MS
)


input_password = ""

error_count = 0


# 初始状态
lamp_off()

buzzer_off()

set_servo(
    SHADE_OPEN
)


# ==================================================
# 19. OLED临时提示
# ==================================================

def oled_message(
    line1,
    line2=""
):

    oled.fill(0)


    oled.text(
        line1.lower(),
        0,
        18
    )


    if line2:

        oled.text(
            line2.lower(),
            0,
            34
        )


    oled.show()


# ==================================================
# 20. 模式颜色提示
# ==================================================

def mode_hint(r, g, b):

    rgb(r, g, b)

    time.sleep(1)

    lamp_off()


# ==================================================
# 21. AUTO
# ==================================================

def enter_auto(
    show_hint=True
):

    global mode
    global security_started
    global security_ready
    global last_message
    global lock_state
    global input_password
    global error_count


    mode = "AUTO"

    security_started = None
    security_ready = False

    buzzer_off()

    lock_state = "UNLOCKED"

    input_password = ""

    error_count = 0


    if show_hint:

        # 绿色提示
        mode_hint(
            0,
            1,
            0
        )


    last_message = "AUTO"

    print("MODE -> AUTO")


# ==================================================
# 22. SLEEP
# ==================================================

def enter_sleep():

    global mode
    global security_started
    global security_ready
    global lamp_state
    global shade_state
    global last_message
    global lock_state
    global input_password


    mode = "SLEEP"

    security_started = None
    security_ready = False

    buzzer_off()

    lock_state = "UNLOCKED"

    input_password = ""


    # 蓝色提示
    mode_hint(
        0,
        0,
        1
    )


    lamp_off()

    lamp_state = False


    set_servo(
        SHADE_CLOSE
    )

    shade_state = True


    last_message = "SLEEP"

    print("MODE -> SLEEP")


# ==================================================
# 23. SECURITY
# ==================================================

def enter_security():

    global mode
    global security_started
    global security_ready
    global lamp_state
    global shade_state
    global last_message
    global lock_state
    global input_password
    global error_count


    mode = "SECURITY"

    buzzer_off()

    lock_state = "LOCKED"

    input_password = ""

    error_count = 0


    # 红色提示
    mode_hint(
        1,
        0,
        0
    )


    lamp_off()

    lamp_state = False


    set_servo(
        SHADE_CLOSE
    )

    shade_state = True


    security_started = (
        time.ticks_ms()
    )

    # 先等待离开缓冲结束，再等PIR回到低电平，
    # 避免主人离开时PIR保持高电平导致误报警。
    security_ready = False

    last_message = "ARMED"


    print("MODE -> SECURITY")
    print("LOCK -> LOCKED")
    print("exit grace: {} ms".format(SECURITY_GRACE_MS))


# ==================================================
# 24. ALERT
# ==================================================

def enter_alert():

    global mode
    global last_message
    global lock_state
    global input_password


    mode = "ALERT"

    lock_state = "LOCKED"

    input_password = ""

    last_message = "ALERT"


    print()

    print("======================")
    print("!!! ALERT !!!")
    print("======================")


# ==================================================
# 25. 密码正确
# ==================================================

def password_ok():

    global input_password
    global error_count
    global lock_state
    global last_message


    print("PASSWORD OK")


    input_password = ""

    error_count = 0

    lock_state = "UNLOCKED"

    last_message = "ACCESS OK"


    # 先停止报警
    buzzer_off()


    # 短提示音
    beep(100)


    oled_message(
        "access ok",
        "unlocked"
    )


    # 绿色提示
    rgb(
        0,
        1,
        0
    )

    time.sleep(1)


    lamp_off()


    # 返回AUTO
    enter_auto(False)


# ==================================================
# 26. 密码错误
# ==================================================

def password_wrong():

    global input_password
    global error_count
    global last_message


    input_password = ""

    error_count += 1


    last_message = (
        "WRONG {}/3".format(
            error_count
        )
    )


    print(
        "WRONG PASSWORD:",
        error_count,
        "/ 3"
    )


    beep(500)


    if error_count >= 3:

        enter_alert()


    else:

        oled_message(
            "wrong password",
            "try {}/3".format(
                error_count
            )
        )


        time.sleep_ms(700)


# ==================================================
# 27. 键盘处理
# ==================================================

def handle_key(key):

    global input_password
    global last_message


    # 只在SECURITY或ALERT接受密码
    if mode not in (
        "SECURITY",
        "ALERT"
    ):

        return


    print(
        "KEY:",
        key
    )


    # 数字
    if key in "1234567890":

        if len(input_password) < 8:

            input_password += key


        last_message = (
            "PWD:"
            + "*" * len(
                input_password
            )
        )


        print(
            "INPUT:",
            "*" * len(
                input_password
            )
        )


    # A = 确认
    elif key == "A":

        if input_password == PASSWORD_CODE:

            password_ok()

        else:

            password_wrong()


    # B = 清空
    elif key == "B":

        input_password = ""

        last_message = "PWD CLEARED"

        print(
            "PASSWORD CLEARED"
        )


# ==================================================
# 28. WiFi连接
# ==================================================

wifi = network.WLAN(
    network.STA_IF
)


wifi.active(False)

time.sleep(1)


wifi.active(True)

time.sleep(1)


try:

    wifi.disconnect()

except:

    pass


print()

print("======================")
print("Connecting WiFi...")
print("SSID:", SSID)
print("======================")


wifi.connect(
    SSID,
    PASSWORD
)


for i in range(30):

    if wifi.isconnected():

        break


    print(
        "Waiting:",
        i + 1,
        "| Status:",
        wifi.status()
    )


    time.sleep(1)


if not wifi.isconnected():

    print("WiFi FAILED")

    raise Exception(
        "WiFi connection failed"
    )


ip = wifi.ifconfig()[0]


print()

print("======================")
print("WiFi SUCCESS!")
print("IP:", ip)
print("Open: http://" + ip)
print("======================")
print()


# ==================================================
# 29. Web服务器
# ==================================================

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)


try:

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

except:

    pass


server.bind(
    (
        "",
        80
    )
)


server.listen(2)

server.settimeout(0.2)


print(
    "Web Server Started"
)


# ==================================================
# 30. 网页
# ==================================================

def make_page(
    temp,
    light_value,
    light_status,
    person,
    raw_pir
):

    if temp is None:

        temp_text = "err"

    else:

        temp_text = (
            "{:.1f} c".format(
                temp
            )
        )


    if mode == "SECURITY":

        security_text = "armed"

    elif mode == "ALERT":

        security_text = "alert"

    else:

        security_text = "normal"


    password_display = (
        "*" * len(
            input_password
        )
    )


    html = """<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>Smart Dorm</title>

<style>

body {{
    font-family: Arial;
    text-align: center;
    background: #f2f4f7;
}}

.card {{
    max-width: 430px;
    margin: 20px auto;
    padding: 20px;
    background: white;
    border-radius: 16px;
}}

button {{
    width: 150px;
    padding: 13px;
    margin: 6px;
    font-size: 16px;
    border: none;
    border-radius: 10px;
}}

.auto {{
    background: #4CAF50;
    color: white;
}}

.sleep {{
    background: #2196F3;
    color: white;
}}

.security {{
    background: #F44336;
    color: white;
}}

</style>

</head>

<body>

<div class="card">

<h2>Smart Dorm</h2>

<h3>Mode: {mode}</h3>

<p>Security: {security}</p>

<p>Logical Lock: {lock}</p>

<p>Message: {message}</p>

<p>Password: {password_display}</p>

<hr>

<p>Temp: {temp}</p>

<p>Light: {light} ({light_status})</p>

<p>PIR Raw: {raw_pir}</p>

<p>Person: {person}</p>

<p>Lamp: {lamp}</p>

<p>Shade: {shade}</p>

<hr>

<form action="/mode"
method="get">

<button
class="auto"
type="submit"
name="set"
value="auto">
AUTO
</button>

<button
class="sleep"
type="submit"
name="set"
value="sleep">
SLEEP
</button>

<button
class="security"
type="submit"
name="set"
value="security">
SECURITY
</button>

</form>

<p>
Security / Alert must be unlocked by keypad
</p>

</div>

</body>

</html>
""".format(

        mode=mode.lower(),

        security=security_text,

        lock=lock_state.lower(),

        message=last_message.lower(),

        password_display=password_display,

        temp=temp_text,

        light=light_value,

        light_status=(
            light_status.lower()
        ),

        raw_pir=raw_pir,

        person=(
            "yes"
            if person
            else "no"
        ),

        lamp=(
            "on"
            if lamp_state
            else "off"
        ),

        shade=(
            "close"
            if shade_state
            else "open"
        )
    )


    return html


# ==================================================
# 31. 初始温度
# ==================================================

temp = read_temp()

last_temp_ms = (
    time.ticks_ms()
)


# ==================================================
# 32. 主循环
# ==================================================

while True:

    now = (
        time.ticks_ms()
    )


    # ==================================================
    # 键盘
    # ==================================================

    key = scan_key()


    if key is not None:

        handle_key(
            key
        )


    # ==================================================
    # PIR
    # ==================================================

    raw_pir = (
        pir.value()
    )


    if raw_pir == 1:

        last_motion = now


    person = (
        time.ticks_diff(
            now,
            last_motion
        )
        < PERSON_HOLD_MS
    )


    # ==================================================
    # 光照
    # ==================================================

    light_value = (
        read_light()
    )


    if (
        light_value
        > DARK_ON
    ):

        light_status = "DARK"


    elif (
        light_value
        < BRIGHT_OFF
    ):

        light_status = "BRIGHT"


    else:

        light_status = "MID"


    # ==================================================
    # 温度
    # ==================================================

    if (
        time.ticks_diff(
            now,
            last_temp_ms
        )
        >= 2000
    ):

        temp = read_temp()

        last_temp_ms = (
            time.ticks_ms()
        )


    # ==================================================
    # Web请求
    # ==================================================

    client = None

    redirect = False


    try:

        client, addr = (
            server.accept()
        )


        request = (
            client.recv(1024)
            .decode()
        )


        first_line = (
            request
            .split("\r\n")[0]
        )


        parts = (
            first_line.split(" ")
        )


        if len(parts) >= 2:

            path = parts[1]

        else:

            path = "/"


        print(
            "WEB:",
            path
        )


        # ==============================================
        # AUTO
        # ==============================================

        if (
            path == "/mode?set=auto"
            or
            path == "/ai?cmd=AUTO_MODE"
        ):

            # SECURITY / ALERT不能直接解除
            if mode in (
                "SECURITY",
                "ALERT"
            ):

                last_message = (
                    "PASSWORD REQUIRED"
                )

                print(
                    "AUTO DENIED - PASSWORD REQUIRED"
                )


            else:

                enter_auto()


            redirect = True


        # ==============================================
        # SLEEP
        # ==============================================

        elif (
            path == "/mode?set=sleep"
            or
            path == "/ai?cmd=SCENE_SLEEP"
        ):

            if mode in (
                "SECURITY",
                "ALERT"
            ):

                last_message = (
                    "PASSWORD REQUIRED"
                )

                print(
                    "SLEEP DENIED - PASSWORD REQUIRED"
                )


            else:

                enter_sleep()


            redirect = True


        # ==============================================
        # SECURITY
        # ==============================================

        elif (
            path == "/mode?set=security"
            or
            path == "/ai?cmd=SCENE_SECURITY"
        ):

            if mode in (
                "SECURITY",
                "ALERT"
            ):

                last_message = (
                    "PASSWORD REQUIRED"
                )


            else:

                enter_security()


            redirect = True


        # ==============================================
        # favicon
        # ==============================================

        elif (
            path == "/favicon.ico"
        ):

            client.send(
                b"HTTP/1.1 204 No Content\r\n"
                b"Connection: close\r\n\r\n"
            )

            client.close()

            client = None


    except OSError:

        pass


    except Exception as e:

        print(
            "WEB ERROR:",
            e
        )


    # ==================================================
    # AUTO
    # ==================================================

    if mode == "AUTO":

        buzzer_off()


        # ==============================================
        # 自动照明
        #
        # 双阈值滞回控制
        #
        # >2300  开灯
        # <1550  关灯
        # 中间区域保持原状态
        # ==============================================

        if not person:

            # 无人
            lamp_off()

            lamp_state = False


        else:

            # 环境明显变暗
            if (
                light_value
                > DARK_ON
            ):

                lamp_on()

                lamp_state = True


            # 环境真正足够亮
            elif (
                light_value
                < BRIGHT_OFF
            ):

                lamp_off()

                lamp_state = False


            # 1550～2300
            # 保持之前的灯状态
            else:

                if lamp_state:

                    lamp_on()

                else:

                    lamp_off()


        # ==============================================
        # 自适应窗帘
        #
        # 有人 + 高温 + 强光
        # → 关闭窗帘
        # ==============================================

        if (
            person
            and
            temp is not None
            and
            temp >= TEMP_HIGH
            and
            light_status == "BRIGHT"
        ):

            set_servo(
                SHADE_CLOSE
            )

            shade_state = True


        elif (
            temp is None
            or
            temp <= TEMP_NORMAL
            or
            light_status != "BRIGHT"
        ):

            set_servo(
                SHADE_OPEN
            )

            shade_state = False


    # ==================================================
    # SLEEP
    # ==================================================

    elif mode == "SLEEP":

        buzzer_off()


        lamp_off()

        lamp_state = False


        set_servo(
            SHADE_CLOSE
        )

        shade_state = True


    # ==================================================
    # SECURITY
    # ==================================================

    elif mode == "SECURITY":

        buzzer_off()

        lamp_off()
        lamp_state = False

        set_servo(
            SHADE_CLOSE
        )
        shade_state = True

        if security_started is not None:

            elapsed = time.ticks_diff(
                now,
                security_started
            )

            # 先过离开缓冲时间。
            # 缓冲结束后必须看到一次PIR低电平，才正式进入入侵检测，
            # 防止刚离开时PIR自身延时保持高电平造成误报警。
            if elapsed >= SECURITY_GRACE_MS:

                if not security_ready:

                    if raw_pir == 0:
                        security_ready = True
                        last_message = "ARMED READY"
                        print("SECURITY READY")

                elif raw_pir == 1:

                    print("PIR IN SECURITY!")
                    enter_alert()


    # ==================================================
    # ALERT
    # ==================================================

    elif mode == "ALERT":

        # 窗帘保持关闭
        set_servo(
            SHADE_CLOSE
        )

        shade_state = True


        # 红灯 + 蜂鸣器闪烁
        phase = (
            now // 400
        ) % 2


        if phase == 0:

            rgb(
                1,
                0,
                0
            )

            buzzer.value(0)


        else:

            lamp_off()

            buzzer.value(1)


        lamp_state = False


    # ==================================================
    # OLED最终显示
    #
    # 全部小写
    #
    # mode
    # light
    # temp
    # person
    # lamp
    # shade
    # lock
    #
    # 只有报警时显示 alarm!!!
    # ==================================================

    oled.fill(0)


    # 1 mode
    oled.text(
        "mode:"
        + mode.lower(),
        0,
        0
    )


    # 2 light
    oled.text(
        "light:{}".format(
            light_value
        ),
        0,
        8
    )


    # 3 temp
    if temp is None:

        temp_text = "err"

    else:

        temp_text = (
            "{:.1f}c".format(
                temp
            )
        )


    oled.text(
        "temp:"
        + temp_text,
        0,
        16
    )


    # 4 person
    oled.text(
        "person:"
        + (
            "yes"
            if person
            else "no"
        ),
        0,
        24
    )


    # 5 lamp
    oled.text(
        "lamp:"
        + (
            "on"
            if lamp_state
            else "off"
        ),
        0,
        32
    )


    # 6 shade
    oled.text(
        "shade:"
        + (
            "close"
            if shade_state
            else "open"
        ),
        0,
        40
    )


    # 7 lock
    oled.text(
        "lock:"
        + lock_state.lower(),
        0,
        48
    )


    # 8 alarm
    if mode == "ALERT":

        oled.text(
            "alarm!!!",
            0,
            56
        )


    oled.show()


    # ==================================================
    # Web响应
    # ==================================================

    if client is not None:

        try:

            if redirect:

                client.send(
                    b"HTTP/1.1 303 See Other\r\n"
                    b"Location: /\r\n"
                    b"Connection: close\r\n\r\n"
                )


            else:

                page = make_page(
                    temp,
                    light_value,
                    light_status,
                    person,
                    raw_pir
                )


                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; "
                    "charset=utf-8\r\n"
                    "Cache-Control: no-store\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    + page
                )


                client.send(
                    response.encode()
                )


        except Exception as e:

            print(
                "WEB SEND ERROR:",
                e
            )


        try:

            client.close()

        except:

            pass


    time.sleep_ms(50)
