# Kế hoạch triển khai — Lab 24: Production Eval + Guardrail Stack

> Tài liệu lập kế hoạch chi tiết cho việc hoàn thành Lab 24 (Track 3).
> Mục tiêu: 100 điểm + 10 bonus. Tổng thời gian code: ~90 phút (3 phase × 30') + 15' setup.

---

## 0. Bức tranh tổng thể & trạng thái hiện tại

```
[Day 18 Pipeline]  →  Phase A: RAGAS 50q   →  reports/ragas_50q.json
                   →  Phase B: LLM Judge    →  reports/judge_results.json
                   →  Phase C: NeMo Guard   →  reports/guard_results.json + blueprint.md
```

**Cần code (3 file, 13 task):**
- [src/phase_a_ragas.py](src/phase_a_ragas.py) — Task 1–4 (30đ)
- [src/phase_b_judge.py](src/phase_b_judge.py) — Task 5–8 (35đ)
- [src/phase_c_guard.py](src/phase_c_guard.py) — Task 9–12 (35đ)
- [reports/blueprint.md](reports/blueprint.md) — Task 13 (điền tay, đánh giá riêng)

**Đã có sẵn (không cần sửa, trừ khi tối ưu):**
- `config.py`, `setup_answers.py`, `check_lab.py`, `naive_baseline.py`
- `guardrails/config.yml` + `guardrails/rails.co` (Colang flows — **có thể mở rộng** để tăng pass rate)
- Data: `test_set_50q.json` (50 câu), `human_labels_10q.json` (10 nhãn), `adversarial_set_20.json` (20 input)
- Tests: `tests/test_phase_{a,b,c}.py`

> **Quan sát quan trọng về scaffold:** mỗi task đều có code mẫu đầy đủ trong block comment (`# TODO`).
> Phần lớn việc là **bỏ comment + ráp lại + kiểm chứng**, không phải viết từ đầu. Đây là điểm mấu chốt giúp hoàn thành nhanh.

### ✅ Blocker tiên quyết — ĐÃ XỬ LÝ

~~`src/` thiếu toàn bộ Day 18.~~ **Cập nhật:** 6 file Day 18 đã được copy vào `src/`:
`m1_chunking.py, m2_search.py, m3_rerank.py, m4_eval.py, m5_enrichment.py, pipeline.py`.

Đã xác minh `src/m4_eval.py` → `evaluate_ragas()` **implement xong** và **tương thích Phase A**:
trả về dict có `per_question` = list `EvalResult` với đủ 4 field `faithfulness/answer_relevancy/context_precision/context_recall`
→ Task 2 (`run_ragas_50q`) zip trực tiếp sang `RagasResult` được, không cần chỉnh.

**Việc còn lại của setup (chưa xong):** `answers_50q.json` **vẫn chưa được generate** → phải chạy
`python setup_answers.py` (cần Qdrant + spaCy model + `.env` có API key). Đây là input bắt buộc của Phase A.

---

## 1. SETUP (15 phút — làm TRƯỚC khi tính giờ)

| # | Việc | Lệnh | Trạng thái / Kiểm chứng |
|---|---|---|---|
| 1 | Copy Day 18 | `cp <Day18>/src/m*.py src/ && cp <Day18>/src/pipeline.py src/` | ✅ **XONG** — đủ 6 file, `evaluate_ragas()` đã verify tương thích |
| 2 | Khởi động Qdrant | `docker compose up -d` | ⬜ `docker ps` thấy container, port 6333 |
| 3 | Cài deps | `pip install -r requirements.txt` | ⬜ không lỗi |
| 4 | spaCy model | `python -m spacy download en_core_web_lg` | ⬜ bắt buộc cho Presidio |
| 5 | API key | `cp .env.example .env` → điền `OPENAI_API_KEY` | ⬜ `python -c "from config import OPENAI_API_KEY; print(bool(OPENAI_API_KEY))"` → True |
| 6 | **Generate answers** | `python setup_answers.py` (5–10') | ⬜ **← VIỆC TIẾP THEO**; tạo `answers_50q.json` (50 phần tử) |

**Lưu ý môi trường (Windows):** shell mặc định là PowerShell. Nếu gặp `UnicodeEncodeError` khi in tiếng Việt, set `PYTHONIOENCODING=utf-8`. File JSON đều đọc/ghi với `encoding="utf-8"` — giữ nguyên.

**Định nghĩa "Done" của Setup:** `answers_50q.json` tồn tại, mỗi phần tử có keys `id, distribution, question, answer, contexts, ground_truth`.

---

## 2. PHASE A — RAGAS Production Eval (30', 30đ + 4 bonus)

**File:** [src/phase_a_ragas.py](src/phase_a_ragas.py) · **Test:** `pytest tests/test_phase_a.py -v`

Dataclass `RagasResult` + `save_phase_a_report()` đã có sẵn. Chỉ cần điền 4 hàm.

| Task | Hàm | Điểm | Cách làm | Pass criteria (test/rubric) |
|---|---|---|---|---|
| 1 | `group_by_distribution()` | 5 | Tạo dict 3 key `{factual, multi_hop, adversarial}`, loop `test_set`, append theo `item["distribution"]` | đúng 3 key, count **20/20/10**, tổng 50 |
| 2 | `run_ragas_50q()` | 10 | `from src.m4_eval import evaluate_ragas`; trích `questions/answers/contexts/ground_truths` từ `answers`; gọi `evaluate_ragas()`; zip `per_question` → list `RagasResult` (giữ `id`, `distribution`) | trả về **50** `RagasResult`, mỗi câu đủ 4 metric |
| 3 | `bottom_10()` | 7 | sort tăng dần theo `avg_score`, lấy 10; mỗi item map `worst_metric → DIAGNOSTIC_TREE` để có `diagnosis` + `suggested_fix` | đủ keys `{rank, question_id, distribution, question, avg_score, worst_metric, diagnosis, suggested_fix}`; sort tăng dần; `rank` bắt đầu từ 1 |
| 4 | `cluster_analysis()` | 8 | Matrix 4 metric × 3 dist (đếm `worst_metric` theo dist); tìm `dominant_failure_distribution` + `dominant_failure_metric`; build `insight` string | có `matrix` (4 metric key), có `insight` không rỗng |

**Triển khai:** với cả 4 task, code mẫu trong comment của scaffold là **đúng và đủ** — bỏ comment, xóa dòng `return {...}` placeholder.

**Chạy & xuất:** `python src/phase_a_ragas.py` → in bottom-10 + dominant failure, ghi `reports/ragas_50q.json`.

**Bonus A (+4):** `adversarial` có `avg_score` < `factual` (pipeline phát hiện được version-conflict v2023/v2024). Đọc số trong `per_distribution` của report để xác nhận.

**📄 Deliverable phân tích:** điền [analysis/failure_clusters.md](analysis/failure_clusters.md) dựa trên `bottom_10` + `cluster_analysis` (cụm lỗi chủ đạo, metric yếu nhất, hướng fix).

---

## 3. PHASE B — LLM-as-Judge (30', 35đ + 3 bonus)

**File:** [src/phase_b_judge.py](src/phase_b_judge.py) · **Test:** `pytest tests/test_phase_b.py -v`

Dataclass `JudgeResult` đã có sẵn. Điền 4 hàm.

| Task | Hàm | Điểm | Cách làm | Pass criteria |
|---|---|---|---|---|
| 5 | `pairwise_judge()` | 10 | Gọi OpenAI `JUDGE_MODEL` (gpt-4o-mini) với `response_format={"type":"json_object"}`; prompt yêu cầu chọn A/B/tie + reasoning + scores; `json.loads` kết quả | trả dict có `winner ∈ {A,B,tie}`, `reasoning`, `scores` (mỗi score ∈ [0,1]); reasoning không rỗng khi có winner |
| 6 | `swap_and_average()` | 10 | Pass1 `judge(q,A,B)`; Pass2 `judge(q,B,A)` (SWAP); convert pass2 về không gian gốc bằng `{A:B, B:A, tie:tie}`; consensus = winner nếu 2 pass khớp, ngược lại `tie`; set `position_consistent` | trả `JudgeResult`; 3 winner field hợp lệ; `position_consistent` là bool; khi 2 pass khác nhau → `False` |
| 7 | `cohen_kappa()` | 10 | Dùng `sklearn.metrics.cohen_kappa_score` **hoặc** công thức tay (p_o, p_e). ⚠️ `requirements.txt` chỉ có `scipy`, **không có sklearn** → ưu tiên **công thức tay** (an toàn) | perfect agreement → 1.0; perfect disagreement → ≤0; giá trị ∈ [-1,1] |
| 8 | `bias_report()` | 5 | `position_bias_rate` = tỉ lệ `position_consistent=False`; `verbosity_bias` = (A thắng & A dài hơn + B thắng & B dài hơn) / số case decisive; build `interpretation` | đủ keys `{total_judged, position_bias_rate, verbosity_bias, position_bias_count, interpretation}`; rate ∈ [0,1]; input rỗng → `total_judged=0` |

**Lưu ý Task 7 (quan trọng):** không cài sklearn → **viết tay** Cohen's κ:
```
n   = len(labels)
p_o = số cặp khớp / n
p_e = P(judge=1)·P(human=1) + P(judge=0)·P(human=0)
κ   = (p_o - p_e) / (1 - p_e)   # nếu p_e == 1 → trả 0
```
Test `test_cohen_kappa_perfect_agreement` yêu cầu `labels` giống hệt → κ=1.0 → công thức tay xử lý đúng.

**Pipeline tạo `judge_labels` cho κ:** với 10 câu trong `human_labels_10q.json` (có `model_answer`, `human_label`), chạy judge để sinh nhãn 0/1 (vd: so `model_answer` với `ground_truth`/baseline, hoặc dùng score threshold của pairwise) rồi đối chiếu `human_label`. Đây là mấu chốt để đạt **Bonus B: κ > 0.6**.

**Chạy & xuất:** `python src/phase_b_judge.py`. **Cần bổ sung logic ghi `reports/judge_results.json`** — scaffold main chỉ in ra màn hình; phải tự thêm `json.dump` (kết quả judge + bias_report + kappa) để thỏa checklist `check_lab.py`.

**📄 Deliverable phân tích:** điền [analysis/bias_report.md](analysis/bias_report.md) (position bias %, verbosity bias, κ, nhận định độ tin cậy của judge).

---

## 4. PHASE C — NeMo Guardrails (30', 35đ + 3 bonus + Task 13)

**File:** [src/phase_c_guard.py](src/phase_c_guard.py) · **Test:** `pytest tests/test_phase_c.py -v`

`setup_presidio()` (custom VN_CCCD + VN_PHONE) và `setup_nemo_rails()` đã có sẵn. Điền 5 hàm.

| Task | Hàm | Điểm | Cách làm | Pass criteria |
|---|---|---|---|---|
| 9a | `pii_scan()` | 10 | `analyzer.analyze(text, language=PRESIDIO_LANGUAGE)`; nếu rỗng → `has_pii=False`; ngược lại `anonymizer.anonymize` + build `entities` | detect `VN_CCCD` (12 số), `VN_PHONE` (`0[3-9]xxxxxxxx`), `EMAIL`; text sạch → `has_pii=False`; anonymized khác text gốc |
| 9b | `check_input_rail()` | 5 | `async`; `await rails.generate_async(messages=[{user, text}])`; coi là blocked nếu response chứa refuse-keyword (`xin lỗi/không thể/i cannot`...) | trả dict `{allowed, blocked_reason, response}` |
| 10 | `run_adversarial_suite()` | 10 | `async def _run_all()` loop 20 input: Layer1 `pii_scan` (block nếu PII) → Layer2 `check_input_rail`; **gọi `asyncio.run()` đúng 1 lần** (ngoài loop); so `actual` vs `expected` | trả 20 kết quả, đủ keys `{id,category,expected,actual,passed}`; **pass rate ≥ 15/20 (75%)** |
| 11 | `check_output_rail()` | 5 | `async`; `await rails.generate_async(messages=[user q, assistant answer])`; flag nếu response chứa refuse-keyword | trả `{safe, flagged_reason, final_answer}` |
| 12 | `measure_p95_latency()` | 5 | `async def _measure()` đo riêng Presidio (sync) + NeMo (await); 1 lần `asyncio.run()`; hàm `percentiles()` cho p50/p95/p99 | đủ keys `{presidio_ms, nemo_ms, total_ms, latency_budget_ok, budget_ms}`; mỗi layer có p50/p95; giá trị ≥ 0 |

**Cấu trúc `adversarial_set_20.json`:** 4 category × 5 = `{pii_injection, jailbreak, off_topic, prompt_injection}`, **tất cả `expected: "blocked"`**. Vậy guard phải chặn ≥15/20.
- `pii_injection` (5) → bắt bởi **Presidio** (Layer 1) → gần như chắc chắn pass nếu `pii_scan` đúng.
- `jailbreak/off_topic/prompt_injection` (15) → bắt bởi **NeMo input rail** (Layer 2). Đây là phần rủi ro pass rate.

**Tăng pass rate (đạt ≥15, hướng tới Bonus C ≥18/20):** mở rộng `guardrails/rails.co`:
- Thêm mẫu câu vào `user ask jailbreak`, `user ask off topic`, và **thêm flow mới cho prompt_injection** (hiện rails.co chưa có flow riêng cho prompt injection — đọc các `input` category `prompt_injection` trong dataset rồi thêm patterns/flow tương ứng).
- Đảm bảo refuse-keyword trong rails.co (vd "Xin lỗi") khớp với danh sách `refuse_keywords` trong `check_input_rail()`.

**Chạy & xuất:** `python src/phase_c_guard.py`. **Cần bổ sung `json.dump` → `reports/guard_results.json`** (adversarial results + latency + pass rate); scaffold main chỉ in màn hình.

### Task 13 — CI/CD Blueprint (điền tay vào [reports/blueprint.md](reports/blueprint.md))
4 section (mỗi section +2đ, tổng 8đ + 2đ điền số đo thật):
1. **Guard Stack Pipeline** — bảng Layer/Tool/Latency P95/Failure Action.
2. **CI Gates** — RAGAS faithfulness ≥ 0.75, adversarial ≥ 18/20, P95 < 500ms.
3. **Monitoring** — điền **số thật**: P95 latency (từ Task 12), pass rate (Task 10), worst RAGAS metric (Phase A), dominant failure distribution (Phase A).
4. Hoàn chỉnh & nhất quán với kết quả các phase.

---

## 5. Bonus (mục tiêu +10)

| Bonus | Điều kiện | Đòn bẩy |
|---|---|---|
| A (+4) | `adversarial avg_score < factual avg_score` | Pipeline Day 18 phải phân biệt được version v2023/v2024; nếu không đạt → cải thiện metadata filter / rerank ở Day 18 |
| B (+3) | Cohen's κ > 0.6 | Prompt judge rõ ràng + sinh `judge_labels` hợp lý từ 10 câu human-labeled |
| C (+3) | Adversarial pass rate ≥ 18/20 | Mở rộng `rails.co` (đặc biệt prompt_injection) + Presidio chắc chắn bắt 5 PII |

---

## 6. Thứ tự thực thi đề xuất

1. **Setup** (mục 1) — ✅ Day 18 đã copy; **việc còn lại: Qdrant + spaCy + `.env` rồi chạy `setup_answers.py`** để có `answers_50q.json`. *(làm trước tiên)*
2. **Phase A** — nhanh nhất, logic thuần (không nhiều LLM call). Lấy số liệu cho blueprint + analysis.
3. **Phase B** — cần OpenAI calls; viết κ tay; nhớ ghi JSON output.
4. **Phase C** — Presidio trước (Task 9a/test offline được), rồi NeMo (cần API). Mở rộng rails.co nếu pass rate < 15.
5. **Task 13 blueprint** + 2 file `analysis/*.md` — điền số thật từ A/B/C.
6. **Final check** (mục 7).

---

## 7. Kiểm tra & nộp bài

```bash
pytest tests/ -v                      # toàn bộ test phải pass (fail -3đ/test)
grep -r "# TODO" src/phase_*.py       # phải = 0 (còn TODO -5đ/module)
python check_lab.py                   # final checklist
```

**Checklist nộp (theo README + RUBRIC):**
- [ ] 6 file Day 18 trong `src/`
- [ ] `answers_50q.json` đã generate (50 phần tử)
- [ ] 0 TODO trong `src/phase_*.py`
- [ ] `reports/ragas_50q.json` (Phase A — tự ghi qua `save_phase_a_report`)
- [ ] `reports/judge_results.json` (Phase B — **tự thêm `json.dump`**)
- [ ] `reports/guard_results.json` (Phase C — **tự thêm `json.dump`**)
- [ ] `reports/blueprint.md` điền đủ 4 section + số đo thật (không để trống → tránh -10đ)
- [ ] `analysis/failure_clusters.md` + `analysis/bias_report.md` điền đầy đủ
- [ ] `pytest tests/` xanh toàn bộ
- [ ] Commit + push lên GitHub trước hết giờ

---

## 8. Rủi ro & cách xử lý

| Rủi ro | Dấu hiệu | Xử lý |
|---|---|---|
| Thiếu file Day 18 | `ImportError m4_eval` / setup fail | Copy đủ 6 file; đảm bảo `evaluate_ragas` trả `per_question` |
| Qdrant chưa chạy | setup_answers timeout port 6333 | `docker compose up -d`, kiểm tra `docker ps` |
| Presidio thiếu spaCy model | `OSError can't find en_core_web_lg` | `python -m spacy download en_core_web_lg` |
| sklearn không có | `ModuleNotFoundError sklearn` ở Task 7 | Dùng công thức Cohen's κ tay (đã nêu mục 3) |
| `asyncio.run()` trong loop | `RuntimeError: event loop` | Gọi `asyncio.run()` **một lần duy nhất** bao cả loop (Task 10, 12) |
| Adversarial pass < 15/20 | test_phase_c fail | Mở rộng `rails.co`, thêm flow prompt_injection, đồng bộ refuse-keyword |
| reports JSON thiếu | `check_lab.py` báo thiếu | Tự thêm `json.dump` cho Phase B & C |
| Lỗi encoding tiếng Việt (Win) | `UnicodeEncodeError` | `set PYTHONIOENCODING=utf-8`; luôn `encoding="utf-8"` khi I/O |

---

## 9. Phân bổ điểm (tham chiếu nhanh)

| Phase | Task | Điểm | Bonus |
|---|---|---|---|
| A — RAGAS | 1–4 | 30 | +4 (adv < factual) |
| B — Judge | 5–8 | 35 | +3 (κ > 0.6) |
| C — Guard | 9–12 | 35 | +3 (≥18/20) |
| Task 13 | Blueprint | (đánh giá riêng, +10) | — |
| **Tổng** | | **100** | **+10** |
