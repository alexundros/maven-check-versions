FROM python:3.11-slim
WORKDIR /build
RUN pip install build
COPY pyproject.toml src ./
RUN python -m build