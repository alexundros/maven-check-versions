FROM python:3.13-alpine
WORKDIR /build
COPY PyPy.md LICENSE VERSION pyproject.toml src ./
RUN pip install build
RUN python -m build