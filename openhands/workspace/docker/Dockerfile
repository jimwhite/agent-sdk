# syntax=docker/dockerfile:1.7
# OpenHands Runtime Image
# This Dockerfile creates runtime images for OpenHands with hash-based caching

ARG BASE_IMAGE=python:3.12-bookworm
ARG USERNAME=openhands
ARG UID=10001
ARG GID=10001

############################
# Base Runtime Setup
############################
FROM ${BASE_IMAGE} AS base-runtime
ARG USERNAME UID GID

SHELL ["/bin/bash", "-c"]

# Environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    EDITOR=code \
    VISUAL=code \
    GIT_EDITOR="code --wait" \
    OPENVSCODE_SERVER_ROOT=/openhands/.openvscode-server

# Install system dependencies
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates curl wget sudo apt-utils git jq tmux build-essential \
        coreutils util-linux procps findutils grep sed ripgrep ffmpeg \
        apt-transport-https gnupg lsb-release; \
    rm -rf /var/lib/apt/lists/*

# Create user and group
RUN set -eux; \
    (getent group ${GID} || groupadd -g ${GID} ${USERNAME}); \
    (id -u ${USERNAME} >/dev/null 2>&1 || useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}); \
    usermod -aG sudo ${USERNAME}; \
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Install Docker
RUN set -eux; \
    if grep -q "ubuntu" /etc/os-release; then \
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc; \
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null; \
    else \
        curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc; \
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null; \
    fi; \
    chmod a+r /etc/apt/keyrings/docker.asc; \
    apt-get update; \
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; \
    rm -rf /var/lib/apt/lists/*

# Configure Docker
RUN mkdir -p /etc/docker && \
    echo '{"mtu": 1450}' > /etc/docker/daemon.json

# Setup VSCode Server
ARG RELEASE_TAG="openvscode-server-v1.98.2"
ARG RELEASE_ORG="gitpod-io"
RUN set -eux; \
    mkdir -p $(dirname ${OPENVSCODE_SERVER_ROOT}); \
    arch=$(uname -m); \
    if [ "${arch}" = "x86_64" ]; then arch="x64"; \
    elif [ "${arch}" = "aarch64" ]; then arch="arm64"; \
    elif [ "${arch}" = "armv7l" ]; then arch="armhf"; fi; \
    wget https://github.com/${RELEASE_ORG}/openvscode-server/releases/download/${RELEASE_TAG}/${RELEASE_TAG}-linux-${arch}.tar.gz; \
    tar -xzf ${RELEASE_TAG}-linux-${arch}.tar.gz; \
    mv ${RELEASE_TAG}-linux-${arch} ${OPENVSCODE_SERVER_ROOT}; \
    cp ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/openvscode-server ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/code; \
    rm -f ${RELEASE_TAG}-linux-${arch}.tar.gz; \
    chown -R ${USERNAME}:${USERNAME} ${OPENVSCODE_SERVER_ROOT}

# Prepare workspace
RUN mkdir -p /workspace/project && \
    chown -R ${USERNAME}:${USERNAME} /workspace

############################
# Target: with-browser
# Includes browser support (VNC, Chromium, noVNC)
############################
FROM base-runtime AS with-browser
ARG USERNAME

# Install VNC + Desktop + Browser
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        tigervnc-standalone-server xfce4 dbus-x11 novnc websockify \
        $(if grep -q "ubuntu" /etc/os-release; then echo "chromium-browser"; else echo "chromium"; fi); \
    rm -rf /var/lib/apt/lists/*

ENV NOVNC_WEB=/usr/share/novnc \
    NOVNC_PORT=8002 \
    DISPLAY=:1 \
    VNC_GEOMETRY=1280x800 \
    CHROME_BIN=/usr/bin/chromium \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    CHROMIUM_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu" \
    OH_ENABLE_VNC=true

RUN chown -R ${USERNAME}:${USERNAME} ${NOVNC_WEB}

USER ${USERNAME}
WORKDIR /workspace
EXPOSE 8002

############################
# Target: runtime (default)
# Standard runtime without browser support
############################
FROM base-runtime AS runtime
ARG USERNAME

USER ${USERNAME}
WORKDIR /workspace
