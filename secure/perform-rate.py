import requests
import random
import time
from datetime import datetime

BASE_URL = "https://mfh.web.id"  # Secure API di port 5000
GRAFANA_URL = "https://mfh.web.id/grafana"
API_KEY = "glsa_sItmiT4zX4BNNu64G6YBzXNjfAPGIVQ2_8eb9a50f"
DASHBOARD_UID = "aa69d0a9-2546-47e2-b552-b26ee03fa18d"

def add_annotation():
    now = int(time.time() * 1000)
    payload = {
        "dashboardUID": DASHBOARD_UID,
        "time": now,
        "isRegion": False,
        "tags": ["stress-test"],
        "text": "🚀 Stress Test Started (SECURE)"
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    res = requests.post(f"{GRAFANA_URL}/api/annotations", json=payload, headers=headers)
    print("Grafana Annotation:", res.status_code, res.text)

def add_annotation_finished():
    now = int(time.time() * 1000)
    payload = {
        "dashboardUID": DASHBOARD_UID,
        "time": now,
        "isRegion": False,
        "tags": ["stress-test"],
        "text": "✅ Stress Test Finished (SECURE)"
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    res = requests.post(f"{GRAFANA_URL}/api/annotations", json=payload, headers=headers)
    print("Grafana Annotation Finished:", res.status_code, res.text)

def get_token():
    try:
        res = requests.post(f"{BASE_URL}/users/login", json={
            "username": "admin",  # pastikan user ini ada di DB!
            "password": "admin123"
        })
        if res.status_code == 200:
            return res.json().get("access_token")
        else:
            print("Gagal login:", res.text)
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

# Ambil list user
def get_user_ids(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/users/", headers=headers)
        users = res.json()
        if isinstance(users, dict):  # Jika error bentuk dict
            return [1]
        return [u["id"] for u in users]
    except Exception as e:
        print("Gagal fetch user ID:", e)
        return [1]

token = get_token()
if not token:
    print("Token tidak bisa diambil. Exit.")
    exit()

headers_with_auth = {"Authorization": f"Bearer {token}"}
user_ids = get_user_ids(token)

def random_user_id():
    return random.choice(user_ids)

n = 110
durations = []

ENDPOINTS = [
    {"path": "/users/login-rate", "method": "POST"}

]

start_time = time.time()
#add_annotation()
timestart = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for i in range(n):
    config = random.choice(ENDPOINTS)
    if config.get("dynamic"):
        user_id = config.get("id_fn", lambda: 1)()
        path = config["template"].format(user_id)
        params = config.get("params_fn", lambda: {})()
        payload = config.get("payload_fn", lambda: {})()
    else:
        path = config["path"]
        params = config.get("params", {})
        payload = config.get("payload", {})

    url = BASE_URL + path
    method = config["method"]
    # Header: Pakai token jika "auth" True
    headers = headers_with_auth if config.get("auth", False) else {}
    start = time.time()
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, json=payload, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=payload, headers=headers)
        else:
            print(f"[{i+1}] Unsupported method {method}")
            continue
        duration = time.time() - start
        if response.status_code == 200:
            durations.append(duration)
            print(f"[{i+1}/{n}] {method} {path} -> {response.status_code} ({duration*1000:.2f} ms) [SUCCESS]")
        else:
            durations.append(None)
            print(f"[{i+1}/{n}] {method} {path} -> {response.status_code} ({duration*1000:.2f} ms) [FAIL]")
    except Exception as e:
        print(f"[{i+1}/{n}] ERROR: {e}")
        durations.append(None)
    time.sleep(0.1)

#add_annotation_finished()
end_time = time.time()
print("Durasi eksperimen (detik):", end_time - start_time)
durasi_eksperimen = end_time - start_time

valid_durations = [d for d in durations if d is not None]
jumlah_berhasil = len(valid_durations)
jumlah_gagal = durations.count(None)

if valid_durations:
    rata2_response_ms = sum(valid_durations) / jumlah_berhasil * 1000
    throughput = jumlah_berhasil / durasi_eksperimen
else:
    rata2_response_ms = 0
    throughput = 0

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
summary = (
    f"Waktu Mulai          : {timestart}\n"
    f"Waktu Selesai        : {timestamp}\n"
    f"Jumlah Request       : {n}\n"
    f"Request Berhasil     : {jumlah_berhasil}\n"
    f"Request Gagal        : {jumlah_gagal}\n"
    f"Durasi Eksperimen    : {durasi_eksperimen:.2f} detik\n"
    f"Rata-rata Response   : {rata2_response_ms:.2f} ms\n"
    f"Throughput API       : {throughput:.2f} req/detik\n"
    "--------------------------------------------\n"
)
try:
    with open('stress_test_summary_secure.txt', 'r') as f:
        old_content = f.read()
except FileNotFoundError:
    old_content = ""

with open('stress_test_summary_secure.txt', 'w') as f:
    f.write(summary)
    f.write(old_content)

print("Ringkasan hasil eksperimen sudah disimpan di stress_test_summary_secure.txt")
