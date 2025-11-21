FROM python:3.12-slim

# Create the vscode user
RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid 1000 -m vscode

WORKDIR /app

# install libs
RUN apt-get update --allow-releaseinfo-change \
    && apt-get install -y --no-install-recommends git make \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache poetry==1.8.4

# copy only the manifest
COPY pyproject.toml ./
RUN poetry config virtualenvs.in-project true \
 && poetry install --no-root --no-cache \
 && chown -R vscode:vscode /app

USER vscode
COPY --chown=vscode:vscode src ./src

CMD ["poetry", "run", "python", "-u", "-m", "src.main"]
