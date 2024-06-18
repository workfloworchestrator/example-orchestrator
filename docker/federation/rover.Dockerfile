FROM ubuntu

RUN apt update && apt install curl -y

RUN useradd --create-home --shell /bin/bash rover-user

USER rover-user
RUN curl -sSL https://rover.apollo.dev/nix/v0.23.0 | sh

USER root
RUN apt remove curl -y

USER rover-user
WORKDIR /app

ENTRYPOINT ["/home/rover-user/.rover/bin/rover"]
