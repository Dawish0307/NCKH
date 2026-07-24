import requests
import json

# Địa chỉ trạm gác AI của bạn
url = 'http://localhost:5000/api/search/semantic'

# Đóng vai người dùng nhập câu tìm kiếm bằng văn xuôi tự nhiên trên thanh tìm kiếm của web
payload = {
    "query": "Tôi muốn đến một nơi nào đó có công viên bảo tồn."
}

print(f"Khách hàng tìm kiếm: '{payload['query']}'")
print("Đang gửi yêu cầu đến Trạm gác AI...\n")

# Gửi yêu cầu
response = requests.post(url, json=payload)


# In kết quả AI trả về ra màn hình
print("==== KẾT QUẢ AI GỢI Ý ====")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))