# OraTriage Bench

A benchmark for **triaging Oracle E-Business Suite and Oracle Database alerts**: given one alert, decide what an on-call DBA should do with it.

295 alerts across the EBS apps tier, the database tier (19c/23ai), security versus noise, and deliberately hard cases. Every alert has gold answers reviewed by an Oracle Apps DBA.

The point is to measure the question operations teams actually care about: *would this system have woken the right person, and would it have woken the wrong one?* General LLM benchmarks don't measure that for Oracle shops.

## The task

For each alert, a system answers six questions. Only `route` is required.

| Field | Type | Meaning |
|---|---|---|
| `route` | one of 6 | `security` escalate to security first · `page` wake the on-call DBA · `autofix` standard runbook, behind an approval gate · `ticket` handle in business hours · `log` record only · `llm` too unclear for rules, needs reasoning or a human read |
| `needs_human` | yes/no | A DBA must act right now |
| `security_risk` | yes/no | Possible security issue |
| `runbook_safe` | yes/no | A standard runbook fixes it safely without investigation |
| `area` | one of 8 | `concurrent_manager`, `tablespace`, `locking`, `workflow`, `patching`, `security`, `performance`, `maintenance` |
| `severity` | 0–4 | Info, Low, Medium, High, Critical |

## Data

`data/oratriage-bench-v1.jsonl`, one alert per line:

```json
{"id": "B001", "text": "[OEM CRITICAL] FINPRD / ebsapp01: Internal Concurrent Manager (FNDICM) not running since 02:14 ...",
 "slice": "ebs_apps", "difficulty": "easy",
 "gold": {"route": "page", "needs_human": true, "security_risk": false, "runbook_safe": false, "area": "concurrent_manager", "severity": 3},
 "rationale": "PROD ICM down with all managers idle ...", "dba_changed": false, "dba_note": ""}
```

| Slice | Alerts | What's in it |
|---|---|---|
| `ebs_apps` | 75 | Concurrent managers, Workflow and Notification Mailer, adop, OACore/Forms/WebLogic |
| `db_tier` | 72 | Space, ASM, archiver, locking, ORA-600, RMAN, Data Guard, plans and waits |
| `security_noise` | 73 | Real threats mixed with scary-looking but routine events |
| `hard` | 75 | Vague tickets, misleading keywords, symptoms caused by another area, buried key lines |

Gold routes: log 75, ticket 61, page 47, security 43, llm 36, autofix 33. About a third of the alerts are marked `difficulty: hard`.

## How the data was made (read this)

- **The alerts are synthetic.** They were written by Claude (Anthropic) in the style of OEM incidents, alert-log lines, monitoring emails, helpdesk tickets and Slack messages. No company's real data is included. IP addresses use documentation ranges or private ranges.
- **The gold answers were drafted by Claude and then reviewed by one Oracle Apps DBA**, who changed 2 of 295 (both raised to severity 4 for total concurrent-processing outages; see `dba_changed` and `dba_note`).
- **Leakage control:** alerts within cosine similarity 0.92 of the OraTriage training data were removed, and training data near any benchmark alert was dropped.

Because the drafts came from an LLM and the review changed little, **this benchmark may favor systems that think like Claude.** Version 2 will add real, anonymized alerts and more reviewers. Treat v1 as a useful yardstick, not a final word.

## Metrics

- **Route accuracy**: the headline number.
- **Missed urgent**: of alerts whose gold route is `page` or `security`, the share routed to `log` or `ticket`. The costly mistake.
- **False pages**: of alerts whose gold route is `log`, the share routed to `page` or `security`.
- Per-question accuracy, area accuracy, severity mean absolute error, route accuracy per slice.
- Reported alongside: latency (p50), cost per 1,000 alerts, and **whether alert text leaves the company**.

## Run it

```bash
python3 baselines/keyword_rules.py        # writes results/keyword-rules.jsonl
python3 score.py results/keyword-rules.jsonl
python3 score.py --all                    # rebuilds LEADERBOARD.md
```

Standard library only, Python 3.9+. To score your own system, write `results/<name>.jsonl` (see `examples/predict_template.py`) plus an optional `results/<name>.meta.json` with `engine`, `cost_per_1k_usd`, `data_leaves_company` and `notes`.

## Current results

See [LEADERBOARD.md](LEADERBOARD.md). Summary:

| Engine | Route acc. | Missed urgent | Data leaves company? |
|---|---|---|---|
| OraTriage v2, inside Oracle 23ai | 58.0% | 15.6% | no |
| OraTriage v2, local | 56.3% | 17.8% | no |
| Keyword rules baseline | 22.7% | 35.6% | no |
| Claude Haiku 4.5, zero-shot (**partial: 86 of 295**) | 60.5% | 0% | yes |

On the 86 alerts where all of them were run, OraTriage in Oracle scored 61.6% against Claude Haiku's 60.5%. That is a difference of one alert and should be read as "about equal". It still misses too many urgent alerts on its own, so we recommend running it with an LLM fallback for low-confidence cases.

## Submitting results

Open a pull request adding `results/<name>.jsonl` and `.meta.json`. Please state the model and version, whether you used any of the benchmark text for training or prompting (you shouldn't), and the hardware for latency numbers. Results for other decision models (for example Jev from TypeSafe) are especially welcome.

## License

- Code (`score.py`, `baselines/`, `examples/`): MIT, see `LICENSE`.
- Data (`data/`): CC BY 4.0, see `LICENSE-DATA`.

OraTriage Bench is an independent personal project, built with synthetic data. It is not affiliated with or endorsed by Oracle, Anthropic or TypeSafe. Oracle, E-Business Suite and related names are trademarks of their owners.
