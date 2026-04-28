import requests
from typing import Optional, Dict, Any, Union


class HttpClient:
    """HTTP GET/POST 封装"""

    def __init__(self, base_url: str = "", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def get(self, path: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """发送 GET 请求"""
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, data: Optional[Dict] = None, json: Optional[Dict] = None,
             headers: Optional[Dict] = None) -> Dict[str, Any]:
        """发送 POST 请求"""
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, data=data, json=json, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def put(self, path: str, json: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.put(url, json=json, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def delete(self, path: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.delete(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


# ============ 用例 ============

if __name__ == "__main__":
    client = HttpClient(base_url="https://api.example.com")

    # 1. GET 请求 - 获取列表
    users = client.get("/users", params={"page": 1, "limit": 10})
    print(f"获取用户列表: {users}")

    # 2. GET 请求 - 获取单个资源
    user = client.get("/users/123")
    print(f"获取单个用户: {user}")

    # 3. POST 请求 - 创建资源
    new_user = client.post("/users", json={"name": "张三", "email": "zhangsan@example.com"})
    print(f"创建用户: {new_user}")

    # 4. POST 请求 - 登录
    token = client.post("/auth/login", json={"username": "admin", "password": "123456"})
    print(f"登录结果: {token}")

    # 5. PUT 请求 - 更新资源
    updated = client.put("/users/123", json={"name": "李四", "email": "lisi@example.com"})
    print(f"更新用户: {updated}")

    # 6. DELETE 请求 - 删除资源
    result = client.delete("/users/123")
    print(f"删除结果: {result}")