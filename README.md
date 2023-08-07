# xen-exporter
 XCP-ng (XenServer) Prometheus Exporter

Automatically exports _all_ statistics from the [RRD metrics database](https://xapi-project.github.io/xen-api/metrics.html) from Xen.

# Usage

```cmd
docker run -e XEN_USER=root -e XEN_PASSWORD=<password> -e XEN_HOST=<host> -e XEN_SSL_VERIFY=true -p 9100:9100 --rm ghcr.io/mikedombo/xen-exporter:latest
```

> HALT_ON_NO_UUID - optional, false by default. Ignores metrics with no UUID

# Grafana
A Grafana dashboard is [available here](https://grafana.com/grafana/dashboards/16588) (id 16588), which graphs most of the critical metrics
gathered by this exporter.

![Grafana dashboard sample 1](https://grafana.com/api/dashboards/16588/images/12479/image)
![Grafana dashboard sample 2](https://grafana.com/api/dashboards/16588/images/12482/image)



# Example setup for a XenServer cluster

docker-compose.yml

```
version: '2.4'
services:
  xen01:
    container_name: xen01
    image: ghcr.io/mikedombo/xen-exporter:latest
    environment:
      - XEN_HOST=10.10.10.101
      - XEN_USER=root
      - XEN_PASSWORD=s0m3f4ncyp4ssw0rd
      - XEN_SSL_VERIFY=false

  xen02:
    container_name: xen02
    image: ghcr.io/mikedombo/xen-exporter:latest
    environment:
      - XEN_HOST=10.10.10.102
      - XEN_USER=root
      - XEN_PASSWORD=s0m3f4ncyp4ssw0rd
      - XEN_SSL_VERIFY=false
```

prometheus.yml

```
  - job_name: xenserver
    scrape_interval: 60s
    scrape_timeout: 50s
    static_configs:
    - targets:
      - xen01:9100
      - xen02:9100
```

# Limitations

No Prometheus help (comments) or types are currently emitted since all the metrics are being formatted almost entirely automatically.
Meaning that there is no list in the code of what metrics will be emitted, nor is there a list of nice descriptions for each metric type.
When using a cluster, assumes that the username and password of the poolmaster and hosts are the same.

# TODO
- Proper Prometheus help and types for known metrics
- Additional metrics beyond what RRD provides? Perhaps like https://github.com/lovoo/xenstats_exporter
# List of all statistics
<details>

- xen_host_up
- xen_host_avgqu_sz
- xen_host_cpu
- xen_host_cpu_avg
- xen_host_cpu_avg_freq
- xen_host_cpu_c0
- xen_host_cpu_c1
- xen_host_cpu_p0
- xen_host_cpu_p1
- xen_host_cpu_p2
- xen_host_inflight
- xen_host_io_throughput_read
- xen_host_io_throughput_total
- xen_host_io_throughput_write
- xen_host_iops_read
- xen_host_iops_total
- xen_host_iops_write
- xen_host_iowait
- xen_host_latency
- xen_host_loadavg
- xen_host_memory_free_kib
- xen_host_memory_reclaimed
- xen_host_memory_reclaimed_max
- xen_host_memory_total_kib
- xen_host_pif_rx
- xen_host_pif_tx
- xen_host_pool_session_count
- xen_host_pool_task_count
- xen_host_read
- xen_host_read_latency
- xen_host_sr_cache_hits
- xen_host_sr_cache_misses
- xen_host_sr_cache_size
- xen_host_tapdisks_in_low_memory_mode
- xen_host_write
- xen_host_write_latency
- xen_host_xapi_allocation_kib
- xen_host_xapi_free_memory_kib
- xen_host_xapi_live_memory_kib
- xen_host_xapi_memory_usage_kib
- xen_host_xapi_open_fds
- xen_vm_cpu
- xen_vm_memory
- xen_vm_memory_internal_free
- xen_vm_memory_target
- xen_vm_vbd_avgqu_sz
- xen_vm_vbd_inflight
- xen_vm_vbd_io_throughput_read
- xen_vm_vbd_io_throughput_total
- xen_vm_vbd_io_throughput_write
- xen_vm_vbd_iops_read
- xen_vm_vbd_iops_total
- xen_vm_vbd_iops_write
- xen_vm_vbd_iowait
- xen_vm_vbd_latency
- xen_vm_vbd_read
- xen_vm_vbd_read_latency
- xen_vm_vbd_write
- xen_vm_vbd_write_latency
- xen_vm_vif_rx
- xen_vm_vif_tx
- xen_collector_duration_seconds
</details>
