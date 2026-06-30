# CI/CD Blueprint: RAG Eval + Guardrail Stack

**Sinh viên:** Lâm — MSSV 2A202600555  
**Ngày:** 30/06/2026

---

## Guard Stack Architecture

```
User Input
    │
    ▼ (~?ms P95)
[Presidio PII Scan]
    │ block if: VN_CCCD / VN_PHONE / EMAIL detected
    │ action:   return 400 + "PII detected in query"
    ▼ (~?ms P95)
[NeMo Input Rail]
    │ block if: off-topic / jailbreak / prompt injection
    │ action:   return 503 + refuse message
    ▼
[RAG Pipeline (Day 18)]
    │ M1 Chunk → M2 Search → M3 Rerank → GPT-4o-mini
    ▼
[NeMo Output Rail]
    │ flag if:  PII in response / sensitive content
    │ action:   replace with safe response
    ▼
User Response
```

---

## Latency Budget

*(Điền từ kết quả Task 12 — measure_p95_latency())*

| Layer | P50 (ms) | P95 (ms) | P99 (ms) | Budget |
|---|---|---|---|---|
| Presidio PII | 25.5 | 30.0 | 30.0 | <10ms (vượt nhẹ) |
| NeMo Input Rail (self-check LLM) | 738.9 | 1411.8 | 1411.8 | <300ms (vượt) |
| RAG Pipeline | — | — | — | <2000ms (đo riêng ở Day 18) |
| NeMo Output Rail | — | — | — | <300ms |
| **Total Guard** | 755.7 | **1423.8** | 1423.8 | **<500ms** |

**Budget OK?** [ ] Yes / [x] No  
**Comment:** Sau khi chuyển NeMo sang **`self check input` (LLM-based, gpt-4o-mini)** để phân biệt đúng tiếng Việt, mỗi request tốn 1 LLM call → P95 NeMo ~1.4s, **vượt ngưỡng 500ms**. Đây là tradeoff thật: canonical-form matching bằng embedding tiếng Anh nhanh (<2ms) nhưng over-block mọi câu tiếng Việt; self-check LLM chính xác (legit qua, adversarial chặn — xem pass rate 20/20) nhưng chậm. **Hướng tối ưu production:** (1) dùng embedding **đa ngôn ngữ** (bge-m3 / multilingual-MiniLM) cho NeMo để quay lại tốc độ <50ms mà vẫn phân biệt được tiếng Việt; (2) cache verdict theo input đã thấy; (3) chạy self-check song song/streaming; (4) model nhỏ/nhanh hơn cho riêng tác vụ phân loại. Presidio P95 30ms — chi phí chính là load engine spaCy lúc startup (đã singleton + warm-up nên ổn định).

---

## CI/CD Gates (phải pass trước khi merge to main)

```yaml
# .github/workflows/rag_eval.yml
- name: RAGAS Quality Gate
  run: python src/phase_a_ragas.py
  env:
    MIN_FAITHFULNESS: 0.75
    MIN_AVG_SCORE: 0.65

- name: Guardrail Gate
  run: pytest tests/test_phase_c.py -k "test_adversarial_suite_pass_rate"
  # phải ≥ 15/20 (75%)

- name: Latency Gate
  run: python -c "from src.phase_c_guard import measure_p95_latency; ..."
  # P95 total < 500ms
```

---

## Monitoring Dashboard (production)

| Metric | Alert Threshold | Action |
|---|---|---|
| RAGAS faithfulness (daily sample) | < 0.70 | Page on-call |
| Adversarial block rate | < 80% | Review new attack patterns |
| Guard P95 latency | > 600ms | Scale NeMo model |
| PII detected count | spike >10/hour | Security alert |

---

## Kết quả thực tế từ Lab

| | Kết quả |
|---|---|
| RAGAS avg_score (50q) | 0.813 (factual 0.902 / multi_hop 0.773 / adversarial 0.714) |
| Worst metric | answer_relevancy (yếu nhất ở factual & adversarial) |
| Dominant failure distribution | factual (≈ multi_hop, đồng hạng 20 lỗi); adversarial avg thấp nhất |
| Cohen's κ | 0.800 (9/10 khớp — substantial/almost-perfect agreement) |
| Adversarial pass rate | 20 / 20 (100%) — presidio 4, nemo self-check 16 |
| Guard P95 latency | 1423.8 ms (Presidio 30 + NeMo self-check 1412) — vượt budget 500ms |

**Bonus đạt được:** Phase A (adversarial 0.714 < factual 0.902) ✅ · Phase B (κ=0.80 > 0.6) ✅ · Phase C (20/20 ≥ 18) ✅

---

## Nhận xét & Cải tiến

> [Viết 3-5 câu về: điều gì hoạt động tốt, điều gì cần cải thiện,
>  nếu deploy production thực sự bạn sẽ thay đổi gì trong stack này?]
