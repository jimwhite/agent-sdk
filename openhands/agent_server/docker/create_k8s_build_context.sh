#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Kubernetes Build Context Generator for OpenHands Agent Server
# ------------------------------------------------------------
# This script creates a tar.gz file containing everything needed
# to build the agent-server in a Kubernetes environment.
# The resulting tar.gz will have a Dockerfile at the top level
# and all necessary source code and dependencies.
# ------------------------------------------------------------

# Config (overridables)
OUTPUT_DIR="${OUTPUT_DIR:-./k8s-build}"
BASE_IMAGE="${BASE_IMAGE:-nikolaik/python-nodejs:python3.12-nodejs22}"
TARGET="${TARGET:-binary}"
CLEAN_OUTPUT="${CLEAN_OUTPUT:-true}"
CUSTOM_TAGS="${CUSTOM_TAGS:-python}"

# Generate tag using same logic as build.sh
GIT_SHA="${GITHUB_SHA:-$(git rev-parse --verify HEAD 2>/dev/null || echo unknown)}"
SHORT_SHA="${GIT_SHA:0:7}"
IFS=',' read -ra CUSTOM_TAG_ARRAY <<< "${CUSTOM_TAGS}"
PRIMARY_TAG="${CUSTOM_TAG_ARRAY[0]}"

# Generate output filename with tag
if [[ -n "${OUTPUT_NAME:-}" ]]; then
    # Use provided OUTPUT_NAME if specified
    OUTPUT_FILENAME="${OUTPUT_NAME}"
else
    # Generate filename with tag format: agent-server-{SHORT_SHA}-{PRIMARY_TAG}.tar.gz
    OUTPUT_FILENAME="agent-server-${SHORT_SHA}-${PRIMARY_TAG}.tar.gz"
fi

# Validate target
case "${TARGET}" in
  binary|binary-minimal|source|source-minimal) ;;
  *) echo "[k8s-build] ERROR: Invalid TARGET '${TARGET}'. Must be one of: binary, binary-minimal, source, source-minimal" >&2; exit 1 ;;
esac

# Paths
SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd -P)"
BUILD_CONTEXT_DIR="${OUTPUT_DIR}/build-context"

echo "[k8s-build] Creating Kubernetes build context for agent-server"
echo "[k8s-build] Repository root: ${REPO_ROOT}"
echo "[k8s-build] Target: ${TARGET}"
echo "[k8s-build] Base image: ${BASE_IMAGE}"
echo "[k8s-build] Git SHA: ${SHORT_SHA}"
echo "[k8s-build] Primary tag: ${PRIMARY_TAG}"
echo "[k8s-build] Output: ${OUTPUT_DIR}/${OUTPUT_FILENAME}"

# Clean and create output directory
if [[ "${CLEAN_OUTPUT}" == "true" && -d "${OUTPUT_DIR}" ]]; then
  echo "[k8s-build] Cleaning existing output directory..."
  rm -rf "${OUTPUT_DIR}"
fi

mkdir -p "${BUILD_CONTEXT_DIR}"

# ------------------------------------------------------------
# Copy source files
# ------------------------------------------------------------
echo "[k8s-build] Copying source files..."

# Copy root-level files needed for build
cd "${REPO_ROOT}"
cp pyproject.toml "${BUILD_CONTEXT_DIR}/"
cp uv.lock "${BUILD_CONTEXT_DIR}/"
cp README.md "${BUILD_CONTEXT_DIR}/"
cp LICENSE "${BUILD_CONTEXT_DIR}/"

# Copy the entire openhands directory structure
cp -r openhands "${BUILD_CONTEXT_DIR}/"

# ------------------------------------------------------------
# Create standalone Dockerfile
# ------------------------------------------------------------
echo "[k8s-build] Creating standalone Dockerfile..."

cat > "${BUILD_CONTEXT_DIR}/Dockerfile" << 'EOF'
# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE=nikolaik/python-nodejs:python3.12-nodejs22
ARG USERNAME=openhands
ARG UID=10001
ARG GID=10001
ARG PORT=8000

####################################################################################
# Builder (source mode)
# We copy source + build a venv here for local dev and debugging.
####################################################################################
FROM python:3.12-bookworm AS builder
ARG USERNAME UID GID
ENV UV_PROJECT_ENVIRONMENT=/agent-server/.venv

COPY --from=ghcr.io/astral-sh/uv /uv /uvx /bin/

RUN groupadd -g ${GID} ${USERNAME} \
 && useradd -m -u ${UID} -g ${GID} -s /usr/sbin/nologin ${USERNAME}
USER ${USERNAME}
WORKDIR /agent-server
# Cache-friendly: lockfiles first
COPY --chown=${USERNAME}:${USERNAME} pyproject.toml uv.lock README.md LICENSE ./
COPY --chown=${USERNAME}:${USERNAME} openhands ./openhands
RUN --mount=type=cache,target=/home/${USERNAME}/.cache,uid=${UID},gid=${GID} \
    uv sync --frozen --no-editable

####################################################################################
# Binary Builder (binary mode)
# We run pyinstaller here to produce openhands-agent-server
####################################################################################
FROM builder AS binary-builder
ARG USERNAME UID GID

# We need --dev for pyinstaller
RUN --mount=type=cache,target=/home/${USERNAME}/.cache,uid=${UID},gid=${GID} \
    uv sync --frozen --dev --no-editable

RUN --mount=type=cache,target=/home/${USERNAME}/.cache,uid=${UID},gid=${GID} \
    uv run pyinstaller openhands/agent_server/agent-server.spec
# Fail fast if the expected binary is missing
RUN test -x /agent-server/dist/openhands-agent-server

####################################################################################
# Base image (minimal)
# It includes only basic packages and the UV runtime.
# No Docker, no VNC, no Desktop, no VSCode Web.
# Suitable for running in headless/evaluation mode.
####################################################################################
FROM ${BASE_IMAGE} AS base-image-minimal
ARG USERNAME UID GID PORT

# Install base packages and create user
RUN set -eux; \
    # Install base packages (works for both Debian-based images)
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates curl wget sudo apt-utils git jq tmux build-essential \
        coreutils util-linux procps findutils grep sed \
        # Docker dependencies
        apt-transport-https gnupg lsb-release; \
    \
    # Create user and group
    (getent group ${GID} || groupadd -g ${GID} ${USERNAME}); \
    (id -u ${USERNAME} >/dev/null 2>&1 || useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}); \
    # Add user to sudo group
    usermod -aG sudo ${USERNAME}; \
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers; \
    # Create workspace directory
    mkdir -p /workspace/project; \
    chown -R ${USERNAME}:${USERNAME} /workspace; \
    rm -rf /var/lib/apt/lists/*

# NOTE: we should NOT include UV_PROJECT_ENVIRONMENT here, 
# since the agent might use it to perform other work (e.g. tools that use Python)
COPY --from=ghcr.io/astral-sh/uv /uv /uvx /bin/

USER ${USERNAME}
WORKDIR /
ENV OH_ENABLE_VNC=false
ENV LOG_JSON=true
EXPOSE ${PORT}

####################################################################################
# Base image (full)
# It includes additional Docker, VNC, Desktop, and VSCode Web.
####################################################################################
FROM base-image-minimal AS base-image

USER root
# --- VSCode Web ---
ENV EDITOR=code \
    VISUAL=code \
    GIT_EDITOR="code --wait" \
    OPENVSCODE_SERVER_ROOT=/openhands/.openvscode-server
ARG RELEASE_TAG="openvscode-server-v1.98.2"
ARG RELEASE_ORG="gitpod-io"
RUN set -eux; \
    # Create necessary directories
    mkdir -p $(dirname ${OPENVSCODE_SERVER_ROOT}); \
    \
    # Determine architecture
    arch=$(uname -m); \
    if [ "${arch}" = "x86_64" ]; then \
        arch="x64"; \
    elif [ "${arch}" = "aarch64" ]; then \
        arch="arm64"; \
    elif [ "${arch}" = "armv7l" ]; then \
        arch="armhf"; \
    fi; \
    \
    # Download and install VSCode Server
    wget https://github.com/${RELEASE_ORG}/openvscode-server/releases/download/${RELEASE_TAG}/${RELEASE_TAG}-linux-${arch}.tar.gz; \
    tar -xzf ${RELEASE_TAG}-linux-${arch}.tar.gz; \
    if [ -d "${OPENVSCODE_SERVER_ROOT}" ]; then rm -rf "${OPENVSCODE_SERVER_ROOT}"; fi; \
    mv ${RELEASE_TAG}-linux-${arch} ${OPENVSCODE_SERVER_ROOT}; \
    cp ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/openvscode-server ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/code; \
    rm -f ${RELEASE_TAG}-linux-${arch}.tar.gz; \
    \
    # Set proper ownership
    chown -R ${USERNAME}:${USERNAME} ${OPENVSCODE_SERVER_ROOT}

# --- Docker ---
RUN set -eux; \
    # Determine OS type and install Docker accordingly
    if grep -q "ubuntu" /etc/os-release; then \
        # Handle Ubuntu
        install -m 0755 -d /etc/apt/keyrings; \
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc; \
        chmod a+r /etc/apt/keyrings/docker.asc; \
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null; \
    else \
        # Handle Debian
        install -m 0755 -d /etc/apt/keyrings; \
        curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc; \
        chmod a+r /etc/apt/keyrings/docker.asc; \
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null; \
    fi; \
    # Install Docker Engine, containerd, and Docker Compose
    apt-get update; \
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# Configure Docker daemon with MTU 1450 to prevent packet fragmentation issues
RUN mkdir -p /etc/docker && \
    echo '{"mtu": 1450}' > /etc/docker/daemon.json


# --- VNC + Desktop + noVNC ---
RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
    # GUI bits (remove entirely if headless)
    tigervnc-standalone-server xfce4 dbus-x11 novnc websockify \
    # Browser
    $(if grep -q "ubuntu" /etc/os-release; then echo "chromium-browser"; else echo "chromium"; fi); \
  apt-get clean; rm -rf /var/lib/apt/lists/*

ENV NOVNC_WEB=/usr/share/novnc \
    NOVNC_PORT=8002 \
    DISPLAY=:1 \
    VNC_GEOMETRY=1280x800 \
    CHROME_BIN=/usr/bin/chromium \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    CHROMIUM_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu"

RUN chown -R ${USERNAME}:${USERNAME} ${NOVNC_WEB}
# Override default XFCE wallpaper
COPY --chown=${USERNAME}:${USERNAME} openhands/agent_server/docker/wallpaper.svg /usr/share/backgrounds/xfce/xfce-shapes.svg

USER ${USERNAME}
WORKDIR /
ENV OH_ENABLE_VNC=true
ENV LOG_JSON=true
EXPOSE ${PORT} ${NOVNC_PORT}


####################################################################################
####################################################################################
# Build Targets
####################################################################################
####################################################################################

############################
# Target A: source
# Local dev and debugging mode: copy source + venv from builder
############################
FROM base-image AS source
ARG USERNAME
COPY --chown=${USERNAME}:${USERNAME} --from=builder /agent-server /agent-server
ENTRYPOINT ["/agent-server/.venv/bin/python", "-m", "openhands.agent_server"]

FROM base-image-minimal AS source-minimal
ARG USERNAME
COPY --chown=${USERNAME}:${USERNAME} --from=builder /agent-server /agent-server
ENTRYPOINT ["/agent-server/.venv/bin/python", "-m", "openhands.agent_server"]

############################
# Target B: binary-runtime
# Production mode: build the binary inside Docker and copy it in.
# NOTE: no support for external artifact contexts anymore.
############################
FROM base-image AS binary
ARG USERNAME

COPY --chown=${USERNAME}:${USERNAME} --from=binary-builder /agent-server/dist/openhands-agent-server /usr/local/bin/openhands-agent-server
RUN chmod +x /usr/local/bin/openhands-agent-server
ENTRYPOINT ["/usr/local/bin/openhands-agent-server"]

FROM base-image-minimal AS binary-minimal
ARG USERNAME
COPY --chown=${USERNAME}:${USERNAME} --from=binary-builder /agent-server/dist/openhands-agent-server /usr/local/bin/openhands-agent-server
RUN chmod +x /usr/local/bin/openhands-agent-server
ENTRYPOINT ["/usr/local/bin/openhands-agent-server"]
EOF

# ------------------------------------------------------------
# Create build instructions
# ------------------------------------------------------------
echo "[k8s-build] Creating build instructions..."

cat > "${BUILD_CONTEXT_DIR}/BUILD_INSTRUCTIONS.md" << EOF
# OpenHands Agent Server - Kubernetes Build Context

This directory contains everything needed to build the OpenHands Agent Server in a Kubernetes environment.

## Contents

- \`Dockerfile\`: Multi-stage Dockerfile for building the agent server
- \`pyproject.toml\`: Root project configuration with workspace definitions
- \`uv.lock\`: Locked dependencies for reproducible builds
- \`openhands/\`: Complete source code including SDK, tools, workspace, and agent server
- \`README.md\` & \`LICENSE\`: Project documentation and license

## Build Targets

The Dockerfile supports multiple build targets:

- \`binary\`: Production binary with full features (Docker, VNC, VSCode Web)
- \`binary-minimal\`: Production binary with minimal features (headless)
- \`source\`: Development mode with source code and virtual environment
- \`source-minimal\`: Development mode with minimal features

## Building

### Basic build (binary target):
\`\`\`bash
docker build -t openhands-agent-server .
\`\`\`

### Build with specific target:
\`\`\`bash
docker build --target binary-minimal -t openhands-agent-server:minimal .
\`\`\`

### Build with custom base image:
\`\`\`bash
docker build --build-arg BASE_IMAGE=ubuntu:22.04 -t openhands-agent-server .
\`\`\`

### Multi-platform build:
\`\`\`bash
docker buildx build --platform linux/amd64,linux/arm64 -t openhands-agent-server .
\`\`\`

## Running

The container exposes port 8000 by default:

\`\`\`bash
docker run -p 8000:8000 openhands-agent-server
\`\`\`

For targets with VNC support, port 8002 is also exposed:

\`\`\`bash
docker run -p 8000:8000 -p 8002:8002 openhands-agent-server
\`\`\`

## Environment Variables

- \`OH_ENABLE_VNC\`: Enable/disable VNC server (default: varies by target)
- \`LOG_JSON\`: Enable JSON logging (default: true)
- \`PORT\`: Server port (default: 8000)

## Generated by

This build context was generated using:
\`./openhands/agent_server/docker/create_k8s_build_context.sh\`

Target: ${TARGET}
Base Image: ${BASE_IMAGE}
Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
EOF

# ------------------------------------------------------------
# Create the tar.gz file
# ------------------------------------------------------------
echo "[k8s-build] Creating tar.gz archive..."

cd "${OUTPUT_DIR}"
tar -czf "${OUTPUT_FILENAME}" -C build-context .

# Get file size for reporting
FILE_SIZE=$(du -h "${OUTPUT_FILENAME}" | cut -f1)

echo "[k8s-build] ✅ Successfully created Kubernetes build context!"
echo "[k8s-build] 📦 Archive: ${OUTPUT_DIR}/${OUTPUT_FILENAME} (${FILE_SIZE})"
echo "[k8s-build] 📁 Contents:"
echo "   - Dockerfile (standalone, multi-stage)"
echo "   - Complete source code (openhands/)"
echo "   - Dependencies (pyproject.toml, uv.lock)"
echo "   - Build instructions (BUILD_INSTRUCTIONS.md)"
echo ""
echo "[k8s-build] 🚀 Ready for Kubernetes deployment!"
echo "[k8s-build] Extract and run: tar -xzf ${OUTPUT_FILENAME} && docker build -t openhands-agent-server ."

# Optional: show archive contents
if command -v tar >/dev/null 2>&1; then
  echo ""
  echo "[k8s-build] 📋 Archive contents:"
  tar -tzf "${OUTPUT_FILENAME}" | head -20
  TOTAL_FILES=$(tar -tzf "${OUTPUT_FILENAME}" | wc -l)
  if [[ ${TOTAL_FILES} -gt 20 ]]; then
    echo "   ... and $((TOTAL_FILES - 20)) more files"
  fi
fi