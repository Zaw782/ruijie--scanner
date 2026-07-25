import json
import hashlib
import time
import os

LICENSE_FILE = "license.json"
SECRET_KEY = "ZawGyI2026SecretKey@123"

def generate_license(key, days):
    expiry = int(time.time()) + (days * 24 * 60 * 60)
    data = {"key": key, "expiry": expiry, "created": int(time.time())}
    signature = hashlib.sha256(f"{key}{expiry}{SECRET_KEY}".encode()).hexdigest()
    data["signature"] = signature
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"✅ License created for Key: {key} | Days: {days}")
    return data

def verify_license():
    if not os.path.exists(LICENSE_FILE):
        return False, "License file not found!"
    with open(LICENSE_FILE, "r") as f:
        data = json.load(f)
    expected_sig = hashlib.sha256(f"{data['key']}{data['expiry']}{SECRET_KEY}".encode()).hexdigest()
    if data.get("signature") != expected_sig:
        return False, "Invalid license signature!"
    if time.time() > data.get("expiry", 0):
        return False, "License expired!"
    remaining_days = int((data['expiry'] - time.time()) / (24 * 60 * 60))
    return True, f"License valid! Remaining: {remaining_days} days"