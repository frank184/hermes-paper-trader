# Notebooks

Notebooks are for research, inspection, and toy examples. They are not part of the production trading loop.

Start Jupyter:

```bash
docker compose up jupyter
```

Open:

```text
http://127.0.0.1:8888
```

## Included Notebooks

- `001_data_flow_toy_example.ipynb`: audit trail shape.
- `002_feature_math_toy_example.ipynb`: simple returns, moving-average distance, volatility, and heuristic scoring.
- `003_policy_gate_toy_example.ipynb`: policy approval/rejection examples.
- `004_alpaca_sdk_toy_example.ipynb`: read-only Alpaca SDK account/clock/bars calls.
- `005_model_research_workbench.ipynb`: data loading, the same supervised model-selection pipeline used by `services/inference-api/app/train.py`, threshold tuning, and `models/baseline.joblib` export.

## VS Code

Connect the VS Code Jupyter extension to:

```text
http://127.0.0.1:8888
```

The notebook server is local-only. Token and XSRF checks are disabled to reduce VS Code remote-kernel friction.

When the Jupyter container restarts, existing kernels are gone. Re-select a kernel in VS Code.

## Stale Kernel After Restart

If Docker logs show:

```text
Kernel does not exist
```

VS Code is trying to reuse a kernel UUID from before the Jupyter container restarted. The notebook file is fine; the old kernel process is gone.

Use this recovery path:

1. Confirm browser Jupyter works at `http://127.0.0.1:8888`.
2. In VS Code, run `Jupyter: Clear Saved Jupyter Servers`.
3. Run `Developer: Reload Window`.
4. Reopen the notebook.
5. Select `Existing Jupyter Server` and enter `http://127.0.0.1:8888`.
6. Select the `Python 3 (ipykernel)` kernel.

If VS Code still appears idle, close the notebook editor tab and reopen it from the file explorer. VS Code can keep a dead notebook controller attached even after the server has recovered.
