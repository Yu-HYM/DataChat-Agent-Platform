import requests
BASE = "http://localhost:9000"

# 1. Get token
r = requests.post(f"{BASE}/auth/token", params={"user": "alice"})
token = r.json()["token"]
print(f"1. Token: {token[:20]}...")

# 2. Chat - GMV
r = requests.post(f"{BASE}/chat", headers={"Authorization": f"Bearer {token}"}, params={"q": "最近三天GMV是多少", "thread_id": "test"}, timeout=180)
print(f"\n2. GMV Chat: {r.json()['answer'][:200]}")

# 3. Chat - 复购率口径
r = requests.post(f"{BASE}/chat", headers={"Authorization": f"Bearer {token}"}, params={"q": "复购率的口径是什么", "thread_id": "test"}, timeout=180)
print(f"\n3. 复购率口径: {r.json()['answer'][:200]}")

# 4. KB search
r = requests.post(f"{BASE}/kb/search", headers={"Authorization": f"Bearer {token}"}, params={"q": "GMV是什么", "top_k": 2}, timeout=30)
for item in r.json()["results"]:
    print(f"\n4. KB搜索: score={item['score']:.3f} source={item['source']}")

# 5. No token
r = requests.post(f"{BASE}/chat", params={"q": "test"})
print(f"\n5. No token: status={r.status_code}")
