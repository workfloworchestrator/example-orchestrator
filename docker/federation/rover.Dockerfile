FROM ubuntu

RUN apt update && apt install curl -y

# uid 1000 so rover can write the supergraph into the bind-mounted /app
# (ubuntu:24.04+ ships a default `ubuntu` user occupying uid 1000)
RUN (userdel -r ubuntu || true) && useradd --create-home --uid 1000 --shell /bin/bash rover-user

USER rover-user
RUN curl -sSL https://rover.apollo.dev/nix/v0.38.1 | sh

USER root
RUN apt remove curl -y

USER rover-user
WORKDIR /app

ENTRYPOINT ["/home/rover-user/.rover/bin/rover"]
