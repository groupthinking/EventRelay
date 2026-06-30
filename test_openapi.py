
import requests

BASE_URL = "http://localhost:8001"

def get_openapi():
    res = requests.get(f"{BASE_URL}/openapi.json")
    if res.status_code == 200:
        data = res.json()
        paths = list(data.get("paths", {}).keys())
        print("Registered paths:")
        for path in paths:
            print(f"  {path}")
    else:
        print(f"Failed to get OpenAPI spec: {res.status_code}")

if __name__ == "__main__":
    get_openapi()
