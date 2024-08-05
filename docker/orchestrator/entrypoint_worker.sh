#!/bin/bash
pip install -r requirements-worker.txt

export PATH=$PATH:$HOME/.local/bin

watchmedo auto-restart --patterns="*.py;*.json" --recursive -- celery -A tasks worker -E --loglevel=info -Q new_workflows,new_tasks,resume_tasks,resume_workflows --concurrency=1 -n%n
