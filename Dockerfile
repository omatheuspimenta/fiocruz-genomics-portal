FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Copy backend files
COPY pyproject.toml uv.lock README.md ./
COPY api.py ./
COPY app ./app
COPY gunicorn_conf.py ./

# Install dependencies
RUN uv sync --frozen

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Command to run the app with Gunicorn
# The actual command is often overridden in docker-compose, but this is a good default.
CMD ["uv", "run", "gunicorn", "-c", "gunicorn_conf.py", "api:app"]
