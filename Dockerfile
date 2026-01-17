# =============================================================================
# GPTMarket Generator - Production Dockerfile
# =============================================================================
#
# Multi-stage build for optimized production image.
# Uses uv for fast, reliable dependency management.
#
# Build:
#   docker build -t gptmarket-generator .
#
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build dependencies
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install production dependencies only (no dev extras)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Stage 2: Production image
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS production

# Labels for container registry
LABEL org.opencontainers.image.source="https://github.com/gptmarket/visual-generator"
LABEL org.opencontainers.image.description="GPTMarket Visual Generator - Temporal Worker"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/build/.venv/bin:$PATH"

# Install FFmpeg, fonts, and media tools
# Fonts needed for FFmpeg drawtext filter (Impact, Arial, Helvetica, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg for video processing
    ffmpeg \
    # Font management
    fontconfig \
    # Core fonts for text overlays
    fonts-dejavu-core \
    fonts-dejavu-extra \
    fonts-liberation \
    fonts-liberation2 \
    fonts-freefont-ttf \
    fonts-noto-core \
    fonts-roboto \
    fonts-unifont \
    # Additional fonts for better coverage
    fonts-opensymbol \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/* \
    # Rebuild font cache
    && fc-cache -f -v

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /build/.venv /build/.venv

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY pyproject.toml ./

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash worker
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app.temporal.worker" || exit 1

# Run the Temporal worker
CMD ["python", "-m", "app.temporal.worker"]
