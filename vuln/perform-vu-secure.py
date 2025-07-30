import asyncio
import aiohttp
import random
import time
from datetime import datetime
import requests

# === KONFIGURASI ===
BASE_URL = "https://mfh.web.id"
VIRTUAL_USERS = 1000
DURATION = 200  # detik
sampling_interval = 200

# === GRAFANA ===
GRAFANA_URL = "https://mfh.web.id/grafana"
API_KEY = "glsa_sItmiT4zX4BNNu64G6YBzXNjfAPGIVQ2_8eb9a50f"
DASHBOARD_UID = "aa69d0a9-2546-47e2-b552-b26ee03fa18d"

# === METRIK GLOBAL ===
success_count = 0
failure_count = 0
response_times = []
request_counter = 0
print_lock = asyncio.Lock()

# === USER CREDENTIALS & TOKEN CACHE ===
user_credentials = [
    {"username": "admin", "password": "admin123"},
    {"username": "user", "password": "user123"},
    {"username": "user2", "password": "user2123"},
]
user_tokens = {}

# === Fungsi Login ===
def get_token(username, password, retries=3):
    for attempt in range(retries):
        try:
            res = requests.post(f"{BASE_URL}/users/login", json={
                "username": username,
                "password": password
            }, timeout=10)
            if res.status_code == 200:
                return res.json().get("access_token")
            else:
                print(f"[{username}] Login gagal ({res.status_code})")
        except Exception as e:
            if attempt == retries - 1:
                print(f"❌ Login gagal untuk {username}: {e}")
        time.sleep(1)
    return None

# === Ambil Token Sebelum Stress Test ===
def prefetch_tokens():
    for cred in user_credentials:
        username = cred["username"]
        password = cred["password"]
        token = get_token(username, password)
        if token:
            user_tokens[username] = token
            print(f"✅ Token untuk {username} berhasil diambil")
        else:
            print(f"❌ Gagal mengambil token untuk {username}")

# === Ambil ID User Dinamis ===
def get_user_ids():
    token = user_tokens.get("admin")
    if not token:
        return [1]
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/users/", headers=headers)
        users = res.json()
        if isinstance(users, dict):
            return [1]
        return [u["id"] for u in users]
    except Exception as e:
        print("Gagal fetch user ID:", e)
        return [1]

# === ID Random User ===
user_ids = []  # Diisi nanti setelah prefetch
def random_user_id():
    return random.choice(user_ids or [1])

# === ENDPOINTS ===
ENDPOINTS = [
    {"path": "/users/", "method": "GET", "auth": True},
    {"path": "/users/login-rate", "method": "POST"},
    {"path": "/users/search", "method": "POST", "auth": True},
    {"path": "/users/hello", "method": "GET"},
    {"path": "/users/custom-metrics", "method": "GET"},
    {"path": "/dashboard/dashboard", "method": "GET"},
    {"dynamic": True, "template": "/users/admin-panel", "method": "GET", "auth": True},
    {"dynamic": True, "template": "/users/profile", "method": "GET", "auth": True},
    {"dynamic": True, "template": "/users/{}", "method": "GET", "id_fn": random_user_id, "auth": True},
    {"dynamic": True, "template": "/users/{}/description", "method": "PUT", "id_fn": random_user_id,
    "payload_fn": lambda: {"description": "Deskripsi baru secure"}, "auth": True},
]

# === GRAFANA ANNOTATION ===
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
        res = requests.post(f"{GRAFANA_URL}/api/annotations", json=payload, headers=headers, timeout=10)
        print(f"Grafana Annotation [{text}]:", res.status_code)
    except Exception as e:
        print(f"❌ Gagal kirim anotasi [{text}]:", e)

# === VIRTUAL USER ===
async def virtual_user(session, end_time):
    global success_count, failure_count, response_times, request_counter

    await asyncio.sleep(random.uniform(0.1, 1.0))  # jitter awal

    selected_user = random.choice(user_credentials)
    username = selected_user["username"]
    token = user_tokens.get(username)

    if not token:
        print(f"[VU] Token kosong untuk {username}")
        return

    headers_with_auth = {"Authorization": f"Bearer {token}"}

    while time.time() < end_time:
        try:
            config = random.choice(ENDPOINTS)
            method = config["method"]
            params = {}
            payload = {}

            if config.get("dynamic"):
                user_id = config.get("id_fn", lambda: 1)()
                path = config["template"].format(user_id)
                params = config.get("params_fn", lambda: {})()
                payload = config.get("payload_fn", lambda: {})()
            else:
                path = config["path"]
                params = config.get("params", {})
                payload = config.get("payload", {})

            if "/search" in path:
                payload = {"search_term": username}

            headers = headers_with_auth if config.get("auth", False) else {}
            url = BASE_URL + path

            start = time.time()
            if method == "GET":
                resp = await session.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                resp = await session.post(url, headers=headers, json=payload, timeout=10)
            elif method == "PUT":
                resp = await session.put(url, headers=headers, json=payload, timeout=10)
            else:
                continue

            resp_text = await resp.text()
            elapsed = (time.time() - start) * 1000
            response_times.append(elapsed)

            async with print_lock:
                request_counter += 1
                if request_counter % sampling_interval == 0:
                    status = "SUCCESS" if resp.status == 200 else f"FAIL ({resp.status})"
                    print(f"[{request_counter}] {username} {method} {path} -> {resp.status} ({elapsed:.2f} ms) [{status}]")
                    if resp.status != 200:
                        print(f"↪ Response: {resp_text}")

            if resp.status == 200:
                success_count += 1
            else:
                failure_count += 1

        except Exception as e:
            failure_count += 1
            async with print_lock:
                request_counter += 1
                if request_counter % sampling_interval == 0:
                    print(f"[{request_counter}] {username} {method} {path} -> EXCEPTION [{type(e).__name__}: {e}]")

# === MAIN ===
async def main():
    global user_ids

    print("🔐 Prefetch token untuk semua user...")
    prefetch_tokens()

    print("🔍 Ambil daftar user ID...")
    user_ids = get_user_ids()
    print(f"✅ Ditemukan {len(user_ids)} user ID.")

    print(f"🚀 Menjalankan {VIRTUAL_USERS} virtual users selama {DURATION} detik...")

    add_annotation(f"🚀Stress Test Started (SECURE {VIRTUAL_USERS} VU)")

    start_time = datetime.now()
    start = time.time()
    end_time = start + DURATION

    from aiohttp import ClientTimeout
    timeout = ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [virtual_user(session, end_time) for _ in range(VIRTUAL_USERS)]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=DURATION + 5)
        except asyncio.TimeoutError:
            print("⏱️ Timeout: Eksperimen dihentikan setelah batas waktu.")

    durasi = time.time() - start
    rata2_resp = sum(response_times) / len(response_times) if response_times else 0
    throughput = success_count / durasi if durasi else 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    add_annotation(f"✅Stress Test Finished (SECURE {VIRTUAL_USERS} VU)")

    summary = (
        f"Waktu Mulai          : {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Waktu Selesai        : {timestamp}\n"
        f"Jumlah Virtual User  : {VIRTUAL_USERS}\n"
        f"Durasi Eksperimen    : {durasi:.2f} detik\n"
        f"Total Request        : {request_counter}\n"
        f"Request Berhasil     : {success_count}\n"
        f"Request Gagal        : {failure_count}\n"
        f"Rata-rata Response   : {rata2_resp:.2f} ms\n"
        f"Throughput API       : {throughput:.2f} req/detik\n"
        "------------------------------------------------------------\n"
    )

    print("\n📊 RINGKASAN HASIL:\n" + summary)

    try:
        with open('stress_test_summary_secure.txt', 'r') as f:
            old = f.read()
    except FileNotFoundError:
        old = ""

    with open('stress_test_summary_secure.txt', 'w') as f:
        f.write(summary + old)

# === EKSEKUSI ===
if __name__ == "__main__":
    asyncio.run(main())
