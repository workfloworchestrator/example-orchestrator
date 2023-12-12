# Example Workflow Orchestrator

Example workflow orchestrator
(https://workfloworchestrator.org/orchestrator-core/) implementation.

**Note: work in progress; first version expected to be released by the end 
of 2023**

## Quickinstall

Create a venv, then run these commands:

```
pip install -r requirements.txt
python main.py db upgrade heads
python -u -m uvicorn --reload --workers 4 --host 0.0.0.0 --port 8080 main:app
```

This assumes a environment that has correct settings or it will use the orchestrator-core defaults (like DB name orchestratorc-core).

And example is in `.env.example`

You can find a list with default settings [here](https://github.com/workfloworchestrator/orchestrator-core/blob/main/orchestrator/settings.py)

