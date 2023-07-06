import base64
import http.server
import urllib.request
import time
import ssl
import os
import re

import pyjson5
import XenAPI


# We aggressively cache the SRs, VMs, and hosts to avoid calling XAPI which can double the runtime (~0.8s to ~1.5s)
# Mapping from UUID to human readable name
srs = dict()
vms = dict()
hosts = dict()
all_srs = set()


def lookup_vm_name(vm_uuid, session):
    return session.xenapi.VM.get_name_label(session.xenapi.VM.get_by_uuid(vm_uuid))


def lookup_sr_name_by_uuid(sr_uuid, session):
    try:
       return session.xenapi.SR.get_name_label(session.xenapi.SR.get_by_uuid(sr_uuid))
    except XenAPI.XenAPI.Failure:
       return sr_uuid


def lookup_host_name(host_uuid, session):
    return session.xenapi.host.get_name_label(
        session.xenapi.host.get_by_uuid(host_uuid)
    )


def lookup_sr_uuid_by_ref(sr_ref, session):
    return session.xenapi.SR.get_uuid(sr_ref)


def find_full_sr_uuid(beginning_uuid, xen, halt_on_no_uuid):
    for i in range(0, 2):
        uuid = list(filter(lambda x: x.startswith(beginning_uuid), all_srs))
        if len(uuid) == 0:
            all_srs.update(
                set(
                    map(
                        lambda x: lookup_sr_uuid_by_ref(x, xen),
                        xen.xenapi.SR.get_all(),
                    )
                )
            )
            continue  # skip the rest of the loop and try the search again
        elif len(uuid) > 1:
            raise Exception(
                f"Found multiple SRs starting with UUID {beginning_uuid}"
            )
        uuid = uuid[0]
        return uuid
    if halt_on_no_uuid: raise Exception(f"Found no SRs starting with UUID {beginning_uuid}")


def get_or_set(d, key, func, *args):
    if key not in d:
        d[key] = func(key, *args)
    return d[key]

def collect_poolmaster():
    xen_user = os.getenv("XEN_USER", "root")
    xen_password = os.getenv("XEN_PASSWORD", "")
    xen_host = os.getenv("XEN_HOST", "localhost")
    verify_ssl = "false"
    verify_ssl = True if verify_ssl.lower() == "true" else False
    try:
       with Xen("https://" + xen_host, xen_user, xen_password, verify_ssl) as xen:
          poolmaster = xen_host
    except XenAPI.XenAPI.Failure as e:
       ipPattern = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
       poolmaster = re.findall(ipPattern,str(e))[0]
    return poolmaster

class Xen:
    def __init__(self, url, username, password, verify_ssl):
        self.session = XenAPI.Session(url, ignore_ssl=not verify_ssl)
        self.session.xenapi.login_with_password(
            username, password, "1.0", "xen-exporter"
        )

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.xenapi.session.logout()
        return False


# Known SR metrics whose legends include the beginning of the UUID, rather than the full UUID
sr_metrics = set(
    [
        "io_throughput_total",
        "avgqu_sz",
        "inflight",
        "iops_write",
        "iops_total",
        "io_throughput_read",
        "read",
        "latency",
        "write_latency",
        "write",
        "io_throughput_write",
        "iowait",
        "read_latency",
        "iops_read",
    ]
)


def collect_metrics():
    xen_user = os.getenv("XEN_USER", "root")
    xen_password = os.getenv("XEN_PASSWORD", "")
    xen_host = os.getenv("XEN_HOST", "localhost")
    verify_ssl = os.getenv("XEN_SSL_VERIFY", "true")
    verify_ssl = True if verify_ssl.lower() == "true" else False

    halt_on_no_uuid = os.getenv("HALT_ON_NO_UUID", "false")
    halt_on_no_uuid = True if halt_on_no_uuid.lower() == "true" else False

    xen_poolmaster = collect_poolmaster()
    collector_start_time = time.perf_counter()

    with Xen("https://" + xen_poolmaster, xen_user, xen_password, verify_ssl) as xen:
        url = f"https://{xen_host}/rrd_updates?start={int(time.time()-10)}&json=true&host=true&cf=AVERAGE"

        req = urllib.request.Request(url)
        req.add_header(
            "Authorization",
            "Basic "
            + base64.b64encode((xen_user + ":" + xen_password).encode("utf-8")).decode(
                "utf-8"
            ),
        )
        res = urllib.request.urlopen(
            req, context=None if verify_ssl else ssl._create_unverified_context()
        )
        metrics = pyjson5.decode_io(res)

        output = ""
        for i, metric_name in enumerate(metrics["meta"]["legend"]):
            metric_legend = metric_name.split(":")[1:]
            collector_type = metric_legend[0]
            collector = metric_legend[1]
            metric_type = metric_legend[2]
            extra_tags = {f"{collector_type}": collector}

            if collector_type == "vm":
                vm = get_or_set(vms, collector, lookup_vm_name, xen)
                extra_tags["vm"] = vm
                extra_tags["vm_uuid"] = collector
            elif collector_type == "host":
                host = get_or_set(hosts, collector, lookup_host_name, xen)
                extra_tags["host"] = host
                extra_tags["host_uuid"] = collector

            if collector_type == "host" and "sr_" in metric_type:
                x = metric_type.split("sr_")[1]
                sr = get_or_set(srs, x.split("_")[0], lookup_sr_name_by_uuid, xen)
                extra_tags["sr"] = sr
                extra_tags["sr_uuid"] = x.split("_")[0]
                metric_type = "sr_" + "_".join(x.split("_")[1:])

            # Handle SR metrics which don't have a full UUID (and don't have sr_)
            if (
                collector_type == "host"
                and len(metric_type.split("_")[-1]) == 8
                and "_".join(metric_type.split("_")[0:-1]) in sr_metrics
            ):
                short_sr = metric_type.split("_")[-1]
                long_sr = find_full_sr_uuid(short_sr, xen, halt_on_no_uuid)
                if(long_sr is not None): ## 
                    sr = get_or_set(srs, long_sr, lookup_sr_name_by_uuid, xen)
                    extra_tags["sr"] = sr
                    extra_tags["sr_uuid"] = long_sr
                metric_type = "_".join(metric_type.split("_")[0:-1])

            if collector_type == "vm" and "vbd_" in metric_type:
                x = metric_type.split("vbd_")[1]
                extra_tags["vbd"] = x.split("_")[0]
                metric_type = "vbd_" + "_".join(x.split("_")[1:])

            if collector_type == "vm" and "vif_" in metric_type:
                x = metric_type.split("vif_")[1]
                extra_tags["vif"] = x.split("_")[0]
                metric_type = "vif_" + "_".join(x.split("_")[1:])

            if collector_type == "host" and "pif_" in metric_type:
                x = metric_type.split("pif_")[1]
                extra_tags["pif"] = x.split("_")[0]
                metric_type = "pif_" + "_".join(x.split("_")[1:])

            if "cpu" in metric_type:
                x = metric_type.split("cpu")[1]
                if x.isnumeric():
                    extra_tags["cpu"] = x
                    metric_type = "cpu"
                elif "-" in x:
                    extra_tags["cpu"] = x.split("-")[0]
                    metric_type = "cpu_" + x.split("-")[1]
            if "CPU" in metric_type:
                x = metric_type.split("CPU")[1]
                extra_tags["cpu"] = x.split("-")[0]
                metric_type = "cpu_" + "_".join(x.split("-")[1:])

            # Normalize metric names to lowercase and underscores
            metric_type = metric_type.lower().replace("-", "_")

            tags = {f'{k}="{v}"' for k, v in extra_tags.items()}
            output += f"xen_{collector_type}_{metric_type}{{{', '.join(tags)}}} {metrics['data'][0]['values'][i]}\n"
        collector_end_time = time.perf_counter()
        output += f"xen_collector_duration_seconds {collector_end_time - collector_start_time}\n"
        return output


class Handler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request: bytes, client_address: tuple[str, int], server) -> None:
        super().__init__(request, client_address, server)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(collect_metrics().encode("utf-8"))


if __name__ == "__main__":
    port = os.getenv("PORT", "9100")
    bind = os.getenv("BIND", "0.0.0.0")

    http.server.HTTPServer(
        (
            bind,
            int(port),
        ),
        Handler,
    ).serve_forever()
