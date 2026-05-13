# Inference API

FastAPI service for baseline prediction. It uses a saved sklearn model when available and otherwise falls back to a heuristic.

Local port:

```text
8002
```

Primary docs:

- [Service doc](../../docs/services/inference-api.md)
- [Runtime flows](../../docs/FLOWS.md)
- [Notebooks](../../docs/NOTEBOOKS.md)

Smoke check:

```bash
curl http://127.0.0.1:8002/health
```

Model workbench:

```text
notebooks/005_model_research_workbench.ipynb
```

It can save `models/baseline.joblib`, which this service uses automatically when present.

Train from labeled `trade_outcomes`:

```bash
./scripts/train.sh
```

The trainer compares several supervised sklearn classifiers, runs small hyperparameter grids, stores validation metrics in the artifact, and saves the best model to `models/baseline.joblib`.

Environment note: this service does not receive Hermes-only secrets from `services/hermes-workspace/.env`.
