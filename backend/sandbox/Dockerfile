# Kiro Labyrinth Sandbox Container
# Minimal Python environment for secure code execution

FROM python:3.12-slim-bookworm

# Security: Create non-root user for code execution
RUN useradd -m -s /bin/bash sandbox && \
    mkdir -p /app /code && \
    chown sandbox:sandbox /app /code

# Install minimal dependencies
RUN pip install --no-cache-dir --upgrade pip

# Security: Remove unnecessary packages
RUN apt-get update && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Security: Remove network utilities
RUN rm -f /usr/bin/wget /usr/bin/curl 2>/dev/null || true

# Copy runner script
COPY --chown=sandbox:sandbox runner.py /app/runner.py
COPY --chown=sandbox:sandbox maze_client.py /app/maze_client.py

# Set working directory
WORKDIR /code

# Switch to non-root user
USER sandbox

# Default command (will be overridden at runtime)
CMD ["python", "/app/runner.py"]
