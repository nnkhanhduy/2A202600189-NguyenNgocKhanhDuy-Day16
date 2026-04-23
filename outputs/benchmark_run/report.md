# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_100.json
- Mode: groq
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.81 | 0.99 | 0.18 |
| Avg attempts | 1 | 1.21 | 0.21 |
| Avg token estimate | 1882.3 | 2567.54 | 685.24 |
| Avg latency (ms) | 19604.66 | 25760.47 | 6155.81 |

## Failure modes
```json
{
  "react": {
    "none": 81,
    "wrong_final_answer": 19
  },
  "reflexion": {
    "none": 99,
    "wrong_final_answer": 1
  },
  "combined": {
    "none": 180,
    "wrong_final_answer": 20
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- actual_token_tracking

## Discussion
Cơ chế Reflexion đã chứng minh được hiệu quả vượt trội trong việc xử lý các câu hỏi phức tạp của HotpotQA, đặc biệt là các trường hợp 'multi-hop reasoning' nơi Agent thường dừng lại sau bước suy luận đầu tiên hoặc bị 'entity drift'. Bằng cách sử dụng vòng lặp suy ngẫm, Agent có khả năng tự nhận diện các thông tin còn thiếu (missing evidence) đã được chỉ ra bởi Evaluator để điều chỉnh chiến thuật tìm kiếm trong context ở các lượt thử tiếp theo. Tuy nhiên, sự cải thiện về độ chính xác (Exact Match) đi kèm với chi phí đáng kể về lượng token tiêu thụ và độ trễ hệ thống, do mỗi lượt suy ngẫm yêu cầu thêm các lần gọi LLM cho cả Reflector và Actor. Trong thực tế, việc tối ưu hóa chất lượng của Evaluator là yếu tố sống còn; nếu Evaluator đưa ra phản hồi sai, Reflexion có thể dẫn đến hiện tượng 'overfitting' vào những bài học không chính xác, làm giảm hiệu suất tổng thể.
