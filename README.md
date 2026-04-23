# Lab 16 — Reflexion Agent Scaffold

Repo này xây dựng và đánh giá **Reflexion Agent** — một kiến trúc agent tự cải thiện thông qua vòng lặp phản chiếu (reflection loop) trên bộ dữ liệu multi-hop QA (HotpotQA).

---

## 1. Những gì đã thực hiện

### 1.1 Tích hợp LLM thật (Groq API)

Thay thế toàn bộ phần mock trong `mock_runtime.py` bằng gọi API thật tới **Groq** (model `llama-3.1-8b-instant`):

- Kết nối Groq API với xác thực qua `GROQ_API_KEY` trong file `.env`
- Thêm retry logic với exponential backoff để xử lý rate limit
- **Tính toán token thực tế**: trích xuất `total_tokens` trực tiếp từ response của API thay vì dùng số ước tính

### 1.2 Xây dựng Reflexion Agent hoàn chỉnh

Triển khai đầy đủ vòng lặp Actor → Evaluator → Reflector trong `agents.py`:

| Bước | Mô tả |
|------|-------|
| **Actor** | Sinh câu trả lời dựa trên câu hỏi, context và bộ nhớ phản chiếu tích lũy |
| **Evaluator** | Đánh giá câu trả lời đúng/sai (trả về JSON có score 0/1 + lý do) |
| **Reflector** | Khi sai: phân tích nguyên nhân, rút ra bài học, đề xuất chiến lược cho lần thử tiếp theo |
| **Memory** | Các phản chiếu được lưu vào bộ nhớ và đưa vào prompt của lần thử sau |

### 1.3 Các phần Bonus đã triển khai

| Extension | Mô tả |
|-----------|-------|
| `structured_evaluator` | Evaluator trả về JSON có cấu trúc đầy đủ (score, reason, missing_evidence, spurious_claims) |
| `reflection_memory` | Bộ nhớ phản chiếu tích lũy qua các lần thử, được đưa vào actor prompt |
| `benchmark_report_json` | Xuất báo cáo JSON đầy đủ với metadata, metrics, failure modes và discussion |
| `actual_token_tracking` | Theo dõi token thực tế từ API response thay vì ước tính |

### 1.4 Chạy benchmark thực tế

- Chạy trên **100 mẫu** từ bộ dữ liệu HotpotQA (`data/hotpot_100.json`)
- So sánh hai kiến trúc: **ReAct** (baseline) vs **Reflexion** (tối đa 3 lần thử)
- Kết quả được lưu tại `outputs/benchmark_run/`

---

## 2. Kết quả đạt được

### Tóm tắt hiệu năng

| Chỉ số | ReAct | Reflexion | Thay đổi |
|--------|-------|-----------|---------|
| **Độ chính xác (EM)** | 81% | 99% | **+18%** |
| **Số lần thử trung bình** | 1.00 | 1.21 | +0.21 |
| **Token trung bình** | 1,882 | 2,567 | +685 |
| **Latency trung bình** | 19.6s | 25.8s | +6.2s |

### Phân tích

- **Reflexion cải thiện đáng kể độ chính xác** (+18%) chỉ với chi phí tăng nhẹ về token (+36%) và latency (+32%)
- **Phần lớn cải thiện đến từ lần thử thứ 2**: agent phân tích lý do sai và điều chỉnh chiến lược trả lời
- **Reflexion không hoàn hảo**: 1 câu hỏi vẫn sai sau 3 lần thử do context không đủ thông tin
- **Rủi ro evaluator bias**: đôi khi evaluator chấp nhận câu trả lời gần đúng nhưng không khớp hoàn toàn với gold answer

### Kết quả chi tiết

```
ReAct:      81/100 đúng,  19/100 sai
Reflexion:  99/100 đúng,   1/100 sai
```

Báo cáo đầy đủ tại [`outputs/benchmark_run/report.md`](outputs/benchmark_run/report.md) và [`outputs/benchmark_run/report.json`](outputs/benchmark_run/report.json).

---

## 3. Cách chạy

### Yêu cầu

- Python 3.9+
- Tài khoản [Groq](https://console.groq.com/) (miễn phí) để lấy API key

### Cài đặt môi trường

```bash
# Tạo và kích hoạt môi trường ảo
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### Cấu hình API key

Tạo file `.env` ở thư mục gốc:

```
GROQ_API_KEY=your_groq_api_key_here
```

### Chạy benchmark

```bash
# Chạy đầy đủ trên 100 mẫu (khuyến nghị)
python run_benchmark.py --dataset data/hotpot_100.json --out-dir outputs/benchmark_run

# Chạy thử nhanh trên 2 mẫu
python run_benchmark.py --dataset data/hotpot_mini.json --out-dir outputs/test_run

# Tùy chỉnh số lần thử tối đa của Reflexion
python run_benchmark.py --dataset data/hotpot_100.json --out-dir outputs/benchmark_run --reflexion-attempts 5
```

### Chấm điểm tự động

```bash
python autograde.py --report-path outputs/benchmark_run/report.json
```

---

## 4. Cấu trúc dự án

```
phase1-track3-lab1-advanced-agent/
├── src/reflexion_lab/
│   ├── agents.py          # ReActAgent và ReflexionAgent (vòng lặp Actor→Evaluator→Reflector)
│   ├── schemas.py         # Các kiểu dữ liệu Pydantic (RunRecord, AttemptTrace, ...)
│   ├── prompts.py         # System prompt cho Actor, Evaluator, Reflector
│   ├── mock_runtime.py    # Runtime LLM (đã tích hợp Groq API thật)
│   ├── reporting.py       # Tạo báo cáo JSON và Markdown
│   └── utils.py           # Tiện ích: normalize_answer, load_dataset, save_jsonl
├── data/
│   ├── hotpot_mini.json   # 2 mẫu để test nhanh
│   └── hotpot_100.json    # 100 mẫu HotpotQA để chạy benchmark
├── outputs/benchmark_run/ # Kết quả benchmark (được tạo tự động)
│   ├── react_runs.jsonl
│   ├── reflexion_runs.jsonl
│   ├── report.json
│   └── report.md
├── run_benchmark.py       # Script chính
├── autograde.py           # Công cụ chấm điểm tự động
├── requirements.txt
└── .env                   # GROQ_API_KEY (không commit lên git)
```
