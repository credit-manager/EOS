import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, url, method="GET", data=None):
    print(f"\n🧪 اختبار: {name}")
    print(f"   الرابط: {url}")
    try:
        req = urllib.request.Request(url, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(data).encode()
        
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode())
            print(f"✅ نجح!")
            print(f"   النتيجة: {json.dumps(result, ensure_ascii=False, indent=2)[:300]}")
            return True
    except Exception as e:
        print(f"❌ فشل: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 بدء اختبارات API")
    print("=" * 60)
    
    # اختبار 1: جلب الـ Schema
    test_endpoint(
        "جلب Schema الحسابات",
        f"{BASE_URL}/api/v1/dynamic/entities/account/schema"
    )
    
    # اختبار 2: جلب السجلات
    test_endpoint(
        "جلب سجلات الحسابات",
        f"{BASE_URL}/api/v1/dynamic/entities/account/records?limit=5"
    )
    
    # اختبار 3: إنشاء سجل جديد
    test_endpoint(
        "إنشاء حساب تجريبي",
        f"{BASE_URL}/api/v1/dynamic/entities/account/records",
        method="POST",
        data={
            "code": "1000-99",
            "name": "Test Account",
            "name_ar": "حساب تجريبي",
            "account_type": "asset"
        }
    )
    
    print("\n" + "=" * 60)
    print("✅ انتهت الاختبارات")
    print("=" * 60)

if __name__ == "__main__":
    main()