import urllib.request
import urllib.error

urls = [
    "http://localhost:8000/api/transacciones/",
    "http://localhost:8000/api/transacciones/exportar_csv/",
    "http://localhost:8000/api/transacciones/exportar-csv/"
]

for u in urls:
    try:
        req = urllib.request.Request(u)
        with urllib.request.urlopen(req) as response:
            print(f"{u} -> {response.status}")
    except urllib.error.HTTPError as e:
        print(f"{u} -> HTTP {e.code}")
    except Exception as e:
        print(f"{u} -> ERROR: {e}")
