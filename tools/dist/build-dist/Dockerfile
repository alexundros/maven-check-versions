FROM python:3.13-alpine
WORKDIR /build
COPY README.md LICENSE VERSION pyproject.toml src ./
RUN pip install build
RUN python -m build