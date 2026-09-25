# Reproducible ARM64/AMD64 sandbox for Hermes role tools.
# No secrets are baked into this image; the active project is mounted at /workspace.
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl git nodejs npm ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 builder
WORKDIR /workspace
USER builder

CMD ["bash"]
