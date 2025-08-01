import json
import os
from datetime import datetime

STATUS_FILE = "scanner_status.json"

def write_status(running: bool, last_update: str = None):
    """تحديث حالة الماسح"""
    status = {
        "running": running,
        "last_update": last_update or datetime.utcnow().isoformat()
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

def read_status():
    """قراءة حالة الماسح"""
    if not os.path.exists(STATUS_FILE):
        return {"running": False, "last_update": None}
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"running": False, "last_update": None}