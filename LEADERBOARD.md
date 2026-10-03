# OraTriage Bench v1: leaderboard

295 Oracle EBS / Database alerts, gold answers reviewed by an Oracle Apps DBA. Sorted by route accuracy. Partial runs (coverage < 100%) are listed but not ranked.

| Engine | Coverage | Route acc. | Missed urgent ↓ | False pages ↓ | Needs DBA | Security | Area | Sev. err ↓ | p50 ms | $ / 1k | Data leaves? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OraTriage v2, inside Oracle 23ai | 100.0% | **58.0%** | 15.6% | 8.0% | 80.3% | 91.9% | 77.6% | 0.71 | 94 | $0.00 | no |
| OraTriage v2, local (Ollama) | 100.0% | **56.3%** | 17.8% | 13.3% | 80.0% | 90.8% | 78.0% | 0.67 | 125 | $0.00 | no |
| Keyword rules (baseline) | 100.0% | **22.7%** | 35.6% | 1.3% | 69.5% | 85.1% | 50.2% | 1.34 | 0 | $0.00 | no |
| Claude Haiku 4.5 (zero-shot, via OpenRouter) (partial) | 29.2% | **60.5%** | 0.0% | 0.0% | 55.8% | 95.3% | 76.7% | 0.48 | 1675 | $1.56 | yes |

**Missed urgent**: alerts that needed a page or a security escalation but were routed to log or ticket. **False pages**: routine alerts (gold: log) that would have woken someone up.

## Route accuracy by slice

| Engine | EBS apps | DB tier | Security vs noise | Hard cases |
|---|---|---|---|---|
| OraTriage v2, inside Oracle 23ai | 68.0% | 55.6% | 67.1% | 41.3% |
| OraTriage v2, local (Ollama) | 57.3% | 52.8% | 69.9% | 45.3% |
| Keyword rules (baseline) | 18.7% | 16.7% | 23.3% | 32.0% |
| Claude Haiku 4.5 (zero-shot, via OpenRouter) | 59.0% | 66.7% | 53.8% | 50.0% |

## Notes

- **OraTriage v2, inside Oracle 23ai**: Closed model: in-database ONNX MiniLM embedding + SQL TF-IDF + calibrated heads, trained on 1,812 synthetic alerts labeled by Claude. Latency on an Apple M3 laptop.
- **OraTriage v2, local (Ollama)**: Same heads on nomic-embed-text embeddings via Ollama.
- **Keyword rules (baseline)**: Regex weights written by hand; no training data.
- **Claude Haiku 4.5 (zero-shot, via OpenRouter)**: Partial run: 86 of 295 alerts before the account ran out of credit. Not comparable to full runs; listed for transparency.
