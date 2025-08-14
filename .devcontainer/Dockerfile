FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Asenna perus työkalut ilman docker-compose-plugin
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    docker.io docker-compose \
    git curl wget build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Asenna Docker CLI ja Compose v2 GitHubin virallisesta binääristä
RUN curl -fsSL https://get.docker.com | sh && \
    DOCKER_COMPOSE_VERSION=2.29.7 && \
    curl -SL https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Varmistetaan että python3 on oletus
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Copilot/Codex valmius
RUN pip install --upgrade pip && \
    pip install jupyter ipykernel

# Käyttäjä docker-ryhmään (Codespaces)
RUN groupadd docker || true && usermod -aG docker vscode || true

