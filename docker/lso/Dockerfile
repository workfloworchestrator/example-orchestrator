FROM python:3.13.13-alpine

WORKDIR /app

RUN apk add --update --no-cache gcc libc-dev libffi-dev

RUN pip install orchestrator-lso=="3.0.0"

RUN pip install pynetbox ansible

# TODO Check with Karel if this is needed. It was causing the build to fail, commenting out seems to work fine.
# RUN mkdir -p $ANSIBLE_COLLECTIONS_PATH

RUN ansible-galaxy collection install nokia.srlinux

EXPOSE 8000
ENTRYPOINT []
CMD ["python", "-m",  "uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
