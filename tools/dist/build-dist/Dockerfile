FROM python:3.11-slim
WORKDIR /build
RUN pip install build
COPY README.md LICENSE VERSION pyproject.toml src ./
RUN python -m build