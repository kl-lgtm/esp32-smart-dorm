import json
import time
import requests


# ==================================================
# 1. Coze
# ==================================================

URL = "https://273v935986.coze.site/stream_run"
PROJECT_ID = "7688744513061355566"


# ==================================================
# 2. ESP32
# ==================================================

# 以 dorm_video_final.py 启动后 Shell 实际显示的 IP 为准。
ESP32_IP = "YOUR_ESP32_IP"


# ==================================================
# 3. 调用 Coze
# ==================================================

def ask_coze(token, text):

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    payload = {
        "content": {
            "query": {
                "prompt": [
                    {
                        "type": "text",
                        "content": {
                            "text": text
                        }
                    }
                ]
            }
        },
        "type": "query",
        "session_id": "smart_dorm_video",
        "project_id": PROJECT_ID
    }

    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=60
    )

    response.raise_for_status()

    parts = []

    for line in response.iter_lines(decode_unicode=True):

        if not line or not line.startswith("data:"):
            continue

        data_text = line[5:].strip()

        if not data_text or data_text == "[DONE]":
            continue

        try:
            obj = json.loads(data_text)

            def find_text(x):
                if isinstance(x, str):
                    s = x.strip()
                    if (
                        s
                        and len(s) <= 20
                        and s == s.upper()
                        and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_" for c in s)
                    ):
                        parts.append(s)

                elif isinstance(x, dict):
                    for v in x.values():
                        find_text(v)

                elif isinstance(x, list):
                    for v in x:
                        find_text(v)

            find_text(obj)

        except Exception:
            pass

    result = "".join(parts)

    if "SCENE_SLEEP" in result:
        return "SCENE_SLEEP"

    if "SCENE_SECURITY" in result:
        return "SCENE_SECURITY"

    if "AUTO_MODE" in result:
        return "AUTO_MODE"

    return "UNKNOWN"


# ==================================================
# 4. 发送给 ESP32
# ==================================================

def send_to_esp32(command):

    command_path = {
        "AUTO_MODE": "/ai?cmd=AUTO_MODE",
        "SCENE_SLEEP": "/ai?cmd=SCENE_SLEEP",
        "SCENE_SECURITY": "/ai?cmd=SCENE_SECURITY",
    }

    path = command_path.get(command)

    if path is None:
        return False

    url = "http://" + ESP32_IP + path

    # 演示时偶发网络延迟允许自动再试一次。
    for attempt in range(2):
        try:
            response = requests.get(
                url,
                timeout=5,
                allow_redirects=True
            )

            if response.status_code == 200:
                return True

        except Exception:
            pass

        if attempt == 0:
            time.sleep(0.5)

    return False


# ==================================================
# 5. 启动前检查 ESP32
# ==================================================

def check_esp32():
    try:
        response = requests.get(
            "http://" + ESP32_IP + "/",
            timeout=5
        )
        return response.status_code == 200
    except Exception:
        return False


# ==================================================
# 6. 连续录视频演示主程序
# ==================================================

print()
print("====================================")
print("       smart dorm ai bridge")
print("====================================")
print()

if check_esp32():
    print("esp32: ready")
else:
    print("esp32: offline")
    print("请先确认 ESP32 主程序正在运行且 IP 正确。")

print()
print("  exit         -> 退出")
print()

# Token只在本机输入。录视频时先输入Token，再开始正式拍摄。
token = input("Token：").strip()

print()
print("ai control: ready")
print()

while True:

    text = input("你：").strip() 

    if text.lower() == "exit":
        break

    if not text:
        continue

    try:
        command = ask_coze(token, text)

        print("AI command:", command)

        if command == "UNKNOWN":
            print("ESP32: not sent")
            print()
            continue

        ok = send_to_esp32(command)

        if ok:
            print("ESP32: SUCCESS")
        else:
            print("ESP32: FAILED")

    except Exception as e:
        print("运行错误：", e)

    print()
