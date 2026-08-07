"""
SCRAPE ẨM THỰC (gialaitourism.vn) + GỘP VỚI DỮ LIỆU DU LỊCH THÀNH 1 FILE EXCEL
================================================================================
File .csv KHÔNG có khái niệm "sheet" (đó là tính năng riêng của Excel .xlsx).
Script này sẽ:
  1. Scrape danh sách quán ăn/nhà hàng (formId 65)
  2. Đọc lại dữ liệu điểm du lịch đã scrape trước đó (gialai_places.csv)
  3. Gộp cả 2 vào 1 file .xlsx với 2 sheet: "Diem_du_lich" và "Am_thuc"

CHÚ Ý VỀ ĐỘ TIN CẬY FIELD:
  - vi_281, vi_282, vi_284, vi_285, vi_286, vi_664, vi_986, vi_524, vi_1139:
    đã XÁC NHẬN qua HAR (đặc biệt vi_986 = "Đánh giá sao" tìm thấy trong
    request bộ lọc tìm kiếm).
  - vi_1101, vi_1102, vi_1089, vi_1004, 283: KHÔNG có displayName xuất hiện
    trong HAR để xác nhận chắc chắn. Đây là suy đoán dựa trên giá trị mẫu
    (vi_1101/vi_1102 dạng số 10-20 nên đoán là giờ mở/đóng cửa). Bạn nên
    kiểm tra lại trên trang thật (xem hướng dẫn "XÁC MINH FIELD" bên dưới).
"""

import requests
import json
import csv
import time
import re
import html
import os # là thư viện chuẩn của Python, cung cấp các hàm để tương tác với hệ điều hành, như tạo thư mục, kiểm tra sự tồn tại của file, và thao tác với đường dẫn.
import pandas as pd


# ============================================================
# HÀM DÙNG CHUNG
# ============================================================

def clean_html_text(raw_html):
    if not raw_html:
        return raw_html
    text = str(raw_html)
    text = re.sub(r'data:image/[^"\']+', '[hình ảnh]', text)
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def safe_unescape(value):
    if isinstance(value, str):
        return html.unescape(value).strip()
    return value


def safe_filename(name, fallback):
    if not name:
        name = str(fallback)
    name = re.sub(r'[\\/:*?"<>|]+', "", str(name))
    return name.strip().replace(" ", "_")[:80]


BASE_URL = "https://gialaitourism.vn"
IMAGE_PREVIEW_PATH = "/headlessCms/api/public/document/preview/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": "https://gialaitourism.vn",
    "Referer": "https://gialaitourism.vn/am-thuc.html",
}

API_URL = "https://gialaitourism.vn/headlessCms/api/public/getDataSearchByKeyAndEnum"


def build_image_url(image_field):
    if not image_field or not isinstance(image_field, dict):
        return ""
    doc_id = image_field.get("id")
    return f"{BASE_URL}{IMAGE_PREVIEW_PATH}{doc_id}" if doc_id else ""


def build_gallery_urls(gallery_raw): #dùng để tạo danh sách các URL ảnh từ trường gallery_raw, trả về một chuỗi các URL được nối với nhau bằng dấu " | ".
    urls = []
    if isinstance(gallery_raw, list):
        for g in gallery_raw:
            gid = g.get("id") if isinstance(g, dict) else None
            if gid:
                urls.append(f"{BASE_URL}{IMAGE_PREVIEW_PATH}{gid}")
    return " | ".join(urls)


# ============================================================
# 1. SCRAPE DANH SÁCH ẨM THỰC (formId 65)
# ============================================================

def scrape_am_thuc():
    print("SCRAPE ẨM THỰC (quán ăn / nhà hàng)")

    page = 1
    page_size = 12
    all_raw = []

    while True:
        payload = [{
            "formId": 65, # formId 65 là mã định danh cho loại dữ liệu "Ẩm thực" (quán ăn/nhà hàng) trên trang gialaitourism.vn. 
                            #Khi gửi request đến API, formId này giúp hệ thống biết rằng bạn muốn truy xuất dữ liệu liên quan đến quán ăn/nhà hàng.
            "list_data_search": [],
            "key_search": "",
            "localization": "vi",
            "pagination": {"currentPage": page, "pageSize": page_size},
            "trang_thai": 1,
            "pageBuilderOptionid": 31741,
        }]
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status() # raise_for_status() là một phương thức của đối tượng Response trong thư viện requests của Python.
                            # Khi bạn gọi phương thức này, nó sẽ kiểm tra mã trạng thái HTTP của phản hồi từ server. 
                            # Nếu mã trạng thái là 4xx (lỗi phía client) hoặc 5xx (lỗi phía server), phương thức sẽ ném ra một ngoại lệ HTTPError, 
                            # giúp bạn dễ dàng phát hiện và xử lý các lỗi trong quá trình gửi request.
        result = r.json()["result"][0] # result = r.json()["result"][0] là một dòng mã trong Python sử dụng thư viện requests để xử lý phản hồi JSON từ một API.
                                        # Cụ thể, r.json() chuyển đổi phản hồi JSON từ server thành một đối tượng Python (thường là dict hoặc list).
                                        # ["result"] truy cập vào khóa "result" trong đối tượng JSON, và [0] lấy phần tử đầu tiên của danh sách kết quả.
        data = result["data"]
        if not data:
            break
        all_raw.extend(data) # lệnh extend() thêm tất cả các phần tử từ danh sách data vào cuối danh sách all_raw.
        total = result["pagination"]["total"] # pagination và total là các thông tin về phân trang (pagination) trong phản hồi JSON từ API. 
                                              # pagination và total ở trong result["pagination"]["total"] cung cấp tổng số bản ghi (total) có sẵn trên server, giúp bạn biết được có bao nhiêu quán ăn/nhà hàng trong cơ sở dữ liệu.
        print(f"  Trang {page}: {len(all_raw)}/{total}")
        if len(all_raw) >= total:
            break
        page += 1
        time.sleep(0.5)
        # dữ liệu trong all_raw sẽ được lưu trữ trong một danh sách Python, mỗi phần tử của danh sách là một dictionary chứa thông tin chi tiết về một quán ăn/nhà hàng, bao gồm các trường như tên, địa chỉ, điện thoại, email, tọa độ (lat/lng), tên file ảnh gốc và link ảnh thật.
        
    print(f"Tổng số quán ăn/nhà hàng: {len(all_raw)}")

    records = []
    for item in all_raw:
        d = item.get("data_formbuilder", {})
        coord = d.get("vi_286") or {}
        image_field = d.get("vi_664") or {}
        gallery_urls = build_gallery_urls(d.get("vi_1139"))

        records.append({
            "id": item.get("id"),
            "ten": safe_unescape(d.get("vi_281")),
            "dia_chi": safe_unescape(d.get("vi_282")),
            "website": safe_unescape(d.get("vi_283")),          # chưa xác nhận 100%
            "dien_thoai": safe_unescape(d.get("vi_284")),
            "email": safe_unescape(d.get("vi_285")),
            "gia_trung_binh_vnd": d.get("vi_524"),                # xem lưu ý ở đầu file
            "danh_gia_sao": d.get("vi_986"),                      # XÁC NHẬN: "Đánh giá sao"
            "gio_dong_cua_uoc_tinh": d.get("vi_1101"),            # suy đoán, cần kiểm tra lại
            "gio_mo_cua_uoc_tinh": d.get("vi_1102"),              # suy đoán, cần kiểm tra lại
            "field_1089_raw": d.get("vi_1089"),                   # chưa rõ ý nghĩa
            "field_1004_raw": d.get("vi_1004"),                   # chưa rõ ý nghĩa
            "lat": coord.get("lat"),
            "lng": coord.get("lng"),
            "anh": image_field.get("value"),
            "anh_url": build_image_url(image_field),
            "anh_phu_urls": gallery_urls,
        })

    return records


# ============================================================
# 2. TẢI ẢNH VỀ THƯ MỤC RIÊNG
# ============================================================

def download_images(records, image_dir):
    os.makedirs(image_dir, exist_ok=True) #os.makedirs là một hàm trong thư viện os của Python, 
                                          #được sử dụng để tạo một thư mục mới. 
                                          # Tham số image_dir là đường dẫn đến thư mục cần tạo. 
                                          # Tham số exist_ok=True cho phép bỏ qua lỗi nếu thư mục đã tồn tại, 
                                          # nghĩa là nếu thư mục đã tồn tại, hàm sẽ không gây ra lỗi và tiếp tục thực hiện các lệnh tiếp theo.
    downloaded = 0
    for rec in records:
        url = rec.get("anh_url")
        if not url:
            continue
        ext = os.path.splitext(rec.get("anh") or "")[1] or ".jpg"
        filename = f"{rec['id']}_{safe_filename(rec.get('ten'), rec['id'])}{ext}"
        filepath = os.path.join(image_dir, filename)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            downloaded += 1
        except Exception as e:
            print(f"  Lỗi tải ảnh {rec['id']}: {e}")
        time.sleep(0.3)
    print(f"Đã tải {downloaded} ảnh vào ./{image_dir}/")





# ============================================================
# 3. CHẠY SCRAPE + GHÉP VÀO 1 FILE EXCEL NHIỀU SHEET
# ============================================================

if __name__ == "__main__":
    # --- Bước 1: scrape ẩm thực ---
    am_thuc_records = scrape_am_thuc()

    with open("gialai_am_thuc.json", "w", encoding="utf-8") as f:
        json.dump(am_thuc_records, f, ensure_ascii=False, indent=2)

    # Tạo một file giaLai_am_thuc.csv chứa dữ liệu quán ăn/nhà hàng
    csv_fields = [k for k in am_thuc_records[0].keys() if k != "_mo_ta_raw_html"] # lệnh này tạo ra một danh sách các trường (field) để lưu vào file CSV, loại bỏ trường "_mo_ta_raw_html" vì nó chứa dữ liệu mô tả gốc (raw HTML) có thể gây lỗi khi xuất ra CSV/XLSX.

    with open("gialai_am_thuc.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(am_thuc_records)
        
    print("Đã lưu: gialai_am_thuc.csv")

    download_images(am_thuc_records, "images_am_thuc")

    df_am_thuc = pd.DataFrame(am_thuc_records)

    # --- Bước 2: đọc lại dữ liệu điểm du lịch đã scrape trước đó ---
    # (Đổi đường dẫn nếu file của bạn nằm chỗ khác)
    diem_du_lich_csv = "gialai_places.csv"
    if os.path.exists(diem_du_lich_csv):
        df_diem_du_lich = pd.read_csv(diem_du_lich_csv, encoding="utf-8-sig") #read_csv là một hàm trong thư viện pandas của Python, 
                                                                                #được sử dụng để đọc dữ liệu từ một tệp CSV (Comma-Separated Values) 
                                                                                # và chuyển đổi nó thành một DataFrame của pandas.
                                                                                # Lệnh encoding="utf-8-sig" được sử dụng để đảm bảo rằng tệp CSV được đọc với mã hóa UTF-8,
                                                                                # bao gồm cả ký tự BOM (Byte Order Mark) nếu có.
    else:
        print(f"CẢNH BÁO: không tìm thấy {diem_du_lich_csv}, sheet Diem_du_lich sẽ để trống.")
        df_diem_du_lich = pd.DataFrame()

    # --- Bước 3: ghi cả 2 bảng vào 1 file .xlsx, mỗi bảng 1 sheet ---
    output_path = "gialai_du_lich_va_am_thuc.xlsx"
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        if not df_diem_du_lich.empty:
            df_diem_du_lich.to_excel(writer, sheet_name="Diem_du_lich", index=False)
        df_am_thuc.to_excel(writer, sheet_name="Am_thuc", index=False)

    print(f"\nĐÃ TẠO FILE: {output_path}")
    print("  - Sheet 'Diem_du_lich': dữ liệu điểm du lịch")
    print("  - Sheet 'Am_thuc'     : dữ liệu quán ăn/nhà hàng")


# ============================================================
# XÁC MINH LẠI CÁC FIELD CHƯA CHẮC CHẮN (vi_1101, vi_1102, vi_1089, vi_1004, 283)
# ============================================================
"""
Cách xác minh chính xác 100% ý nghĩa 1 field code (ví dụ vi_1101):

1. Mở trang https://gialaitourism.vn/am-thuc.html trên Chrome
2. Mở DevTools (F12) > tab Network > lọc "Fetch/XHR"
3. Bấm vào 1 quán ăn bất kỳ để xem trang chi tiết của nó
4. Tìm request nào trả về đúng object có chứa "vi_1101" trong response
5. Nếu trang có ô lọc/bộ lọc (như "Giờ mở cửa", "Wifi miễn phí"...) và bạn
   thao tác vào ô lọc đó, request gửi đi thường sẽ có "displayName" đi kèm
   field code tương ứng - đây CHÍNH LÀ CÁCH tôi xác nhận vi_986 = "Đánh giá sao".
6. Xuất lại file .har mới (Network tab > chuột phải > "Save all as HAR")
   sau khi đã thao tác vào các bộ lọc đó, rồi gửi lại cho tôi để tôi đọc
   chính xác thay vì suy đoán.
"""