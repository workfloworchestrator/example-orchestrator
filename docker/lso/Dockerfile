FROM python:3.12-alpine

WORKDIR /app

RUN apk add --update --no-cache gcc libc-dev libffi-dev

RUN pip install orchestrator-lso=="1.0.2" 

RUN pip install pynetbox

RUN ansible-galaxy collection install nokia.srlinux -p /usr/local/lib/python3.12/site-packages/ansible_collections

EXPOSE 8000
ENTRYPOINT []
CMD ["python", "-m",  "uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
