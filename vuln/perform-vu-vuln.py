import aiohttp
import asyncio
import random
import time
from datetime import datetime
import requests

BASE_URL = "http://103.196.153.165:5001"
VIRTUAL_USERS = 1000
DURATION = 200  # detik
USERNAME = "admin"
PASSWORD = "admin123"

# Global shared counter
success_count = 0
failure_count = 0
response_times = []
request_counter = 0
print_lock = asyncio.Lock()
sampling_interval = 100  # bisa diubah ke 100 atau 25

# === GRAFANA ===
GRAFANA_URL = "https://mfh.web.id/grafana"
API_KEY = "glsa_sItmiT4zX4BNNu64G6YBzXNjfAPGIVQ2_8eb9a50f"
DASHBOARD_UID = "aa69d0a9-2546-47e2-b552-b26ee03fa18d"

# === USER CREDENTIALS ===
user_credentials = [
    {"username": "admin", "password": "admin123"},
    {"username": "user", "password": "user123"},
    {"username": "user2", "password": "user2123"},
]

# === ANOTASI GRAFANA ===
def add_annotation(text):
    now = int(time.time() * 1000)
    payload = {
        "dashboardUID": DASHBOARD_UID,
        "time": now,
        "isRegion": False,
        "tags": ["stress-test"],
        "text": text
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(f"{GRAFANA_URL}/api/annotations", json=payload, headers=headers, timeout=30)
        print(f"Grafana Annotation [{text}]: {res.status_code} {res.reason}")
        print("↪ Response:", res.text)
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal kirim anotasi [{text}]:", str(e))

# Endpoints
user_ids = [1, 2, 3]  # Ubah jika lebih banyak user
def random_user_id():
    return random.choice(user_ids)

ENDPOINTS = [
    {"dynamic_login": True, "template": "/users/login-rate", "method": "POST"},
    {"path": "/", "method": "GET"},
    {"dynamic_login": True, "template": "/users/login", "method": "POST"},
    {"dynamic_search": True, "template": "/users/search", "method": "POST"},
    {"path": "/users/hello", "method": "GET"},
    {"path": "/users/custom-metrics", "method": "GET"},
    {"path": "/dashboard/dashboard", "method": "GET"},
    {"dynamic": True, "template": "/users/admin-panel", "method": "GET", "params_fn": lambda: {"username": "admin"}},
    {"dynamic": True, "template": "/users/profile/{}", "method": "GET", "id_fn": random_user_id},
    {"dynamic": True, "template": "/users/{}", "method": "GET", "id_fn": random_user_id},
    {"dynamic": True, "template": "/users/{}/description", "method": "PUT", "id_fn": random_user_id,
    "payload_fn": lambda: {"description": "Deskripsi baru <script>alert('xss');</script>"}}
]

# Virtual user function
async def virtual_user(session, end_time):
    global success_count, failure_count, response_times, request_counter

    while time.time() < end_time:
        config = random.choice(ENDPOINTS)
        method = config["method"]
        params = {}
        payload = {}

        # Ambil salah satu user acak
        selected_user = random.choice(user_credentials)
        selected_username = selected_user["username"]
        selected_password = selected_user["password"]

        # Tentukan path dan payload sesuai jenis endpoint
        if config.get("dynamic_login"):
            path = config["template"]
            payload = {"username": selected_username, "password": selected_password}

        elif config.get("dynamic_search"):
            path = config["template"]
            payload = {"search_term": selected_username}

        elif config.get("dynamic"):
            user_id = config.get("id_fn", lambda: 1)()
            path = config["template"].format(user_id)
            params = config.get("params_fn", lambda: {})()
            payload = config.get("payload_fn", lambda: {})()

        else:  # endpoint statis
            path = config["path"]
            params = config.get("params", {})
            payload = config.get("payload", {})

        url = BASE_URL + path

        # Mulai request
        start = time.time()
        try:
            resp = None
            if method == "GET":
                resp = await session.get(url, params=params, timeout=5)
            elif method == "POST":
                resp = await session.post(url, json=payload, timeout=5)
            elif method == "PUT":
                resp = await session.put(url, json=payload, timeout=5)

            await resp.text()
            elapsed = (time.time() - start) * 1000
            response_times.append(elapsed)

            async with print_lock:
                request_counter += 1
                if request_counter % sampling_interval == 0:
                    status = "SUCCESS" if resp.status == 200 else f"FAIL ({resp.status})"
                    print(f"[{request_counter}] {method} {path} -> {resp.status} ({elapsed:.2f} ms) [{status}]")

            if resp.status == 200:
                success_count += 1
            else:
                failure_count += 1

        except Exception as e:
            failure_count += 1
            async with print_lock:
                request_counter += 1
                if request_counter % sampling_interval == 0:
                    print(f"[{request_counter}] {method} {path} -> EXCEPTION [{type(e).__name__}: {e}]")




# Main
async def main():
    global success_count, failure_count, response_times
    success_count = 0
    failure_count = 0
    response_times = []

    timestart = datetime.now()
    add_annotation(f"🚀 Stress Test Started ({VIRTUAL_USERS} VU)")
    print(f"🚀 Menjalankan {VIRTUAL_USERS} virtual users selama {DURATION} detik...")
    start = time.time()
    end_time = start + DURATION

    async with aiohttp.ClientSession() as session:
        tasks = [virtual_user(session, end_time) for _ in range(VIRTUAL_USERS)]
        await asyncio.gather(*tasks)

    add_annotation(f"✅ Stress Test Finished ({VIRTUAL_USERS} VU)")  # ✅ Tambahan ini

    durasi = time.time() - start
    rata2_resp = sum(response_times) / len(response_times) if response_times else 0
    throughput = success_count / durasi if durasi else 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary = (
        f"Waktu Mulai          : {timestart.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Waktu Selesai        : {timestamp}\n"
        f"Jumlah Virtual User  : {VIRTUAL_USERS}\n"
        f"Durasi Eksperimen    : {durasi:.2f} detik\n"
        f"Total Request        : {success_count + failure_count}\n"
        f"Request Berhasil     : {success_count}\n"
        f"Request Gagal        : {failure_count}\n"
        f"Rata-rata Response   : {rata2_resp:.2f} ms\n"
        f"Throughput API       : {throughput:.2f} req/detik\n"
        "------------------------------------------------------------\n"
    )

    print("\n📊 RINGKASAN HASIL:\n" + summary)

    try:
        with open("stress_test_summary_async_vuln.txt", "r") as f:
            old = f.read()
    except FileNotFoundError:
        old = ""

    with open("stress_test_summary_async_vuln.txt", "w") as f:
        f.write(summary + old)

# Run
if __name__ == "__main__":
    asyncio.run(main())
