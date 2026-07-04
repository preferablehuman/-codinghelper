FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin sandbox \
    && mkdir -p /sandbox-work \
    && chown sandbox:sandbox /sandbox-work

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

USER sandbox

EXPOSE 8100

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
