"""
Script scrape danh sách địa điểm du lịch từ gialaitourism.vn
Dùng API public: /headlessCms/api/public/getDataSearchByKeyAndEnum
(Endpoint này được website tự dùng để hiển thị danh sách điểm du lịch,
không cần đăng nhập / cookie).

Nếu bị lỗi SSLCertVerificationError, chạy trước:
    python -m pip install pip-system-certs
"""

import requests
import json
import csv
import time

URL = "https://gialaitourism.vn/headlessCms/api/public/getDataSearchByKeyAndEnum"

# Header lấy đúng từ request thật của trình duyệt (trong file HAR)
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": "https://gialaitourism.vn",
    "Referer": "https://gialaitourism.vn/diem-du-lich.html",
}

PAGE_SIZE = 12
page = 1
all_places = []

while True:
    payload = [
        {
            "formId": 64,
            "list_data_search": [],
            "key_search": "",
            "localization": "vi",
            "pagination": {
                "currentPage": page,
                "pageSize": PAGE_SIZE,
            },
            "trang_thai": 1,
            "pageBuilderOptionid": 31703,
        }
    ]

    r = requests.post(URL, json=payload, headers=headers, timeout=15)
    r.raise_for_status()

    result = r.json()["result"][0]
    data = result["data"]

    if not data:
        break

    all_places.extend(data)
    total = result["pagination"]["total"]

    print(f"Đã lấy trang {page} ({len(all_places)}/{total})")

    if len(all_places) >= total:
        break

    page += 1
    time.sleep(1)  # nghỉ giữa các request, tránh spam server

print("Tổng số địa điểm:", len(all_places))

# ----- Trích xuất dữ liệu cần thiết -----
places = []
for item in all_places:
    d = item.get("data_formbuilder", {})

    coord = d.get("vi_313") or {}
    image = d.get("vi_335") or {}

    place = {
        "id": item.get("id"),
        "ten": d.get("vi_265"),           # Tên địa điểm (field đúng)
        "dia_chi": d.get("vi_267"),       # Địa chỉ
        "dien_thoai": d.get("vi_268"),    # Điện thoại
        "mo_ta": d.get("vi_338"),         # Mô tả
        "dien_tich": d.get("vi_276"),     # Diện tích (nếu có)
        "danh_gia": d.get("vi_1098"),     # Điểm đánh giá
        "lat": coord.get("lat"),
        "lng": coord.get("lng"),
        "anh": image.get("value"),        # tên file ảnh
    }
    places.append(place)

# ----- Lưu ra JSON -----
with open("gialai_places.json", "w", encoding="utf-8") as f:
    json.dump(places, f, ensure_ascii=False, indent=2)

# ----- Lưu ra CSV (dễ mở bằng Excel) -----
with open("gialai_places.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(places[0].keys()))
    writer.writeheader()
    writer.writerows(places)

print("Đã lưu: gialai_places.json và gialai_places.csv")

# In thử vài kết quả đầu để kiểm tra nhanh
for i, p in enumerate(places[:5], 1):
    print("=" * 60)
    print(i, "-", p["ten"])
    print("Địa chỉ:", p["dia_chi"])
    print("Điện thoại:", p["dien_thoai"])
    print("Tọa độ:", p["lat"], p["lng"])