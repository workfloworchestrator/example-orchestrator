FROM python:3.12.7-alpine

WORKDIR /app

RUN apk add --update --no-cache gcc libc-dev libffi-dev

RUN pip install orchestrator-lso=="2.2.0"

RUN pip install pynetbox

RUN ansible-galaxy collection install nokia.srlinux -p /app/demo/ansible

EXPOSE 8000
ENTRYPOINT []
CMD ["python", "-m",  "uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
