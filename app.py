"""
CityPulse local entry point.
Run: python app.py
Open: http://127.0.0.1:8000/
"""
import uvicorn
from backend.app import app

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8000

if __name__ == "__main__":
    print("=" * 65)
    print("  CityPulse - Living City Model")
    print(f"  Server running on http://{LOCAL_HOST}:{LOCAL_PORT}")
    print("=" * 65)
    uvicorn.run(app, host=LOCAL_HOST, port=LOCAL_PORT)
