# LLM bake-off (Blue Balance)

Compares local open-weight models for two roles: the agent (Arabic tool calling + refusals) and the crew-report extractor (10 fields with verbatim spans).

All test data in `cases.py` is **synthetic (Simulated)**: case IDs, fixture numbers and crew reports were written for this test and come from no real inspection. These are dev cases; the frozen held-out set for the extractor is a separate task.

## Run
```
set PYTHONUTF8=1
python eval/bakeoff/run_bakeoff.py gemma4:e4b-it-qat
python eval/bakeoff/run_bakeoff.py qwen3.5:4b
python eval/bakeoff/run_bakeoff.py qwen3.5:9b
python eval/bakeoff/run_bakeoff.py --summary
```
Needs Ollama on `127.0.0.1:11434` with the model pulled.

## Settings (same for every model)
`temperature 0`, `seed 42`, `num_ctx 8192`, `think false`, non-streaming `/api/chat`.

## What is measured
| Test | Metric |
|---|---|
| 10 Arabic tool questions | valid call (schema-valid), correct tool, correct arguments (only the listed keys) |
| 3 refusal prompts | refusal marker present, banned assertion words, any state-changing tool call. The texts are saved for manual review. |
| 10 crew reports | JSON valid, field accuracy, span exact-match (raw substring), empty-when-unsupported. Reported raw and after the code span verifier. |
| Latency | Ollama timers: `ttft_s` = load + prompt eval; `total_s` = total duration; median per test group |
| VRAM | peak `nvidia-smi memory.used` sampled every 0.5 s, plus the baseline before loading |

Every prompt, raw response and timing is saved in `results/<model>.json`.
