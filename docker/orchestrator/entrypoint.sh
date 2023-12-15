#!/bin/bash
python main.py db upgrade heads
pip install -r requirements.txt
python -u -m uvicorn --reload --proxy-headers --workers 4 --host 0.0.0.0 --port 8080 $UVICORN_ARGS main:app
# python -u -m debugpy --listen 0.0.0.0:5678 -m uvicorn --reload --proxy-headers --workers 4 --host 0.0.0.0 --port 8080 $UVICORN_ARGS main:app
# python -u -m debugpy --listen 0.0.0.0:5678 -m uvicorn --proxy-headers --workers 4 --host 0.0.0.0 --port 8080 $UVICORN_ARGS main:app
