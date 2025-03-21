FROM pypy:3.11-slim AS base

FROM base AS builder
WORKDIR /build
COPY requirements.txt ./
RUN pip install --user -r requirements.txt
COPY src pyproject.toml VERSION ./
RUN pip install --user .

FROM base
COPY --from=builder /root/.local /root/.local
WORKDIR /app
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["maven_check_versions"]