# Failure Cluster Analysis — Phase A

**Sinh viên:** Lâm — MSSV 2A202600555
**Ngày:** 30/06/2026

---

## 1. Aggregate RAGAS Scores theo Distribution

| Metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 0.883 | 0.639 | 0.700 |
| answer_relevancy | 0.803 | 0.744 | 0.506 |
| context_precision | 0.971 | 0.904 | 0.967 |
| context_recall | 0.950 | 0.804 | 0.683 |
| **avg_score** | **0.902** | **0.773** | **0.714** |

→ avg_score giảm dần factual > multi_hop > adversarial — đúng kỳ vọng: câu càng "bẫy" pipeline càng yếu.

---

## 2. Bottom 10 Questions

| Rank | Distribution | Question | avg_score | worst_metric |
|---|---|---|---|---|
| 1 | multi_hop | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 | 0.000 | faithfulness |
| 2 | multi_hop | Nhân viên Manager thâm niên 12 năm: tổng phụ cấp… | 0.271 | faithfulness |
| 3 | adversarial | Bao lâu phải đổi mật khẩu một lần? | 0.375 | faithfulness |
| 4 | adversarial | Mật khẩu phải có tối thiểu bao nhiêu ký tự? | 0.417 | faithfulness |
| 5 | adversarial | Nhân viên Manager có thể dùng VPN cá nhân (NordVPN…)? | 0.417 | faithfulness |
| 6 | factual | Nam nhân viên được nghỉ bao nhiêu ngày khi vợ sinh? | 0.500 | faithfulness |
| 7 | factual | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | 0.598 | faithfulness |
| 8 | adversarial | Nhân viên thử việc có được hưởng bảo hiểm sức khỏe? | 0.667 | answer_relevancy |
| 9 | multi_hop | Nếu cần mua laptop 30 triệu cho nhân viên… | 0.714 | context_recall |
| 10 | multi_hop | Nhân viên Senior 9 năm thâm niên được nghỉ bao nhiêu phép… | 0.735 | context_recall |

---

## 3. Failure Cluster Matrix

*(Mỗi ô = số câu có worst_metric = row, thuộc distribution = col)*

| worst_metric | factual | multi_hop | adversarial | Total |
|---|---|---|---|---|
| faithfulness | 3 | 10 | 3 | 16 |
| answer_relevancy | 15 | 5 | 2 | 22 |
| context_precision | 0 | 0 | 0 | 0 |
| context_recall | 2 | 5 | 5 | 12 |

---

## 4. Dominant Failure Analysis

**Dominant distribution:** factual (20 lỗi — đồng hạng với multi_hop 20; do mỗi câu luôn có 1 worst_metric nên cột = số câu của distribution. Xét theo avg_score thì **adversarial** mới là yếu nhất.)
**Dominant metric:** answer_relevancy (22/50 câu có đây là metric kém nhất)

**Lý do phân tích:**

> answer_relevancy thấp chủ yếu ở factual (15 câu) là do bộ generator (gpt-4o-mini) trả lời hơi lan man / thêm thông tin thừa ngoài trọng tâm câu hỏi, dù context_precision và context_recall của factual rất cao (0.97 / 0.95) — tức retrieval tốt nhưng câu trả lời chưa "đúng trọng tâm". Ở multi_hop, faithfulness là điểm yếu (10 câu) vì pipeline phải kết hợp nhiều tài liệu + tính toán (lương, phụ cấp, ngày phép) nên dễ suy luận sai/bịa số. context_precision = 0 lỗi trên toàn corpus → khâu rerank (M3) lọc context rất sạch.

---

## 5. Suggested Fixes

| Metric yếu | Root cause | Suggested fix |
|---|---|---|
| faithfulness | LLM hallucinating khi multi-hop/tính toán | Siết system prompt ("chỉ dùng số có trong context"), giảm temperature, thêm bước verify số liệu |
| context_recall | Thiếu chunk liên quan ở multi_hop/adversarial | Tăng top-k trước rerank, thêm BM25 cho truy vấn có số/định danh phiên bản |
| context_precision | (không phải vấn đề — 0 lỗi) | Giữ nguyên rerank M3 |
| answer_relevancy | Câu trả lời lan man, lệch trọng tâm (factual) | Cải thiện prompt template: yêu cầu trả lời ngắn, đúng trọng tâm; few-shot |

---

## 6. Nhận xét về Adversarial Distribution

> Adversarial có avg_score = 0.714 — **thấp nhất** trong 3 distribution (factual 0.902, multi_hop 0.773), đúng như thiết kế "bẫy". 4/10 câu trong bottom-10 là adversarial (#3, #4, #5, #8). Các câu này chủ yếu liên quan mật khẩu (v1.0 vs v2.0) và VPN cá nhân — pipeline bị nhầm giữa các phiên bản policy (faithfulness thấp 0.700) và trả lời lệch trọng tâm với câu phủ định/bẫy (answer_relevancy chỉ 0.506, thấp nhất toàn bộ). Đáng chú ý câu #1 (multi_hop so sánh mật khẩu v1.0/v2.0) đạt avg=0.000 — pipeline không phân biệt được 2 phiên bản. Đây là bằng chứng cho thấy cần **metadata filter theo version** để pipeline chọn đúng phiên bản policy.
