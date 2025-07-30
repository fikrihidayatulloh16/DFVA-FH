import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print(r.set("test", "value", ex=60))  # Harus return True
print(r.get("test"))  # Harus return b'value'