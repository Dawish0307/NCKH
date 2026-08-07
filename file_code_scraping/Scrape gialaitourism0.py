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
import re


def clean_html_text(raw_html):
    """
    Loại bỏ ảnh base64 và thẻ HTML khỏi mô tả, chỉ giữ lại text thuần.
    Mô tả gốc trên web có thể chứa <img src="data:image/...;base64,...">
    dài hàng chục nghìn ký tự -> vượt giới hạn 32.767 ký tự/ô của Excel,
    làm vỡ cấu trúc file khi xuất CSV/XLSX.
    """
    if not raw_html:
        return raw_html
    text = str(raw_html)
    # Xóa hẳn ảnh base64 (phần nặng nhất gây lỗi)
    text = re.sub(r'data:image/[^"\']+', '[hình ảnh]', text)
    # Xóa các thẻ HTML còn lại (<p>, <span>, <img>, ...)
    text = re.sub(r'<[^>]+>', ' ', text)
    # Gộp khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
    time.sleep(0.5)  # nghỉ giữa các request, tránh spam server

print("Tổng số địa điểm:", len(all_places))

# ----- Trích xuất dữ liệu cần thiết -----
places = []
for item in all_places:
    d = item.get("data_formbuilder", {})

    coord = d.get("vi_313") or {}
    image = d.get("vi_335") or {}

    mo_ta_raw = d.get("vi_338")        # Mô tả gốc (có thể chứa HTML + ảnh base64)
    mo_ta_clean = clean_html_text(mo_ta_raw)

    place = {
        "id": item.get("id"),
        "ten": d.get("vi_265"),           # Tên địa điểm (field đúng)
        "dia_chi": d.get("vi_267"),       # Địa chỉ
        "dien_thoai": d.get("vi_268"),    # Điện thoại
        "mo_ta": mo_ta_clean,             # Mô tả đã dọn sạch HTML/ảnh (dùng cho CSV/Excel)
        "dien_tich": d.get("vi_276"),     # Diện tích (nếu có)
        "danh_gia": d.get("vi_1098"),     # Điểm đánh giá
        "lat": coord.get("lat"),
        "lng": coord.get("lng"),
        "anh": image.get("value"),        # tên file ảnh
    }
    places.append(place)
    # Giữ riêng bản mô tả gốc (đầy đủ, có HTML/ảnh) để không mất dữ liệu
    place["_mo_ta_raw_html"] = mo_ta_raw

# ----- Lưu ra JSON (đầy đủ, bao gồm cả mô tả gốc) -----
with open("gialai_places.json", "w", encoding="utf-8") as f:
    json.dump(places, f, ensure_ascii=False, indent=2)

# ----- Lưu ra CSV (dễ mở bằng Excel) - KHÔNG kèm mô tả gốc để tránh vỡ file -----
csv_fields = [k for k in places[0].keys() if k != "_mo_ta_raw_html"]
with open("gialai_places.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
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