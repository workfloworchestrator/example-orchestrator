FROM ubuntu

RUN apt update && apt install curl -y

RUN useradd --create-home --shell /bin/bash rover-user

USER rover-user

WORKDIR /app

RUN curl -sSL https://rover.apollo.dev/nix/v0.23.0 | sh

ENTRYPOINT ["/home/rover-user/.rover/bin/rover"]
