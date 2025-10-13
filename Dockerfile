FROM python:3.10-alpine

# Setup the port to expose
EXPOSE 9100/tcp

# How to stop the container
STOPSIGNAL SIGINT

# Setup the running user
RUN addgroup --gid 10001 xenexporter && \
    adduser --uid 10001 xenexporter --gid 1001

# Install dependencies
COPY --chown=0:0 --chmod=0644 ./requirements.txt /app/requirements.txt
RUN python3 -m pip install -r /app/requirements.txt

# Install the actual script
COPY --chown=0:0 --chmod=0644 ./xen-exporter.py /app/xen-exporter.py

# How to start the script
USER 10001
ENTRYPOINT [ "python3", "/app/xen-exporter.py" ]
