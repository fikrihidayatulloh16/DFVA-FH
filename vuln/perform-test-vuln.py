import requests
import random
import time
from datetime import datetime

BASE_URL = "http://103.196.153.165:5001"
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
        "text": "🚀 Stress Test Started (VULN)"
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
        "text": "✅ Stress Test Finished (VULN)"
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    res = requests.post(f"{GRAFANA_URL}/api/annotations", json=payload, headers=headers)
    print("Grafana Annotation Finished:", res.status_code, res.text)

headers_with_auth = {}

# 🟢 Ambil semua user ID dari endpoint /
try:
    response = requests.get(BASE_URL + "/")
    users = response.json()
    user_ids = [u["id"] for u in users]
    username_admin = next((u["username"] for u in users if u["role"] == "admin"), "admin")
except Exception as e:
    print("Gagal fetch user ID dari API:", e)
    user_ids = [1]
    username_admin = "admin"

def random_user_id():
    return random.choice(user_ids)

# 🟢 List endpoint dinamis
ENDPOINTS = [
    {"path": "/", "method": "GET"},
    {"path": "/users/login", "method": "POST", "payload": {"username": username_admin, "password": "admin123"}},
    {"path": "/users/search", "method": "POST", "payload": {"search_term": username_admin}},
    {"path": "/users/hello", "method": "GET"},
    {"path": "/users/custom-metrics", "method": "GET"},
    {"path": "/dashboard/dashboard", "method": "GET"},
    # 🟢 Endpoint yang butuh ID atau username param akan diisi saat loop
    {"dynamic": True, "template": "/users/admin-panel", "method": "GET", "params_fn": lambda: {"username": username_admin}},
    {"dynamic": True, "template": "/users/profile/{}", "method": "GET", "id_fn": random_user_id},
    {"dynamic": True, "template": "/users/{}", "method": "GET", "id_fn": random_user_id},
    {"dynamic": True, "template": "/users/{}/description", "method": "PUT", "id_fn": random_user_id,
     "payload_fn": lambda: {"description": "Deskripsi baru <script>alert('xss');</script>"}},
]

durasi_target = 20  # detik
durations = []
jumlah_berhasil = 0
jumlah_gagal = 0
i = 0
n = 20

start_time = time.time()
#add_annotation()
timestart = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

while time.time() - start_time < durasi_target:
    i += 1
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
            print(f"[{i}] Unsupported method {method}")
            continue
        duration = time.time() - start
        if response.status_code == 200:
            durations.append(duration)
            jumlah_berhasil += 1
            print(f"[{i}] {method} {path} -> {response.status_code} ({duration*1000:.2f} ms) [SUCCESS]")
        else:
            durations.append(None)
            jumlah_gagal += 1
            print(f"[{i}] {method} {path} -> {response.status_code} ({duration*1000:.2f} ms) [FAIL]")
    except Exception as e:
        print(f"[{i}] ERROR: {e}")
        durations.append(None)
        jumlah_gagal += 1
    time.sleep(0)  # bisa dihilangkan untuk true max load

end_time = time.time()
#add_annotation_finished()
durasi_eksperimen = end_time - start_time

valid_durations = [d for d in durations if d is not None]
if valid_durations:
    rata2_response_ms = sum(valid_durations) / len(valid_durations) * 1000
    throughput = len(valid_durations) / durasi_eksperimen
else:
    rata2_response_ms = 0
    throughput = 0

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
summary = (
    f"Waktu Mulai          : {timestart}\n"
    f"Waktu Selesai        : {timestamp}\n"
    f"Durasi Eksperimen    : {durasi_eksperimen:.2f} detik\n"
    f"Total Request Terkirim : {i}\n"
    f"Request Berhasil     : {jumlah_berhasil}\n"
    f"Request Gagal        : {jumlah_gagal}\n"
    f"Rata-rata Response   : {rata2_response_ms:.2f} ms\n"
    f"Throughput API       : {throughput:.2f} req/detik\n"
    "--------------------------------------------\n"
)

try:
    with open('stress_test_summary_vuln.txt', 'r') as f:
        old_content = f.read()
except FileNotFoundError:
    old_content = ""

with open('stress_test_summary_vuln.txt', 'w') as f:
    f.write(summary)
    f.write(old_content)

print("Ringkasan hasil eksperimen sudah disimpan di stress_test_summary_vuln.txt")
