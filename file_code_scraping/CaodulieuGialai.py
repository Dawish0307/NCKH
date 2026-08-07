import requests
import json
import csv
import time
import re
import html
import os


def clean_html_text(raw_html):
    
    if not raw_html: #raw_html là một chuỗi HTML thô (có thể chứa thẻ HTML và ảnh base64). Nếu raw_html là None hoặc rỗng, hàm sẽ trả về raw_html mà không xử lý gì thêm.
        return raw_html
    text = str(raw_html)

    text = html.unescape(text) # html.unescape là một hàm trong module html của Python, dùng để giải mã các thực thể HTML (HTML entities) trong chuỗi văn bản. 
                               #Ví dụ, nó sẽ chuyển đổi "&amp;" thành "&", "&lt;" thành "<", và "&gt;" thành ">". 
                               # Điều này giúp làm cho văn bản trở nên dễ đọc hơn sau khi loại bỏ các thẻ HTML và ảnh base64.

    # Xóa hẳn ảnh base64 (phần nặng nhất gây lỗi)
    text = re.sub(r'data:image/[^"\']+', '[hình ảnh]', text) #re.sub là một hàm trong module re (regular expression) của Python, 
                                                             #dùng để thay thế các chuỗi con trong một chuỗi bằng một chuỗi khác. 
                                                             # Ở đây, nó tìm tất cả các chuỗi bắt đầu bằng "data:image/" và 
                                                             # kết thúc trước dấu nháy kép hoặc nháy đơn, và thay thế chúng bằng "[hình ảnh]". 
                                                             # Điều này giúp loại bỏ các ảnh được nhúng dưới dạng base64 trong HTML, 
                                                             # vì chúng có thể rất dài và gây lỗi khi xuất ra CSV/XLSX.

    # Xóa các thẻ HTML còn lại (<p>, <span>, <img>, ...)
    text = re.sub(r'<[^>]+>', ' ', text)
    # Gộp khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def safe_unescape(value):
    """Decode HTML entity cho các field text đơn giản (không cần xóa thẻ)."""
    if isinstance(value, str):
        return html.unescape(value).strip()
    return value


BASE_URL = "https://gialaitourism.vn"
IMAGE_PREVIEW_PATH = "/headlessCms/api/public/document/preview/"


def build_image_url(image_field):
    """
    Ghép link ảnh thật từ field vi_335.
    Cấu trúc thực tế lấy từ file HAR:
        vi_335 = {"id": "2797", "value": "bao tang.jpg", "trangThai": 1}
    Link ảnh thật (đã kiểm chứng khớp với ảnh tải trong HAR):
        https://gialaitourism.vn/headlessCms/api/public/document/preview/{id}
    """
    if not image_field or not isinstance(image_field, dict):
        return ""
    doc_id = image_field.get("id")
    if not doc_id:
        return ""
    return f"{BASE_URL}{IMAGE_PREVIEW_PATH}{doc_id}"


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
    image_field = d.get("vi_335") or {}

    mo_ta_raw = d.get("vi_338") #mo_ta_raw là một biến chứa dữ liệu mô tả gốc (raw HTML) của địa điểm du lịch, được lấy từ trường "vi_338" trong dictionary d.
    mo_ta_clean = clean_html_text(mo_ta_raw)

    place = {
        "id": item.get("id"),
        "ten": safe_unescape(d.get("vi_265")),
        "dia_chi": safe_unescape(d.get("vi_267")),
        "dien_thoai": safe_unescape(d.get("vi_268")),
        "mo_ta": mo_ta_clean,
        "dien_tich": safe_unescape(d.get("vi_276")),
        "danh_gia": d.get("vi_1098"),
        "lat": coord.get("lat"),
        "lng": coord.get("lng"),
        "anh": image_field.get("value"),       # tên file ảnh gốc
        "anh_url": build_image_url(image_field),  # link ảnh thật, xem trực tiếp trên trình duyệt
    }
    places.append(place) # lệnh append() thêm một phần tử vào cuối danh sách places. 
                        #Ở đây, mỗi phần tử là một dictionary chứa thông tin chi tiết về một địa điểm du lịch, 
                        # bao gồm tên, địa chỉ, điện thoại, mô tả, diện tích, đánh giá, tọa độ (lat/lng), tên file ảnh gốc và link ảnh thật.
    place["_mo_ta_raw_html"] = mo_ta_raw #_mo_ta_raw_html được tìm thấy trong dictionary place, chứa mô tả gốc (raw HTML) của địa điểm.

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

# ----- Tải ảnh về thư mục riêng "images/" -----
IMAGE_DIR = "images" # image_dir là một biến chứa tên thư mục nơi các ảnh sẽ được lưu trữ. Trong trường hợp này, các ảnh sẽ được lưu trong thư mục có tên "images".
os.makedirs(IMAGE_DIR, exist_ok=True) # os.makedirs là một hàm trong thư viện os của Python, được sử dụng để tạo một thư mục mới.
                                      # Tham số IMAGE_DIR là đường dẫn đến thư mục cần tạo.
                                        # Tham số exist_ok=True cho phép bỏ qua lỗi nếu thư mục đã tồn tại, nghĩa là nếu thư mục đã tồn tại, 
                                        # hàm sẽ không gây ra lỗi và tiếp tục thực hiện các lệnh tiếp theo.


def safe_filename(name, fallback):
    """Chuyển tên địa điểm thành tên file an toàn (bỏ ký tự đặc biệt)."""
    if not name:
        name = fallback
    name = re.sub(r'[\\/:*?"<>|]+', "", name)  # bỏ ký tự cấm trong tên file Windows
    name = name.strip().replace(" ", "_")
    return name[:80]  # giới hạn độ dài


downloaded = 0
skipped = 0
for p in places:
    url = p.get("anh_url")
    if not url:
        skipped += 1
        continue

    # Lấy phần đuôi file gốc (.jpg, .png...) từ tên ảnh, mặc định .jpg nếu không rõ
    orig_name = p.get("anh") or ""
    ext = os.path.splitext(orig_name)[1] or ".jpg"

    filename = f"{p['id']}_{safe_filename(p.get('ten'), p['id'])}{ext}"
    filepath = os.path.join(IMAGE_DIR, filename)

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        with open(filepath, "wb") as imgf:
            imgf.write(resp.content)
        downloaded += 1
        print(f"Đã tải: {filename}")
    except Exception as e:
        print(f"Lỗi tải ảnh {p['id']} ({p.get('ten')}): {e}")
        skipped += 1

    time.sleep(0.3)  # nghỉ giữa các lần tải, tránh spam server

print(f"\nHoàn tất tải ảnh: {downloaded} thành công, {skipped} bỏ qua/lỗi.")
print(f"Ảnh được lưu trong thư mục: ./{IMAGE_DIR}/")

# In thử vài kết quả đầu để kiểm tra nhanh
for i, p in enumerate(places[:5], 1):
    print("=" * 60)
    print(i, "-", p["ten"])
    print("Địa chỉ:", p["dia_chi"])
    print("Điện thoại:", p["dien_thoai"])
    print("Link ảnh:", p["anh_url"])
    print("Tọa độ:", p["lat"], p["lng"])