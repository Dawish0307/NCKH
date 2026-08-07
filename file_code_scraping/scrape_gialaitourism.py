import requests
import json
import csv
import time
import re
import html



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
    
    text = html.unescape(text)
    
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

def safe_unescape(value):
    """Decode HTML entity cho các field text đơn giản (không cần xóa thẻ).""" 
    """
        isinstance(value, str) là kiểm tra xem value có phải 
        là một chuỗi (string) hay không. Nếu value là một chuỗi, 
        thì hàm sẽ thực hiện việc giải mã các thực thể HTML (HTML entities) 
        trong chuỗi đó bằng cách sử dụng html.unescape(value). 
        Sau đó, nó sẽ loại bỏ các khoảng trắng thừa ở đầu và cuối chuỗi bằng phương thức strip() 
        và trả về kết quả đã được xử lý. 
        Nếu value không phải là một chuỗi, 
        hàm sẽ trả về giá trị gốc mà không thực hiện bất kỳ thay đổi nào.
        """
    if isinstance(value, str):
        return html.unescape(value).strip()
    return value

# ----- Trích xuất dữ liệu cần thiết -----
places = []
for item in all_places:
    d = item.get("data_formbuilder", {}) #data_formbuilder là một dict chứa các field của địa điểm được lấy ở trên web. Mỗi field có một key riêng, 
                                         #ví dụ: "vi_265" là tên địa điểm, "vi_267" là địa chỉ, "vi_268" là điện thoại, "vi_338" là mô tả, "vi_276" là diện tích, "vi_1098" là điểm đánh giá, "vi_313" là tọa độ (lat/lng), "vi_335" là ảnh.

    coord = d.get("vi_313") or {} #coord là một dict chứa tọa độ vĩ độ (lat) và kinh độ (lng) của địa điểm. Nếu không có, trả về dict rỗng.
    image = d.get("vi_335") or {} #image là một dict chứa thông tin về ảnh của địa điểm. Nếu không có, trả về dict rỗng.

    mo_ta_raw = d.get("vi_338")        # Mô tả gốc (có thể chứa HTML + ảnh base64)(base64 là phần nặng nhất gây lỗi)
    mo_ta_clean = clean_html_text(mo_ta_raw)

    place = {
        "id": item.get("id"),
        "ten": safe_unescape(d.get("vi_265")),           # Tên địa điểm (field đúng)
        "dia_chi": safe_unescape(d.get("vi_267")),       # Địa chỉ safae_unescape là dùng để giải mã các thực thể HTML (HTML entities) trong chuỗi văn bản.
        "dien_thoai": safe_unescape(d.get("vi_268")),    # Điện thoại
        "mo_ta": mo_ta_clean,             # Mô tả đã dọn sạch HTML/ảnh (dùng cho CSV/Excel)
        "dien_tich": safe_unescape(d.get("vi_276")),     # Diện tích (nếu có)
        "danh_gia": d.get("vi_1098"),     # Điểm đánh giá
        "lat": coord.get("lat"),          # Tọa độ vĩ độ
        "lng": coord.get("lng"),          # Tọa độ kinh độ
        "anh": image.get("value"),        # tên file ảnh
    }
    places.append(place)
    # Giữ riêng bản mô tả gốc (đầy đủ, có HTML/ảnh) để không mất dữ liệu
    place["_mo_ta_raw_html"] = mo_ta_raw #_mo_ta_raw_html là một key trong dict place, dùng để lưu trữ mô tả gốc của địa điểm (có thể chứa HTML và ảnh base64).

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