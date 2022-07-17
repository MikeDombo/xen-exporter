# xen-exporter
 XCP-ng (XenServer) Prometheus Exporter

Automatically exports _all_ statistics from the [RRD metrics database](https://xapi-project.github.io/xen-api/metrics.html) from Xen.

# Usage

```cmd
docker run -e XEN_USER=root -e XEN_PASSWORD=<password> -e XEN_HOST=<host> -e XEN_SSL_VERIFY=true -p 9100:9100 --rm ghcr.io/mikedombo/xen-exporter:latest
```
