# LLM Judge Bias Report — Phase B

**Sinh viên:** Lâm — MSSV 2A202600555
**Ngày:** 30/06/2026
**Judge model:** gpt-4o-mini

---

## Phương pháp

- **Cohen's κ:** dùng `single_answer_judge()` chấm trực tiếp từng `model_answer` (trong `human_labels_10q.json`)
  là TỐT (1) hay XẤU (0) bằng cách **đối chiếu ground_truth** lấy từ `test_set_50q.json`, rồi so với `human_label`.
- **Pairwise / bias:** `swap_and_average()` so `model_answer` (A) với `ground_truth` (B) — chạy 2 lượt đảo thứ tự.

> Lưu ý: cách cũ (so model_answer với câu giả "sai hoàn toàn") khiến judge luôn chọn A → mọi nhãn = 1 → **κ = 0**.
> Cách mới có tham chiếu thực nên judge phân biệt được đúng/sai → **κ = 0.80**.

---

## 1. Cohen's κ Analysis

**Human labels:** 10 câu (6 label=1, 4 label=0) · **Judge labels:** sinh từ `single_answer_judge`

| Question ID | Human Label | Judge Label | Agree? |
|---|---|---|---|
| 1  | 1 | 1 | Yes |
| 5  | 0 | 0 | Yes |
| 12 | 1 | 0 | **No** |
| 21 | 1 | 1 | Yes |
| 23 | 1 | 1 | Yes |
| 29 | 0 | 0 | Yes |
| 33 | 1 | 1 | Yes |
| 41 | 0 | 0 | Yes |
| 46 | 1 | 1 | Yes |
| 50 | 0 | 0 | Yes |

**Agreement:** 9/10 · **Cohen's κ = 0.800** → *substantial → almost perfect* (Landis-Koch).
Vượt ngưỡng bonus κ > 0.6 ✅. Câu lệch duy nhất là **id12** (Thưởng Tết): human cho là đạt, judge chấm chưa đạt do model_answer thiếu điều kiện "≥6 tháng" có trong ground_truth.

---

## 2. Pairwise Swap-and-Average (model_answer vs ground_truth)

| ID | Final winner | Position consistent? |
|---|---|---|
| 1, 5, 21, 23, 29, 33, 41, 50 | B (ground_truth) | True |
| 12 | B (ground_truth) | True |
| 46 | tie | **False** |

Ground_truth (B) thắng ở 9/10 case (hợp lý — đây là đáp án chuẩn). id46 cho kết quả không nhất quán giữa 2 lượt → final = tie.

---

## 3. Position Bias

- Số case không nhất quán khi đảo thứ tự: **1/10** → **position_bias_rate = 0.10**
- Diễn giải: bias thấp (<0.3) → judge khá ổn định, ít bị ảnh hưởng bởi vị trí A/B. Swap-and-average đã "bắt" được 1 case (id46) và hạ nó về tie thay vì kết luận sai.

---

## 4. Verbosity Bias

Trong 9 case có winner rõ ràng (loại tie):
- A (model_answer) thắng VÀ dài hơn: **0 / 9**
- B (ground_truth) thắng VÀ dài hơn: **9 / 9**
- **Verbosity bias rate = 1.00**

**Diễn giải:** con số 1.0 ở đây là **artefact của thiết kế đo** (B luôn là ground_truth — vừa đúng hơn vừa đầy đủ/dài hơn), KHÔNG có nghĩa judge mù quáng chọn câu dài. Để đo verbosity bias "sạch" cần các cặp answer **xấp xỉ chất lượng nhưng khác độ dài**. Dù vậy, nó nhắc một rủi ro thật trong production: LLM judge có thể ưu ái câu dài/hoa mỹ — cần kiểm soát bằng tiêu chí súc tích rõ ràng trong prompt.

---

## 5. Nhận xét chung

> - **κ = 0.80** cho thấy LLM judge (gpt-4o-mini) đồng thuận cao với con người **khi được cung cấp ground_truth** làm mỏ neo. Không có tham chiếu, judge dễ thiên về "câu nào nghe hợp lý hơn".
> - **Position bias 10%** — thấp; swap-and-average vẫn cần thiết để loại các case mơ hồ (như id46).
> - **Verbosity bias** đo trong lab bị nhiễu bởi thiết kế; production nên đo trên cặp answer cân bằng độ dài.
> - Khuyến nghị production: LLM judge + ground_truth/rubric + swap-and-average + giám sát định kỳ bằng human annotation; theo dõi κ theo thời gian để phát hiện drift.
