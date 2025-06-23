import requests

res = requests.post('http://127.0.0.1:5000/download', json={
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
})

print(res.json())