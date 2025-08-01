import os
import subprocess
import sys

STATUS_FILE = "scanner_status.json"
PID_FILE = "scanner_server.pid"


def start_server():
    if os.path.exists(PID_FILE):
        print("❗ الخادم يعمل بالفعل.")
        return

    process = subprocess.Popen([sys.executable, "scanner_server.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))
    print(f"✅ تم تشغيل الخادم. PID: {process.pid}")


def stop_server():
    if not os.path.exists(PID_FILE):
        print("⚠️ لا يوجد خادم قيد التشغيل.")
        return

    with open(PID_FILE, "r") as f:
        pid = int(f.read())

    try:
        os.kill(pid, 9)
        print("🛑 تم إيقاف الخادم بنجاح.")
    except Exception as e:
        print(f"❌ خطأ في الإيقاف: {e}")
    finally:
        os.remove(PID_FILE)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="التحكم في خادم الفحص.")
    parser.add_argument("action", choices=["start", "stop"], help="start أو stop")
    args = parser.parse_args()

    if args.action == "start":
        start_server()
    else:
        stop_server()