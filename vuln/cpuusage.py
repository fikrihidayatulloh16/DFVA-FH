import psutil
from time import sleep

while True:
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    print(f"CPU: {cpu}%, Memory: {mem}%")
    sleep(1)