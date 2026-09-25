FROM ubuntu:26.04

RUN apt update && apt install curl -y

ARG ROVER_UID=1001
RUN userdel -r ubuntu 2>/dev/null || true \
    && useradd --uid ${ROVER_UID} --create-home --shell /bin/bash rover-user

USER rover-user
RUN curl -sSL https://rover.apollo.dev/nix/v0.38.1 | sh

USER root
RUN apt remove curl -y

USER rover-user
WORKDIR /app

ENTRYPOINT ["/home/rover-user/.rover/bin/rover"]
