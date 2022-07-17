FROM python:3.10-alpine

COPY . /app

RUN python3 -m pip install -r /app/requirements.txt

EXPOSE 9100/tcp

STOPSIGNAL SIGINT
ENTRYPOINT [ "python3", "/app/xen-exporter.py" ]
