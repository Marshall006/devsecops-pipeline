# ⚠️ Dockerfile VOLONTAIREMENT mal configuré — démonstration uniquement.
FROM python:latest
ADD https://example.com/setup.sh /tmp/setup.sh
RUN apt-get update && apt-get install -y curl
COPY . /app
RUN pip install -r /app/deps.lst
CMD python /app/app.py
