
FROM mcr.microsoft.com/devcontainers/python:3.12

# Asenna perus työkalut
RUN apt-get update && apt-get install -y \
    docker.io docker-compose-plugin \
    git curl wget build-essential \
    python3-venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Varmista että python3 on oletus
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Asenna Copilot/Codex-valmius (Jupyter)
RUN pip install --upgrade pip \
    && pip install jupyter ipykernel

# Lisää vscode-käyttäjä docker-ryhmään Codespacesia/Hetzneriä varten
RUN groupadd docker || true && usermod -aG docker vscode || true

