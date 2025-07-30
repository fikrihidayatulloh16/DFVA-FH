import requests
import time
from datetime import datetime

def test_rate_limit():
    print("=== Starting test ===")
    base_url = "https://mfh.web.id/users/login-rate"
    
    for i in range(104):
        try:
            response = requests.post(base_url)
            print(f"[{datetime.now()}] Request {i+1}: {response.status_code}")
            print("Response:", response.text)
            print("Headers:", {k: v for k, v in response.headers.items() if 'RateLimit' in k})
        except Exception as e:
            print(f"Error: {e}")
        
        if i == 99:
            print("=== Waiting 30 seconds ===")
            time.sleep(30)
            
        if i == 101:
            print("=== Waiting 30 seconds ===")
            time.sleep(30)

if __name__ == "__main__":
    test_rate_limit()
