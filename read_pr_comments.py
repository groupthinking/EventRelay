import urllib.request
import json

url = "https://api.github.com/repos/groupthinking/EventRelay/pulls/733/reviews"
req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github.v3+json'})
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(json.dumps(data, indent=2))
except Exception as e:
    print(e)
