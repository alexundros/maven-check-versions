FROM python:3.13-alpine as base
FROM base as builder
COPY requirements.txt /requirements.txt
RUN pip install --user -r /requirements.txt

FROM base
COPY --from=builder /root/.local /root/.local
COPY src /app
WORKDIR /app

ENV PATH=/home/app/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["-ci"]
ENTRYPOINT ["python", "maven_check_versions/__init__.py"]