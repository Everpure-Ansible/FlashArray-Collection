#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2026, Simon Dodsley (simon@everpuredata.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: purefa_metrics
version_added: '1.46.0'
short_description: Collect OpenMetrics data from a Everpure FlashArray
description:
  - Reads the OpenMetrics exporter built into Purity//FA 6.7.0 and later, and
    returns what it publishes as structured data.
  - The exporter is not part of the REST API and has no py-pure-client method,
    so this module reads it over HTTPS directly.
  - Returns every metric by default, or a chosen resource group, named metrics,
    or individual components of a metric.
  - Read-only. This module never reports a change and is safe in check mode.
author:
  - Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  subset:
    description:
      - Which of the exporter's six endpoints to read.
      - C(all) reads every metric the array publishes. The array warns that
        this endpoint is slower than the others, and it returns by far the most
        data.
      - C(array) collects the C(purefa_info), C(purefa_alerts),
        C(purefa_array), C(purefa_hw), C(purefa_network) and C(purefa_drive)
        instruments.
      - C(directories) collects C(purefa_info) and C(purefa_directory). This
        endpoint can be slow to answer - see the note on polling intervals.
      - C(hosts) collects C(purefa_info) and C(purefa_host).
      - C(pods) collects C(purefa_info) and C(purefa_pod).
      - C(volumes) collects C(purefa_info) and C(purefa_volume).
      - C(purefa_info) is therefore present whichever endpoint is read.
    type: str
    default: all
    choices: [ all, array, volumes, hosts, pods, directories ]
  metrics:
    description:
      - Names of the metrics to return, such as
        C(purefa_hw_component_temperature_celsius).
      - Omit to return every metric the chosen I(subset) publishes.
      - The exporter has no server-side filtering, so the whole endpoint is
        read either way and this selects from the result.
      - Naming a metric the array does not publish fails the task, listing what
        is available. Which metrics exist varies with Purity version and array
        configuration.
    type: list
    elements: str
  labels:
    description:
      - Return only the samples whose labels match every one of these label
        names and values.
      - This is how an individual component of a metric is selected - a
        C(component_name) of C(CT0.TMP0) for one temperature sensor, or a
        C(component_type) of C(temp_sensor) for all of them.
      - Label names and values are those the exporter publishes, and are
        matched exactly.
    type: dict
  include_samples:
    description:
      - Whether to return the individual samples of each metric.
      - Set to C(false) to return only each metric's help text, type and sample
        count, which is a cheap way to discover what an array publishes without
        carrying the values back.
    type: bool
    default: true
  raw:
    description:
      - Additionally return the exporter's response as unparsed OpenMetrics
        exposition text, under C(raw).
      - I(metrics) and I(labels) do not apply to it. It is the whole response
        for the chosen I(subset).
    type: bool
    default: false
  validate_certs:
    description:
      - Whether to verify the array's TLS certificate.
      - FlashArrays ship with a self-signed certificate, which does not
        validate, so this defaults to C(false) to match the behaviour of the
        rest of this collection. Set it to C(true) on an array that has been
        given a certificate signed by a trusted CA.
    type: bool
    default: false
  timeout:
    description:
      - Seconds to wait for the array to answer.
    type: int
    default: 60
extends_documentation_fragment:
  - everpure.flasharray.everpure.fa
notes:
  - Requires Purity//FA 6.7.0 or later, which is where the exporter was moved
    inside Purity. An earlier array serves the exporter's HTML index page
    instead of metrics, which this module reports as an error.
  - The exporter authenticates with the API token as a bearer credential, so
    this module needs I(api_token) or the C(PUREFA_API) environment variable.
    It cannot use the I(id_token) or I(private_key_file) authentication modes
    that the rest of the collection accepts, because the exporter rejects
    everything but an API token.
  - The endpoint is rate limited. This module makes one request per task, but a
    tight loop over it can still be refused.
  - On how often to read it - the Prometheus configuration examples published
    with Purity//FA use a scrape interval of 60 seconds for every endpoint
    except C(directories), which they set to 30 minutes because it can take a
    long time to respond. A playbook polling this module repeatedly is doing
    the same job as a scrape, so the same intervals are a sensible guide, and
    I(timeout) may need raising for C(subset=directories) on an array with
    many managed directories.
"""

EXAMPLES = r"""
- name: Collect every metric the array publishes
  everpure.flasharray.purefa_metrics:
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: metrics

- name: Collect only the array-level metrics
  everpure.flasharray.purefa_metrics:
    subset: array
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Read one metric, every component of it
  everpure.flasharray.purefa_metrics:
    subset: array
    metrics:
      - purefa_hw_component_temperature_celsius
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: temperatures

- name: Read one metric for a single component
  everpure.flasharray.purefa_metrics:
    subset: array
    metrics:
      - purefa_hw_component_temperature_celsius
    labels:
      component_name: CT0.TMP0
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Read the write bandwidth of one volume
  everpure.flasharray.purefa_metrics:
    subset: volumes
    metrics:
      - purefa_volume_performance_bandwidth_bytes
    labels:
      name: database01
      dimension: write_bytes_per_sec
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Discover what an array publishes, without the values
  everpure.flasharray.purefa_metrics:
    include_samples: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Pass the exposition text on to something that speaks OpenMetrics
  everpure.flasharray.purefa_metrics:
    raw: true
    include_samples: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: exposition

- name: Fail when any hardware component is not ok
  everpure.flasharray.purefa_metrics:
    subset: array
    metrics:
      - purefa_hw_component_status
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: hardware
  failed_when: >-
    hardware.purefa_metrics.purefa_hw_component_status.samples
    | selectattr('labels.component_status', 'ne', 'ok')
    | list | length > 0
"""

RETURN = r"""
purefa_metrics:
  description:
    - The metrics read from the array, keyed by metric name.
  returned: always
  type: dict
  contains:
    help:
      description: The metric's description, as the exporter publishes it.
      type: str
      sample: FlashArray hardware component temperature
    type:
      description:
        - The OpenMetrics instrument type. Every metric the exporter currently
          publishes is a gauge.
      type: str
      sample: gauge
    sample_count:
      description:
        - How many samples the metric has, before I(labels) filtering.
      type: int
      sample: 55
    samples:
      description:
        - One entry per labelled time series, omitted when
          I(include_samples=false).
        - A value the exporter reports as C(NaN), C(+Inf) or C(-Inf) is
          returned as C(none), because JSON has no representation for those.
      type: list
      elements: dict
      contains:
        labels:
          description: The sample's labels.
          type: dict
        value:
          description: The sample's value.
          type: float
  sample:
    purefa_hw_component_temperature_celsius:
      help: FlashArray hardware component temperature
      type: gauge
      sample_count: 2
      samples:
        - labels:
            component_name: CT0.TMP0
            component_type: temp_sensor
          value: 30.0
        - labels:
            component_name: CT1.TMP0
            component_type: temp_sensor
          value: 31.0
raw:
  description:
    - The exporter's unparsed OpenMetrics exposition text, when I(raw=true).
  returned: when I(raw=true)
  type: str
"""

from math import isfinite
from os import environ

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    purefa_argument_spec,
)

# The exporter's own index page lists these, and they are the only paths it
# serves. An unrecognised path returns that HTML page with a 200, rather than
# a 404, so a typo has to be caught by the choices in the argument spec.
ENDPOINTS = {
    "all": "/metrics",
    "array": "/metrics/array",
    "volumes": "/metrics/volumes",
    "hosts": "/metrics/hosts",
    "pods": "/metrics/pods",
    "directories": "/metrics/directories",
}
# Required, and the only value the exporter accepts. Anything else is a 400
# naming the valid values.
NAMESPACE = "purefa"


def _parse_labels(text):
    """Parse the label section of a sample line into a dict

    Walks the string rather than splitting on commas, because a label value is
    a quoted string that may itself contain a comma, and may escape a quote, a
    backslash or a newline.
    """
    labels = {}
    index = 0
    length = len(text)
    while index < length:
        equals = text.find("=", index)
        if equals == -1:
            break
        name = text[index:equals].strip().strip(",").strip()
        if equals + 1 >= length or text[equals + 1] != '"':
            break
        index = equals + 2
        characters = []
        while index < length:
            character = text[index]
            if character == "\\" and index + 1 < length:
                following = text[index + 1]
                characters.append(
                    {"n": "\n", '"': '"', "\\": "\\"}.get(following, following)
                )
                index += 2
                continue
            if character == '"':
                index += 1
                break
            characters.append(character)
            index += 1
        if name:
            labels[name] = "".join(characters)
        while index < length and text[index] in ", ":
            index += 1
    return labels


def _parse_value(text):
    """Return a sample's value as a float, or None if it has no finite value

    Values arrive as doubles, often in scientific notation. The format also
    permits NaN, +Inf and -Inf, none of which JSON can carry, so those become
    None rather than something a playbook cannot serialise.
    """
    try:
        value = float(text)
    except ValueError:
        return None
    if not isfinite(value):
        return None
    return value


def _split_sample(line):
    """Split a sample line into its metric name, label text and value

    A sample is C(name{labels} value) or C(name value), optionally followed by
    a timestamp which the exporter does not currently emit.
    """
    brace = line.find("{")
    if brace != -1:
        close = line.rfind("}")
        if close == -1:
            return None
        name = line[:brace].strip()
        label_text = line[brace + 1 : close]
        remainder = line[close + 1 :].split()
    else:
        parts = line.split()
        if len(parts) < 2:
            return None
        name = parts[0]
        label_text = ""
        remainder = parts[1:]
    if not name or not remainder:
        return None
    return name, label_text, remainder[0]


def parse_exposition(text):
    """Parse OpenMetrics exposition text into a dict keyed by metric name"""
    metrics = {}

    def entry(name):
        return metrics.setdefault(
            name, {"help": None, "type": None, "sample_count": 0, "samples": []}
        )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            parts = line.split(None, 3)
            # "# HELP <name> <text>" and "# TYPE <name> <type>". Anything else
            # is a plain comment.
            if len(parts) >= 3 and parts[1] == "HELP":
                entry(parts[2])["help"] = parts[3] if len(parts) > 3 else ""
            elif len(parts) >= 4 and parts[1] == "TYPE":
                entry(parts[2])["type"] = parts[3]
            continue
        split = _split_sample(line)
        if not split:
            continue
        name, label_text, value = split
        metric = entry(name)
        metric["samples"].append(
            {"labels": _parse_labels(label_text), "value": _parse_value(value)}
        )
        metric["sample_count"] += 1
    return metrics


def select_metrics(module, metrics):
    """Narrow the parsed metrics to what the task asked for"""
    wanted = module.params["metrics"]
    if wanted:
        missing = sorted(set(wanted) - set(metrics))
        if missing:
            module.fail_json(
                msg="This array does not publish {0}. It publishes: {1}".format(
                    ", ".join(missing), ", ".join(sorted(metrics))
                )
            )
        metrics = {name: metrics[name] for name in sorted(set(wanted))}

    labels = module.params["labels"]
    if labels:
        wanted_labels = {key: str(value) for key, value in labels.items()}
        filtered = {}
        for name, metric in metrics.items():
            matching = [
                sample
                for sample in metric["samples"]
                if all(
                    sample["labels"].get(key) == value
                    for key, value in wanted_labels.items()
                )
            ]
            filtered[name] = dict(metric, samples=matching)
        metrics = filtered

    if not module.params["include_samples"]:
        metrics = {
            name: {key: value for key, value in metric.items() if key != "samples"}
            for name, metric in metrics.items()
        }
    return metrics


def read_exposition(module):
    """Read the exporter, returning its response body as text"""
    target = module.params["fa_url"] or environ.get("PUREFA_URL")
    token = module.params["api_token"] or environ.get("PUREFA_API")
    if not target:
        module.fail_json(
            msg="You must set the fa_url argument or the PUREFA_URL "
            "environment variable."
        )
    if not token:
        module.fail_json(
            msg="purefa_metrics requires an API token, set with the api_token "
            "argument or the PUREFA_API environment variable. The OpenMetrics "
            "exporter authenticates with the API token as a bearer credential "
            "and rejects the id_token and private_key_file authentication "
            "modes the rest of this collection accepts."
        )
    # fa_url is documented as an address or hostname, but tolerate someone
    # passing a URL rather than building https://https://...
    host = target.split("://", 1)[-1].strip("/")
    url = "https://{0}{1}?namespace={2}".format(
        host, ENDPOINTS[module.params["subset"]], NAMESPACE
    )
    response, info = fetch_url(
        module,
        url,
        headers={"Authorization": "Bearer {0}".format(token)},
        method="GET",
        timeout=module.params["timeout"],
    )
    status = info["status"]
    if status == -1:
        module.fail_json(msg="Failed to reach {0}. Error: {1}".format(url, info["msg"]))
    if status in (400, 401, 403):
        module.fail_json(
            msg="The array refused the request with status {0}: {1}. The "
            "OpenMetrics exporter authenticates with the API token as a "
            "bearer credential - check the token is valid.".format(
                status, info.get("body", b"") or info.get("msg", "")
            )
        )
    if status == 429:
        module.fail_json(
            msg="The array rate limited the request. The OpenMetrics endpoint "
            "refuses bursts of requests - space them out."
        )
    if status != 200:
        module.fail_json(
            msg="Failed to read {0}. Status {1}: {2}".format(
                url, status, info.get("msg", "")
            )
        )
    # An unrecognised path is answered with the exporter's HTML index page and
    # a 200, so the content type is what distinguishes metrics from that page.
    # An array older than 6.7.0 has no exporter at all and answers differently
    # again, which this same check catches.
    content_type = (info.get("content-type") or "").lower()
    if "text/plain" not in content_type:
        module.fail_json(
            msg="{0} did not return OpenMetrics data - the array answered with "
            "content type '{1}'. The built-in OpenMetrics exporter requires "
            "Purity//FA 6.7.0 or later.".format(url, content_type or "unknown")
        )
    return response.read().decode("utf-8")


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            subset=dict(type="str", default="all", choices=sorted(ENDPOINTS)),
            metrics=dict(type="list", elements="str"),
            labels=dict(type="dict"),
            include_samples=dict(type="bool", default=True),
            raw=dict(type="bool", default=False),
            validate_certs=dict(type="bool", default=False),
            timeout=dict(type="int", default=60),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    text = read_exposition(module)
    metrics = parse_exposition(text)
    result = {"changed": False, "purefa_metrics": select_metrics(module, metrics)}
    if module.params["raw"]:
        result["raw"] = text
    module.exit_json(**result)


if __name__ == "__main__":
    main()
