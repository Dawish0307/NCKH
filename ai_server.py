from flask import Flask, request, jsonify
import pandas as pd
import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# 1. Tải mô hình AI xử lý ngôn ngữ tự nhiên (Bản nhẹ, tốc độ cao)
print("Đang khởi động bộ não AI... (Có thể mất 1-2 phút tải mô hình cho lần chạy đầu tiên)")
model = SentenceTransformer('all-MiniLM-L6-v2')

# 2. Đọc dữ liệu điểm du lịch từ file JSON
with open('diem_du_lich.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
df_diem_den = pd.DataFrame(data)

# 3. Mã hóa phần "mô tả" của tất cả các điểm đến thành Vector (Ma trận toán học)
danh_sach_mo_ta = df_diem_den['mo_ta'].tolist()
vector_diem_den = model.encode(danh_sach_mo_ta)
print("Đã học xong dữ liệu các điểm đến!")

# --- TRẠM GÁC API: NHẬN YÊU CẦU VÀ TÌM KIẾM NGỮ NGHĨA ---
@app.route('/api/search/semantic', methods=['POST'])
def semantic_search():
    # Nhận câu văn tự nhiên từ người dùng (ví dụ: "tôi muốn đi đâu đó yên tĩnh")
    yeu_cau = request.json.get('query', '')
    
    if not yeu_cau:
        return jsonify({"error": "Vui lòng nhập câu truy vấn"}), 400

    # 4. Biến câu hỏi của người dùng thành Vector
    vector_yeu_cau = model.encode([yeu_cau])
    
    # 5. AI tính toán độ tương đồng (Cosine Similarity)
    do_tuong_dong = cosine_similarity(vector_yeu_cau, vector_diem_den)[0]
    
    # Lấy ra ID của điểm đến có điểm số tương đồng cao nhất
    chi_so_tot_nhat = do_tuong_dong.argmax()
    diem_den_phu_hop = df_diem_den.iloc[chi_so_tot_nhat].to_dict()
    
    # Trả kết quả về
    return jsonify({
        "status": "success",
        "cau_hoi_nguoi_dung": yeu_cau,
        "ket_qua_goi_y": diem_den_phu_hop,
        "diem_tuong_dong": round(float(do_tuong_dong[chi_so_tot_nhat]), 4)
    })

if __name__ == '__main__':
    print("--------------------------------------------------")
    print("AI Server đã sẵn sàng trực chiến tại: http://127.0.0.1:5000")
    print("--------------------------------------------------")
    app.run(port=5000, debug=True)