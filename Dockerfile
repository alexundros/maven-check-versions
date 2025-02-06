FROM python:3.13-alpine as base

FROM base as builder
WORKDIR /build
COPY src pyproject.toml requirements.txt ./
RUN pip install --user -r requirements.txt
RUN pip install --user .

FROM base
COPY --from=builder /root/.local /root/.local
WORKDIR /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["maven_check_versions"]