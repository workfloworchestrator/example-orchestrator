# import uvicorn
from orchestrator import OrchestratorCore
from orchestrator.cli.main import app as core_cli
from orchestrator.settings import AppSettings

import products  # noqa: F401  Side-effects
import workflows  # noqa: F401  Side-effects

app = OrchestratorCore(base_settings=AppSettings())

if __name__ == "__main__":
    core_cli()
    # uvicorn.run(app, host="127.0.0.1", port=8080)
