# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_preset module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
import json
import pathlib
import re
import sys
from contextlib import ExitStack
from unittest.mock import Mock, MagicMock, patch

import pytest

# Mock external dependencies before importing module
sys.modules["grp"] = MagicMock()
sys.modules["pwd"] = MagicMock()
sys.modules["fcntl"] = MagicMock()
sys.modules["ansible"] = MagicMock()
sys.modules["ansible.module_utils"] = MagicMock()
sys.modules["ansible.module_utils.basic"] = MagicMock()
sys.modules["pypureclient"] = MagicMock()
sys.modules["pypureclient.flasharray"] = MagicMock()
sys.modules["ansible_collections"] = MagicMock()
sys.modules["ansible_collections.everpure"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils"] = (
    MagicMock()
)
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.purefa"] = (
    MagicMock()
)
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()

import plugins.modules.purefa_preset as preset_module
from plugins.modules.purefa_preset import (
    CONFIG_SECTIONS,
    Decision,
    _error_text,
    _is_absent,
    build_body,
    carry_over_naming,
    changed_sections,
    decide,
    normalise_preset,
    not_a_block_preset,
    validate_preset,
)

FLEET = "ansibledev"
FIXTURES = pathlib.Path(__file__).resolve().with_name("fixtures")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _ApiObject:
    """Stands in for an API object, which Mock cannot.

    Reading a field whose value is null raises AttributeError on the objects the
    SDK builds, rather than returning None, and so does reading a field they do not
    define. Mock returns a value for everything, so a Mock-based fixture cannot
    express a response the array described with nulls.
    """

    def __init__(self, **fields):
        self._fields = fields

    def __getattr__(self, name):
        try:
            value = self._fields[name]
        except KeyError:
            raise AttributeError(name) from None
        if value is None:
            raise AttributeError(name)
        return value


class _ApiPreset(_ApiObject):
    """A preset item, which the module reads through to_dict()"""

    def __init__(self, fields):
        super().__init__(**fields)
        self._dict = fields

    def to_dict(self):
        return copy.deepcopy(self._dict)


class _Model:
    """What a patched model class builds: the class it stands for, and its fields"""

    def __init__(self, kind, **kwargs):
        self.kind = kind
        self.kwargs = kwargs


def _error_response(status_code, *messages):
    return Mock(
        status_code=status_code,
        errors=[_ApiObject(message=m) for m in messages],
        items=None,
    )


def _ok(items=()):
    return Mock(status_code=200, items=list(items), errors=None)


def _reference(name):
    return {"name": name, "parameter": None}


def _volume(name="data", **overrides):
    """A volumes entry as AnsibleModule fills it in: every suboption present"""
    volume = {
        "name": name,
        "count": "1",
        "provisioned_size": "1073741824",
        "placement": None,
        "snapshots": None,
        "replications": None,
        "naming_template": None,
    }
    volume.update(overrides)
    return volume


def _rule(every="3600000", keep_for="86400000", at=None, suffix=None):
    return {"every": every, "keep_for": keep_for, "at": at, "suffix": suffix}


def _snapshot(name="hourly", rules=None, **overrides):
    snapshot = {
        "name": name,
        "policy_action": "create_or_reuse",
        "rules": [_rule()] if rules is None else rules,
        "naming_template": None,
    }
    snapshot.update(overrides)
    return snapshot


def _replication(name="offsite", target="arrayB", rules=None, **overrides):
    replication = {
        "name": name,
        "target": _reference(target),
        "rules": (
            [_rule("86400000", "604800000", "7200000")] if rules is None else rules
        ),
        "naming_template": None,
    }
    replication.update(overrides)
    return replication


def _qos(name="q1", **overrides):
    qos = {
        "name": name,
        "iops_limit": "50000",
        "bandwidth_limit": "1073741824",
        "naming_template": None,
    }
    qos.update(overrides)
    return qos


def _tag(key="app", value="postgres", **overrides):
    tag = {"key": key, "value": value, "namespace": "default", "copyable": True}
    tag.update(overrides)
    return tag


def _param(name, ptype, **overrides):
    param = {
        "name": name,
        "type": ptype,
        "display_name": None,
        "description": None,
        "subtype": None,
        "default": None,
        "allowed_values": None,
        "minimum": None,
        "maximum": None,
        "resource_type": None,
    }
    param.update(overrides)
    return param


def _params(**overrides):
    """A full, valid set of task parameters, as AnsibleModule would hand them over"""
    params = {
        "fa_url": "10.0.0.1",
        "api_token": "token",
        "name": "app",
        "new_name": None,
        "state": "present",
        "workload_type": "PostgreSQL",
        "description": "A test preset",
        "placement": {
            "name": "pl",
            "storage_class": _reference("flasharray-x"),
            "qos": "q1",
            "targets": [_reference("arrayB")],
        },
        "volumes": [
            _volume(
                count="2",
                provisioned_size="107374182400",
                snapshots=["hourly"],
                replications=["offsite"],
            )
        ],
        "qos": [_qos()],
        "snapshots": [_snapshot()],
        "replications": [_replication()],
        "parameters": [
            _param(
                "env",
                "string",
                default="dev",
                allowed_values=["dev", "test", "prod"],
            )
        ],
        "tags": [
            _tag(),
            _tag("environment", "{{ parameters.env }}", copyable=False),
        ],
        "skip_verify_deployable": False,
    }
    params.update(overrides)
    return params


def _minimal_params(**overrides):
    """The smallest valid block preset: one placement and one volume"""
    params = _params(
        description=None,
        placement={
            "name": "default-placement",
            "storage_class": _reference("flasharray-x"),
            "qos": None,
            "targets": None,
        },
        volumes=[_volume()],
        qos=None,
        snapshots=None,
        replications=None,
        parameters=None,
        tags=None,
    )
    params.update(overrides)
    return params


def _server_form(body, name="app", revision=1):
    """A body as the array reads it back, which is not the way it was written

    Defaults are filled in, empty sections come back as null or [] as it pleases,
    lists are in no particular order, and the preset is wrapped in the fields the
    array owns.
    """
    preset = copy.deepcopy(body)
    for section in CONFIG_SECTIONS:
        # A placement names nothing, so the array gives it no template and
        # its model has no field for one (Purity//FA 6.10.6, REST 2.54)
        fills_template = section != "placement_configurations"
        for config in preset.get(section) or []:
            if fills_template and not config.get("naming_patterns"):
                config["naming_patterns"] = [
                    {"template": "{{ workload.name }}-%s" % config["name"]}
                ]
            for rule in config.get("rules") or []:
                rule.setdefault("suffix", "")
                rule.setdefault("time_zone", "")
    for index, section in enumerate(
        (
            "description",
            "parameters",
            "periodic_replication_configurations",
            "qos_configurations",
            "snapshot_configurations",
            "workload_tags",
        )
    ):
        preset.setdefault(section, None if index % 2 else [])
    for section in CONFIG_SECTIONS + ("parameters", "workload_tags"):
        if preset.get(section):
            preset[section] = list(reversed(preset[section]))
    preset.update(
        id="0f8f4b36-0000-4000-8000-000000000001",
        name=name,
        revision=revision,
        context={"name": FLEET},
        platform_features=["fa_block"],
        directory_configurations=[],
        export_configurations=None,
        quota_configurations=[],
    )
    return preset


class _FakeFleet:
    """An array in a fleet, holding presets and recording every call made to it

    Reads come from the store. Writes are recorded in calls, and change the store the
    way the array does, so that a second run sees what the first one left.
    """

    def __init__(self, store=None, fail=None, fleets=True):
        self.store = {} if store is None else store
        self.fail = fail or {}
        self.calls = []
        self.fleets = fleets

    def get_fleets(self):
        self.calls.append(("get_fleets", {}))
        if not self.fleets:
            return _ok([])
        return _ok([_ApiObject(name=FLEET)])

    def get_presets_workload(self, **kwargs):
        self.calls.append(("get", kwargs))
        if "get" in self.fail:
            return self.fail["get"]
        if "get_after_write" in self.fail and self.writes():
            return self.fail["get_after_write"]
        name = kwargs["names"][0]
        if name not in self.store:
            return _error_response(400, "Preset does not exist.")
        return _ok([_ApiPreset(copy.deepcopy(self.store[name]))])

    def post_presets_workload(self, **kwargs):
        self.calls.append(("post", kwargs))
        if "post" in self.fail:
            return self.fail["post"]
        name = kwargs["names"][0]
        self.store[name] = _server_form(kwargs["preset"].kwargs, name)
        return _ok()

    def put_presets_workload(self, **kwargs):
        self.calls.append(("put", kwargs))
        if "put" in self.fail:
            return self.fail["put"]
        name = kwargs["names"][0]
        old = self.store[name]
        self.store[name] = _server_form(
            kwargs["preset"].kwargs, name, old["revision"] + 1
        )
        return _ok()

    def patch_presets_workload(self, **kwargs):
        self.calls.append(("patch", kwargs))
        if "patch" in self.fail:
            return self.fail["patch"]
        new = kwargs["preset"].kwargs["name"]
        preset = self.store.pop(kwargs["names"][0])
        preset["name"] = new
        self.store[new] = preset
        return _ok()

    def delete_presets_workload(self, **kwargs):
        self.calls.append(("delete", kwargs))
        if "delete" in self.fail:
            return self.fail["delete"]
        self.store.pop(kwargs["names"][0])
        return _ok()

    def writes(self):
        return [c for c in self.calls if c[0] in ("post", "put", "patch", "delete")]

    def kinds(self):
        return [c[0] for c in self.calls if c[0] != "get_fleets"]


class _Exit(Exception):
    def __init__(self, kwargs):
        super().__init__("exit_json")
        self.kwargs = kwargs


class _Fail(Exception):
    def __init__(self, kwargs):
        super().__init__(kwargs.get("msg"))
        self.kwargs = kwargs


class _Run:
    """The outcome of one main()"""

    def __init__(self):
        self.kind = None
        self.result = None
        self.module = None
        self.array = None
        self.api_check = None
        self.get_array = None
        self.models = None
        self.argument_spec = None
        self.module_kwargs = None


def _run_main(
    params,
    array=None,
    check_mode=False,
    diff=False,
    sdk=True,
    api_check=None,
    reject=None,
):
    """Run main() against a fake fleet, returning what it did

    The SDK models are replaced by builders that keep their arguments, so a test
    reads what was sent, not that something was. reject maps a model name to the
    exception the real model would raise for the body. The module's own parameter
    handling is replaced too, since AnsibleModule is a mock here.
    """
    array = _FakeFleet() if array is None else array
    module = Mock()
    module.params = copy.deepcopy(params)
    module.check_mode = check_mode
    module._diff = diff

    def fail_json(**kwargs):
        raise _Fail(kwargs)

    def exit_json(**kwargs):
        raise _Exit(kwargs)

    module.fail_json.side_effect = fail_json
    module.exit_json.side_effect = exit_json
    run = _Run()
    run.module = module
    run.array = array
    run.api_check = Mock() if api_check is None else api_check
    run.get_array = Mock(return_value=array)
    ansible_module = Mock(return_value=module)
    run.models = {
        name: Mock(side_effect=lambda _n=name, **kw: _Model(_n, **kw))
        for name in ("PresetWorkload", "PresetWorkloadPatch", "PresetWorkloadPost")
    }
    for name, error in (reject or {}).items():
        run.models[name] = Mock(side_effect=error)
    with ExitStack() as patches:
        for target, replacement in (
            ("HAS_PURESTORAGE", sdk),
            ("get_array", run.get_array),
            ("AnsibleModule", ansible_module),
            ("purefa_argument_spec", Mock(return_value={})),
            ("check_api_version", run.api_check),
            *run.models.items(),
        ):
            patches.enter_context(
                patch("plugins.modules.purefa_preset.%s" % target, replacement)
            )
        try:
            preset_module.main()
        except _Exit as exit_:
            run.kind = "exit"
            run.result = exit_.kwargs
        except _Fail as fail:
            run.kind = "fail"
            run.result = fail.kwargs
    run.argument_spec = (
        ansible_module.call_args[0][0] if ansible_module.called else None
    )
    run.module_kwargs = ansible_module.call_args[1] if ansible_module.called else None
    return run


def _stored(params, name="app", revision=3):
    """The preset on the fleet when it was made from these task parameters"""
    return _server_form(build_body(params), name, revision)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def _set(path, value):
    """A change to the valid parameters: set value at a dotted path"""

    def apply(params):
        node = params
        keys = path.split(".")
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        last = keys[-1]
        if isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value

    return apply


def _many(*changes):
    def apply(params):
        for change in changes:
            change(params)

    return apply


def _drop_param(name):
    def apply(params):
        params["parameters"] = [p for p in params["parameters"] if p["name"] != name]

    return apply


VALIDATION_CASES = [
    ("no-workload-type", _set("workload_type", None), "workload_type is required"),
    (
        "bogus-workload-type",
        _set("workload_type", "Bogus"),
        "workload_type 'Bogus' is not one of",
    ),
    (
        "long-description",
        _set("description", "x" * 1025),
        "description is longer than 1024",
    ),
    ("no-placement", _set("placement", None), "needs a placement"),
    ("no-volumes", _set("volumes", []), "at least one entry in volumes"),
    (
        "six-volumes",
        _set("volumes", [_volume("v%d" % i) for i in range(6)]),
        "volumes has 6 entries",
    ),
    (
        "two-qos",
        _set("qos", [_qos("q1"), _qos("q2")]),
        "qos has 2 entries, at most 1 is allowed",
    ),
    (
        "three-snapshots",
        _many(
            _set("snapshots", [_snapshot("s1"), _snapshot("s2"), _snapshot("s3")]),
            _set("volumes.0.snapshots", ["s1", "s2", "s3"]),
        ),
        "snapshots has 3 entries, at most 2 are allowed",
    ),
    (
        "three-replications",
        _many(
            _set(
                "replications",
                [_replication("r1"), _replication("r2"), _replication("r3")],
            ),
            _set("volumes.0.replications", ["r1", "r2", "r3"]),
        ),
        "replications has 3 entries, at most 2 are allowed",
    ),
    (
        "volume-named-like-placement",
        _set("volumes.0.name", "pl"),
        "configuration name 'pl' is used by a placement and a volume",
    ),
    (
        "snapshot-named-like-volume",
        _set("snapshots.0.name", "data"),
        "'data' is used by a volume and a snapshot",
    ),
    (
        "replication-named-like-qos",
        _set("replications.0.name", "q1"),
        "'q1' is used by a qos and a replication",
    ),
    ("empty-volume-name", _set("volumes.0.name", ""), "has an empty name"),
    (
        "placement-qos-undefined",
        _set("placement.qos", "nope"),
        "placement qos refers to 'nope', which is not defined in qos",
    ),
    (
        "no-storage-class",
        _set("placement.storage_class", None),
        "placement needs a storage_class",
    ),
    (
        "storage-class-both",
        _set("placement.storage_class", {"name": "flasharray-x", "parameter": "env"}),
        "placement storage_class needs exactly one of name and parameter",
    ),
    (
        "storage-class-neither",
        _set("placement.storage_class", {"name": None, "parameter": None}),
        "placement storage_class needs exactly one of name and parameter",
    ),
    (
        "storage-class-name-is-a-template",
        _set(
            "placement.storage_class",
            {"name": "{{ parameters.env }}", "parameter": None},
        ),
        "placement storage_class name '{{ parameters.env }}' is a parameter "
        "reference. Give the parameter's name with parameter instead of name",
    ),
    (
        "target-name-is-a-template",
        _set(
            "placement.targets", [{"name": "{{ parameters.env }}", "parameter": None}]
        ),
        "placement target name '{{ parameters.env }}' is a parameter reference",
    ),
    (
        "two-targets",
        _set("placement.targets", [_reference("a"), _reference("b")]),
        "placement targets has 2 entries, at most 1 is allowed",
    ),
    (
        "target-neither",
        _set("placement.targets", [{"name": None, "parameter": None}]),
        "placement target needs exactly one of name and parameter",
    ),
    (
        "target-both",
        _set("placement.targets", [{"name": "arrayB", "parameter": "env"}]),
        "placement target needs exactly one of name and parameter",
    ),
    (
        "volume-placement-undefined",
        _set("volumes.0.placement", "other"),
        "refers to placement 'other', which is not defined. The placement is 'pl'",
    ),
    (
        "volume-snapshot-undefined",
        _set("volumes.0.snapshots", ["hourly", "nope"]),
        "refers to snapshot configuration 'nope'",
    ),
    (
        "volume-replication-undefined",
        _set("volumes.0.replications", ["nope"]),
        "refers to replication configuration 'nope'",
    ),
    (
        "volume-snapshot-listed-twice",
        _set("volumes.0.snapshots", ["hourly", "hourly"]),
        "volume 'data' lists snapshot configuration 'hourly' more than once",
    ),
    (
        "volume-replication-listed-twice",
        _set("volumes.0.replications", ["offsite", "offsite"]),
        "volume 'data' lists replication configuration 'offsite' more than once",
    ),
    (
        "count-not-a-number",
        _set("volumes.0.count", "abc"),
        "count must be a whole number or a parameter reference",
    ),
    ("count-zero", _set("volumes.0.count", "0"), "count must be at least 1"),
    (
        "count-over-total",
        _set("volumes.0.count", "501"),
        "the volume counts add up to 501, at most 500 are allowed",
    ),
    (
        "counts-add-up",
        _set("volumes", [_volume("a", count="300"), _volume("b", count="300")]),
        "add up to 600",
    ),
    (
        "size-not-512-multiple",
        _set("volumes.0.provisioned_size", "1000"),
        "provisioned_size must be a multiple of 512",
    ),
    (
        "size-too-small",
        _set("volumes.0.provisioned_size", "0"),
        "provisioned_size must be at least 512",
    ),
    (
        "size-too-big",
        _set("volumes.0.provisioned_size", "4503599627370497"),
        "provisioned_size must be at most 4503599627370496",
    ),
    (
        "size-negative",
        _set("volumes.0.provisioned_size", "-512"),
        "provisioned_size must be a whole number",
    ),
    (
        "iops-too-low",
        _set("qos.0.iops_limit", "99"),
        "iops_limit must be at least 100",
    ),
    (
        "iops-too-high",
        _set("qos.0.iops_limit", "100000001"),
        "iops_limit must be at most 100000000",
    ),
    (
        "bandwidth-too-low",
        _set("qos.0.bandwidth_limit", "1048575"),
        "bandwidth_limit must be at least 1048576",
    ),
    (
        "bandwidth-too-high",
        _set("qos.0.bandwidth_limit", str(512 * 1024**3 + 1)),
        "bandwidth_limit must be at most",
    ),
    (
        "qos-unused",
        _set("placement.qos", None),
        "qos 'q1' is not used. Set placement qos to use it",
    ),
    (
        "snapshot-unused",
        _set("volumes.0.snapshots", None),
        "snapshot 'hourly' is not used",
    ),
    (
        "replication-unused",
        _set("volumes.0.replications", None),
        "replication 'offsite' is not used",
    ),
    (
        "snapshot-no-rules",
        _set("snapshots.0.rules", []),
        "snapshot 'hourly' needs at least one rule",
    ),
    (
        "snapshot-three-rules",
        _set(
            "snapshots.0.rules",
            [_rule("1000", "2000"), _rule("2000", "4000"), _rule("4000", "8000")],
        ),
        "has 3 rules, at most 2 are allowed",
    ),
    (
        "keep-for-shorter-than-every",
        _set("snapshots.0.rules", [_rule("3600000", "1800000")]),
        "keep_for (1800000) must not be shorter than every (3600000)",
    ),
    (
        "at-on-second-rule",
        _set(
            "snapshots.0.rules",
            [_rule("86400000", "86400000"), _rule("172800000", "172800000", "5")],
        ),
        "at can only be set on the first rule",
    ),
    (
        "at-without-whole-days",
        _set("snapshots.0.rules", [_rule("3600000", "86400000", "100")]),
        "at can only be set when every is a whole number of days",
    ),
    (
        "at-a-whole-day",
        _set("snapshots.0.rules", [_rule("86400000", "86400000", "86400000")]),
        "at must be less than 86400000",
    ),
    (
        "two-suffixes",
        _set(
            "snapshots.0.rules",
            [
                _rule("1000", "2000", suffix="a"),
                _rule("2000", "4000", suffix="b"),
            ],
        ),
        "sets a suffix on more than one rule",
    ),
    (
        "suffix-not-on-longest-keep",
        _set(
            "snapshots.0.rules",
            [
                _rule("1000", "2000", suffix="a"),
                _rule("2000", "4000"),
            ],
        ),
        "suffix on the rule with the largest keep_for",
    ),
    (
        "intervals-not-multiples",
        _set(
            "snapshots.0.rules",
            [_rule("3600000", "86400000"), _rule("5400000", "86400000")],
        ),
        "intervals 3600000 and 5400000 are not multiples of each other",
    ),
    (
        "rule-every-not-a-number",
        _set("snapshots.0.rules", [_rule("hourly", "86400000")]),
        "rule 1 every must be a whole number",
    ),
    (
        "replication-target-neither",
        _set("replications.0.target", {"name": None, "parameter": None}),
        "replication 'offsite' target needs exactly one of name and parameter",
    ),
    (
        "replication-target-both",
        _set("replications.0.target", {"name": "arrayB", "parameter": "env"}),
        "replication 'offsite' target needs exactly one of name and parameter",
    ),
    (
        "replication-target-name-is-a-template",
        _set(
            "replications.0.target",
            {"name": "{{ parameters.env }}", "parameter": None},
        ),
        "replication 'offsite' target name '{{ parameters.env }}' is a parameter "
        "reference",
    ),
    (
        "replication-no-rules",
        _set("replications.0.rules", []),
        "replication 'offsite' needs at least one rule",
    ),
    # The inputs the array answers with a 500, or accepts and breaks on later
    ("tag-no-value", _set("tags.0.value", None), "tag 'app' needs a value"),
    ("tag-empty-value", _set("tags.0.value", ""), "tag 'app' needs a value"),
    (
        "tag-long-value",
        _set("tags.0.value", "x" * 257),
        "tag 'app' value is longer than 256 characters",
    ),
    ("tag-no-key", _set("tags.0.key", ""), "a tag has an empty key"),
    (
        "tag-long-key",
        _set("tags.0.key", "k" * 65),
        "key is longer than 64 characters",
    ),
    (
        "tag-duplicate",
        _set("tags", [_tag("app", "a"), _tag("app", "b")]),
        "tag key 'app' is set more than once in namespace 'default'",
    ),
    (
        "parameter-bad-name",
        _set("parameters", [_param("my-param", "string")]),
        "parameter names may only contain letters, numbers and _",
    ),
    (
        "parameter-duplicate",
        _set("parameters", [_param("env", "string"), _param("env", "string")]),
        "parameter 'env' is defined more than once",
    ),
    (
        "string-with-minimum",
        _set("parameters.0.minimum", 1),
        "option minimum is not valid for type string",
    ),
    (
        "string-with-resource-type",
        _set("parameters.0.resource_type", "storage-classes"),
        "option resource_type is not valid for type string",
    ),
    (
        "string-with-subtype",
        _set("parameters.0.subtype", "size"),
        "option subtype is not valid for type string",
    ),
    (
        "boolean-with-subtype",
        _set("parameters", [_param("env", "boolean", subtype="size")]),
        "option subtype is not valid for type boolean",
    ),
    (
        "reference-with-subtype",
        _set(
            "parameters",
            [
                _param(
                    "env",
                    "resource_reference",
                    resource_type="remote-arrays",
                    subtype="size",
                )
            ],
        ),
        "option subtype is not valid for type resource_reference",
    ),
    (
        "integer-with-resource-type",
        _set(
            "parameters",
            [_param("env", "integer", resource_type="storage-classes")],
        ),
        "option resource_type is not valid for type integer",
    ),
    (
        "boolean-with-allowed-values",
        _set("parameters", [_param("env", "boolean", allowed_values=["true"])]),
        "option allowed_values is not valid for type boolean",
    ),
    (
        "reference-with-minimum",
        _set(
            "parameters",
            [
                _param(
                    "env",
                    "resource_reference",
                    resource_type="remote-arrays",
                    minimum=1,
                )
            ],
        ),
        "option minimum is not valid for type resource_reference",
    ),
    (
        "reference-without-resource-type",
        _set("parameters", [_param("env", "resource_reference")]),
        "needs resource_type for type resource_reference",
    ),
    (
        "six-allowed-values",
        _set("parameters.0.allowed_values", ["a", "b", "c", "d", "e", "f"]),
        "has 6 allowed_values, at most 5 are allowed",
    ),
    (
        "string-default-not-allowed",
        _set("parameters.0.default", "staging"),
        "default 'staging' is not one of allowed_values",
    ),
    (
        "string-value-too-long",
        _set("parameters.0.allowed_values", ["v" * 65]),
        "is longer than 64 characters",
    ),
    (
        "boolean-bad-default",
        _set("parameters", [_param("env", "boolean", default="maybe")]),
        "default must be true or false, not 'maybe'",
    ),
    (
        "integer-allowed-not-a-number",
        _set("parameters", [_param("env", "integer", allowed_values=["ten"])]),
        "allowed value 'ten' is not a whole number",
    ),
    (
        "integer-default-not-a-number",
        _set("parameters", [_param("env", "integer", default="ten")]),
        "default 'ten' is not a whole number",
    ),
    (
        "integer-default-not-allowed",
        _set(
            "parameters",
            [_param("env", "integer", default="3", allowed_values=["1", "2"])],
        ),
        "default 3 is not one of allowed_values",
    ),
    (
        "integer-minimum-over-maximum",
        _set("parameters", [_param("env", "integer", minimum=10, maximum=5)]),
        "minimum (10) is greater than maximum (5)",
    ),
    (
        "integer-default-below-minimum",
        _set("parameters", [_param("env", "integer", default="1", minimum=5)]),
        "default 1 is below minimum 5",
    ),
    (
        "integer-default-above-maximum",
        _set("parameters", [_param("env", "integer", default="9", maximum=5)]),
        "default 9 is above maximum 5",
    ),
    (
        "long-display-name",
        _set("parameters.0.display_name", "d" * 65),
        "display_name is longer than 64 characters",
    ),
    (
        "long-parameter-description",
        _set("parameters.0.description", "d" * 1025),
        "parameter 'env' description is longer than 1024 characters",
    ),
    (
        "undefined-parameter-used",
        _set("volumes.0.provisioned_size", "{{ parameters.zzz }}"),
        "parameter 'zzz' is used but not defined in parameters",
    ),
    (
        "unused-parameter",
        _set("tags.1.value", "fixed"),
        "parameter 'env' is not used",
    ),
    (
        "storage-class-from-string-parameter",
        _set("placement.storage_class", {"name": None, "parameter": "env"}),
        "uses parameter 'env', which is of type string, not resource_reference",
    ),
    (
        "storage-class-from-wrong-resource-type",
        _many(
            _set(
                "parameters",
                [_param("env", "resource_reference", resource_type="remote-arrays")],
            ),
            _set("placement.storage_class", {"name": None, "parameter": "env"}),
            _set("tags.1.value", "fixed"),
        ),
        "needs a parameter with resource_type storage-classes, but 'env' has remote-arrays",
    ),
    (
        "target-from-wrong-resource-type",
        _many(
            _set(
                "parameters",
                [_param("env", "resource_reference", resource_type="storage-classes")],
            ),
            _set("placement.targets", [{"name": None, "parameter": "env"}]),
            _set("tags.1.value", "fixed"),
        ),
        "placement target needs a parameter with resource_type remote-arrays",
    ),
    (
        "replication-target-from-undefined-parameter",
        _set("replications.0.target", {"name": None, "parameter": "gone"}),
        "parameter 'gone' is used but not defined in parameters",
    ),
    (
        "replication-target-from-wrong-resource-type",
        _many(
            _set(
                "parameters",
                [_param("env", "resource_reference", resource_type="storage-classes")],
            ),
            _set("replications.0.target", {"name": None, "parameter": "env"}),
            _set("tags.1.value", "fixed"),
        ),
        "replication 'offsite' target needs a parameter with resource_type "
        "remote-arrays, but 'env' has storage-classes",
    ),
]


class TestValidatePreset:
    def test_valid_preset_has_no_errors(self):
        assert validate_preset(_params()) == []

    def test_minimal_preset_has_no_errors(self):
        assert validate_preset(_minimal_params()) == []

    @pytest.mark.parametrize(
        "change,expected",
        [case[1:] for case in VALIDATION_CASES],
        ids=[case[0] for case in VALIDATION_CASES],
    )
    def test_each_mistake_is_reported(self, change, expected):
        params = _params()
        change(params)
        errors = validate_preset(params)
        assert any(expected in error for error in errors), errors

    def test_every_mistake_is_reported_at_once(self):
        params = _params(
            workload_type="Bogus",
            volumes=[_volume(count="0", provisioned_size="1000", snapshots=["nope"])],
            tags=[_tag(value=None)],
        )
        errors = validate_preset(params)
        for expected in (
            "workload_type 'Bogus'",
            "count must be at least 1",
            "multiple of 512",
            "snapshot configuration 'nope'",
            "tag 'app' needs a value",
            "snapshot 'hourly' is not used",
        ):
            assert any(expected in error for error in errors), (expected, errors)
        assert len(errors) >= 6

    def test_parameter_references_pass_in_numeric_fields(self):
        params = _params()
        params["parameters"] = [
            _param("size", "integer", default="1073741824", minimum=512),
            _param("copies", "integer", default="2", minimum=1, maximum=10),
            _param("iops", "integer", default="1000"),
            _param("env", "string", default="dev"),
        ]
        params["volumes"][0]["provisioned_size"] = "{{ parameters.size }}"
        params["volumes"][0]["count"] = "{{ parameters.copies }}"
        params["qos"][0]["iops_limit"] = "{{ parameters.iops }}"
        assert validate_preset(params) == []

    def test_reference_parameter_passes_for_storage_class_and_target(self):
        params = _params()
        params["parameters"] = [
            _param("tier", "resource_reference", resource_type="storage-classes"),
            _param("peer", "resource_reference", resource_type="remote-arrays"),
            _param("env", "string", default="dev"),
        ]
        params["placement"]["storage_class"] = {"name": None, "parameter": "tier"}
        params["placement"]["targets"] = [{"name": None, "parameter": "peer"}]
        assert validate_preset(params) == []

    def test_placement_default_name_is_used_when_unnamed(self):
        params = _minimal_params()
        params["placement"]["name"] = None
        params["volumes"][0]["name"] = "default-placement"
        errors = validate_preset(params)
        assert any("used by a placement and a volume" in e for e in errors)

    def test_five_volumes_are_accepted(self):
        params = _minimal_params(volumes=[_volume("v%d" % i) for i in range(5)])
        assert validate_preset(params) == []

    def test_a_volume_without_a_count_counts_as_one(self):
        # The argument spec defaults count to 1; an explicit null gets there too
        assert validate_preset(_minimal_params(volumes=[_volume(count=None)])) == []
        params = _minimal_params(
            volumes=[_volume("a", count=None), _volume("b", count="500")]
        )
        errors = validate_preset(params)
        assert any("add up to 501, at most 500" in e for e in errors), errors

    def test_bandwidth_bounds_are_inclusive(self):
        for limit in ("1048576", "549755813888"):
            params = _params(qos=[_qos(bandwidth_limit=limit)])
            assert validate_preset(params) == [], limit

    @pytest.mark.parametrize("subtype", preset_module.SUBTYPES)
    def test_an_integer_parameter_may_have_any_accepted_subtype(self, subtype):
        # The five values Purity//FA 6.10.6 accepted when each was tried
        params = _params()
        params["parameters"] = [_param("size", "integer", subtype=subtype)]
        params["volumes"][0]["provisioned_size"] = "{{ parameters.size }}"
        params["tags"] = None
        assert validate_preset(params) == []

    @pytest.mark.parametrize("ptype", ["string", "boolean", "resource_reference"])
    @pytest.mark.parametrize("subtype", preset_module.SUBTYPES)
    def test_a_subtype_on_any_other_type_is_refused(self, ptype, subtype):
        # The array answers 400 "Invalid combination of parameters specified."
        params = _params()
        extra = (
            {"resource_type": "storage-classes"}
            if ptype == "resource_reference"
            else {}
        )
        params["parameters"] = [_param("env", ptype, subtype=subtype, **extra)]
        if ptype == "resource_reference":
            params["placement"]["storage_class"] = {"name": None, "parameter": "env"}
            params["tags"] = None
        errors = validate_preset(params)
        assert "parameter 'env' option subtype is not valid for type %s" % ptype in (
            errors
        )

    def test_two_snapshot_and_two_replication_configurations_are_accepted(self):
        params = _params(
            snapshots=[_snapshot("s1"), _snapshot("s2")],
            replications=[_replication("r1"), _replication("r2")],
            volumes=[
                _volume(
                    count="2",
                    provisioned_size="107374182400",
                    snapshots=["s1", "s2"],
                    replications=["r1", "r2"],
                )
            ],
        )
        assert validate_preset(params) == []


# ---------------------------------------------------------------------------
# build_body
# ---------------------------------------------------------------------------


class TestBuildBody:
    def test_never_carries_the_fields_the_array_owns(self):
        body = build_body(_params())
        # A name in a PUT body renames the preset
        for forbidden in ("name", "id", "context", "revision", "platform_features"):
            assert forbidden not in body

    def test_full_body(self):
        body = build_body(_params())
        assert body["workload_type"] == "PostgreSQL"
        assert body["description"] == "A test preset"
        assert body["placement_configurations"] == [
            {
                "name": "pl",
                "storage_class": {
                    "name": "flasharray-x",
                    "resource_type": "storage-classes",
                },
                "qos_configurations": ["q1"],
                "targets": [{"name": "arrayB", "resource_type": "remote-arrays"}],
            }
        ]
        assert body["volume_configurations"] == [
            {
                "name": "data",
                "count": "2",
                "provisioned_size": "107374182400",
                "placement_configurations": ["pl"],
                "snapshot_configurations": ["hourly"],
                "periodic_replication_configurations": ["offsite"],
            }
        ]
        assert body["qos_configurations"] == [
            {"name": "q1", "iops_limit": "50000", "bandwidth_limit": "1073741824"}
        ]
        assert body["snapshot_configurations"] == [
            {
                "name": "hourly",
                "policy_action": "create_or_reuse",
                "rules": [{"every": "3600000", "keep_for": "86400000"}],
            }
        ]
        assert body["periodic_replication_configurations"] == [
            {
                "name": "offsite",
                "remote_targets": [
                    {"name": "arrayB", "resource_type": "remote-arrays"}
                ],
                "rules": [
                    {"every": "86400000", "keep_for": "604800000", "at": "7200000"}
                ],
            }
        ]
        assert body["workload_tags"] == [
            {
                "key": "app",
                "value": "postgres",
                "namespace": "default",
                "copyable": "true",
            },
            {
                "key": "environment",
                "value": "{{ parameters.env }}",
                "namespace": "default",
                "copyable": "false",
            },
        ]

    def test_minimal_body_sends_only_what_was_described(self):
        body = build_body(_minimal_params())
        assert sorted(body) == [
            "placement_configurations",
            "volume_configurations",
            "workload_type",
        ]
        assert body["placement_configurations"][0] == {
            "name": "default-placement",
            "storage_class": {
                "name": "flasharray-x",
                "resource_type": "storage-classes",
            },
        }
        assert body["volume_configurations"][0]["count"] == "1"

    def test_unnamed_placement_gets_the_default_name_and_volumes_use_it(self):
        params = _minimal_params()
        params["placement"]["name"] = None
        body = build_body(params)
        assert body["placement_configurations"][0]["name"] == "default-placement"
        assert body["volume_configurations"][0]["placement_configurations"] == [
            "default-placement"
        ]

    def test_volume_may_name_the_placement_itself(self):
        params = _minimal_params()
        params["volumes"][0]["placement"] = "default-placement"
        body = build_body(params)
        assert body["volume_configurations"][0]["placement_configurations"] == [
            "default-placement"
        ]

    def test_numbers_are_sent_as_text(self):
        params = _minimal_params()
        params["volumes"][0]["count"] = 3
        params["volumes"][0]["provisioned_size"] = 1073741824
        body = build_body(params)
        assert body["volume_configurations"][0]["count"] == "3"
        assert body["volume_configurations"][0]["provisioned_size"] == "1073741824"

    def test_a_volume_without_a_count_is_sent_as_one(self):
        body = build_body(_minimal_params(volumes=[_volume(count=None)]))
        assert body["volume_configurations"][0]["count"] == "1"

    def test_parameter_templates_pass_through_unchanged(self):
        params = _params()
        params["parameters"] = [
            _param("size", "integer", default="1073741824"),
            _param("copies", "integer", default="2"),
            _param("env", "string", default="dev"),
        ]
        params["volumes"][0]["provisioned_size"] = "{{ parameters.size }}"
        params["volumes"][0]["count"] = "{{ parameters.copies }}"
        body = build_body(params)
        assert body["volume_configurations"][0]["provisioned_size"] == (
            "{{ parameters.size }}"
        )
        assert body["volume_configurations"][0]["count"] == "{{ parameters.copies }}"
        assert body["workload_tags"][1]["value"] == "{{ parameters.env }}"

    def test_parameter_reference_expands_to_the_three_fields(self):
        params = _minimal_params()
        params["placement"]["storage_class"] = {"name": None, "parameter": "tier"}
        params["placement"]["targets"] = [{"name": None, "parameter": "peer"}]
        body = build_body(params)
        placement = body["placement_configurations"][0]
        assert placement["storage_class"] == {
            "id": "{{ parameters.tier.id }}",
            "name": "{{ parameters.tier.name }}",
            "resource_type": "{{ parameters.tier.resource_type }}",
        }
        assert placement["targets"] == [
            {
                "id": "{{ parameters.peer.id }}",
                "name": "{{ parameters.peer.name }}",
                "resource_type": "{{ parameters.peer.resource_type }}",
            }
        ]

    def test_naming_templates_become_naming_patterns(self):
        params = _params()
        params["volumes"][0]["naming_template"] = "{{ workload.name }}-data-{{ i }}"
        params["qos"][0]["naming_template"] = "q"
        params["snapshots"][0]["naming_template"] = "s"
        params["replications"][0]["naming_template"] = "r"
        body = build_body(params)
        assert body["volume_configurations"][0]["naming_patterns"] == [
            {"template": "{{ workload.name }}-data-{{ i }}"}
        ]
        assert body["qos_configurations"][0]["naming_patterns"] == [{"template": "q"}]
        assert body["snapshot_configurations"][0]["naming_patterns"] == [
            {"template": "s"}
        ]
        assert body["periodic_replication_configurations"][0]["naming_patterns"] == [
            {"template": "r"}
        ]

    def test_rule_suffix_is_sent(self):
        params = _params()
        params["snapshots"][0]["rules"] = [_rule(suffix="hourly")]
        body = build_body(params)
        assert body["snapshot_configurations"][0]["rules"][0]["suffix"] == "hourly"

    def test_always_create_policy_action_is_kept(self):
        params = _params()
        params["snapshots"][0]["policy_action"] = "always_create"
        body = build_body(params)
        assert body["snapshot_configurations"][0]["policy_action"] == "always_create"

    def test_tag_namespace_and_copyable(self):
        params = _minimal_params(
            tags=[_tag("k", "v", namespace="team", copyable=False)]
        )
        body = build_body(params)
        assert body["workload_tags"] == [
            {"key": "k", "value": "v", "namespace": "team", "copyable": "false"}
        ]

    def test_tag_with_numeric_value_is_sent_as_text(self):
        body = build_body(_minimal_params(tags=[_tag("k", 5)]))
        assert body["workload_tags"][0]["value"] == "5"

    def test_string_parameter(self):
        params = _params(tags=[_tag("e", "{{ parameters.env }}")])
        parameter = build_body(params)["parameters"][0]
        assert parameter == {
            "name": "env",
            "type": "string",
            "constraints": {
                "string": {
                    "allowed_values": ["dev", "test", "prod"],
                    "default": "dev",
                }
            },
        }

    def test_integer_parameter_constraints_are_numbers(self):
        params = _params()
        params["parameters"] = [
            _param(
                "size",
                "integer",
                subtype="size",
                display_name="Size",
                description="How big",
                default="2048",
                allowed_values=["1024", "2048"],
                minimum=1024,
                maximum=4096,
            ),
        ]
        params["volumes"][0]["provisioned_size"] = "{{ parameters.size }}"
        parameter = build_body(params)["parameters"][0]
        assert parameter["constraints"] == {
            "integer": {
                "allowed_values": [1024, 2048],
                "default": 2048,
                "minimum": 1024,
                "maximum": 4096,
            }
        }
        assert parameter["metadata"] == {
            "display_name": "Size",
            "description": "How big",
            "subtype": "size",
        }

    def test_integer_parameter_without_constraints_has_none(self):
        params = _params()
        params["parameters"] = [_param("n", "integer")]
        params["volumes"][0]["count"] = "{{ parameters.n }}"
        parameter = build_body(params)["parameters"][0]
        assert "constraints" not in parameter

    def test_boolean_parameter(self):
        params = _params()
        params["parameters"] = [_param("flag", "boolean", default="yes")]
        params["tags"] = [_tag("f", "{{ parameters.flag }}")]
        assert build_body(params)["parameters"][0]["constraints"] == {
            "boolean": {"default": True}
        }

    def test_boolean_false_default_is_kept(self):
        params = _params()
        params["parameters"] = [_param("flag", "boolean", default="false")]
        params["tags"] = [_tag("f", "{{ parameters.flag }}")]
        assert build_body(params)["parameters"][0]["constraints"] == {
            "boolean": {"default": False}
        }

    def test_resource_reference_parameter(self):
        params = _params()
        params["parameters"] = [
            _param(
                "tier",
                "resource_reference",
                resource_type="storage-classes",
                default="flasharray-x",
            )
        ]
        params["placement"]["storage_class"] = {"name": None, "parameter": "tier"}
        params["tags"] = None
        assert build_body(params)["parameters"][0]["constraints"] == {
            "resource_reference": {
                "allowed_values": [{"resource_type": "storage-classes"}],
                "default": {
                    "name": "flasharray-x",
                    "resource_type": "storage-classes",
                },
            }
        }

    def test_resource_reference_parameter_without_default(self):
        params = _params()
        params["parameters"] = [
            _param("tier", "resource_reference", resource_type="storage-classes")
        ]
        params["placement"]["storage_class"] = {"name": None, "parameter": "tier"}
        params["tags"] = None
        assert build_body(params)["parameters"][0]["constraints"] == {
            "resource_reference": {
                "allowed_values": [{"resource_type": "storage-classes"}]
            }
        }

    def test_body_is_free_of_empty_values_but_keeps_false_and_zero(self):
        params = _params()
        params["snapshots"][0]["rules"] = [_rule("86400000", "86400000", "0")]
        body = build_body(params)
        assert body["snapshot_configurations"][0]["rules"][0]["at"] == "0"
        params["tags"] = [_tag("k", "v", copyable=False)]
        assert build_body(params)["workload_tags"][0]["copyable"] == "false"

    def test_does_not_change_the_task_parameters(self):
        params = _params()
        before = copy.deepcopy(params)
        build_body(params)
        assert params == before

    def test_body_is_json_serialisable(self):
        # Plain dicts, lists and scalars only; what the real SDK models make of
        # the body is checked in test_purefa_preset_sdk.py
        body = build_body(_params())
        assert json.loads(json.dumps(body)) == body


# ---------------------------------------------------------------------------
# normalise_preset
# ---------------------------------------------------------------------------


class TestNormalise:
    def test_drops_fields_the_array_owns(self):
        preset = _server_form(build_body(_params()))
        normalised = normalise_preset(preset)
        for dropped in (
            "id",
            "name",
            "context",
            "revision",
            "platform_features",
            "directory_configurations",
            "export_configurations",
            "quota_configurations",
        ):
            assert dropped not in normalised

    def test_null_and_empty_are_alike(self):
        with_null = {"workload_type": "Custom", "workload_tags": None, "parameters": []}
        with_empty = {
            "workload_type": "Custom",
            "workload_tags": [],
            "parameters": None,
        }
        bare = {"workload_type": "Custom"}
        assert normalise_preset(with_null) == normalise_preset(with_empty)
        assert normalise_preset(with_null) == normalise_preset(bare) == bare

    def test_empty_dicts_are_alike_with_missing_ones(self):
        # The SDK's to_dict() leaves out null fields, so a parameter written
        # without constraints reads back with constraints {} or {"integer": {}}
        with_empty = {
            "workload_tags": {},
            "parameters": [
                {"name": "n", "type": "integer", "constraints": {}, "metadata": {}}
            ],
        }
        with_empty_block = {
            "parameters": [
                {"name": "n", "type": "integer", "constraints": {"integer": {}}}
            ]
        }
        bare = {"parameters": [{"name": "n", "type": "integer"}]}
        assert normalise_preset(with_empty) == normalise_preset(bare) == bare
        assert normalise_preset(with_empty_block) == bare

    def test_shapes_the_module_never_writes_are_tolerated(self):
        # A placement without a storage class, a replication without targets and
        # a resource reference without a resource type cannot be written through
        # the module, but a read-back shaped that way must not raise
        preset = {
            "placement_configurations": [{"name": "p", "qos_configurations": []}],
            "periodic_replication_configurations": [{"name": "r", "rules": []}],
            "parameters": [
                {
                    "name": "t",
                    "type": "resource_reference",
                    "constraints": {
                        "resource_reference": {"allowed_values": [{}], "default": {}}
                    },
                }
            ],
        }
        assert normalise_preset(preset) == {
            "placement_configurations": [{"name": "p"}],
            "periodic_replication_configurations": [{"name": "r"}],
            "parameters": [{"name": "t", "type": "resource_reference"}],
        }

    def test_empty_text_is_missing(self):
        preset = {
            "workload_type": "Custom",
            "description": "",
            "snapshot_configurations": [
                {
                    "name": "s",
                    "policy_action": "create_or_reuse",
                    "rules": [
                        {"every": "1", "keep_for": "1", "suffix": "", "time_zone": ""}
                    ],
                }
            ],
        }
        normalised = normalise_preset(preset)
        assert "description" not in normalised
        assert normalised["snapshot_configurations"][0]["rules"] == [
            {"every": "1", "keep_for": "1"}
        ]

    def test_numbers_become_text_where_the_array_types_them_as_text(self):
        preset = {
            "volume_configurations": [
                {"name": "v", "count": 2, "provisioned_size": 1073741824}
            ],
            "qos_configurations": [
                {"name": "q", "iops_limit": 1000, "bandwidth_limit": 5000}
            ],
            "snapshot_configurations": [
                {
                    "name": "s",
                    "policy_action": "always_create",
                    "rules": [{"every": 1, "keep_for": 2, "at": 0}],
                }
            ],
        }
        normalised = normalise_preset(preset)
        assert normalised["volume_configurations"][0]["count"] == "2"
        assert normalised["volume_configurations"][0]["provisioned_size"] == (
            "1073741824"
        )
        assert normalised["qos_configurations"][0]["iops_limit"] == "1000"
        assert normalised["qos_configurations"][0]["bandwidth_limit"] == "5000"
        assert normalised["snapshot_configurations"][0]["rules"] == [
            {"every": "1", "keep_for": "2", "at": "0"}
        ]

    def test_integer_parameter_constraints_stay_numbers(self):
        preset = {
            "parameters": [
                {
                    "name": "n",
                    "type": "integer",
                    "constraints": {
                        "integer": {
                            "default": 2,
                            "minimum": 1,
                            "maximum": 9,
                            "allowed_values": [1, 2],
                        },
                        "string": None,
                        "boolean": None,
                    },
                }
            ]
        }
        constraints = normalise_preset(preset)["parameters"][0]["constraints"]
        assert constraints == {
            "integer": {
                "default": 2,
                "minimum": 1,
                "maximum": 9,
                "allowed_values": [1, 2],
            }
        }

    def test_parameter_with_all_null_constraints_matches_one_without(self):
        read_back = {
            "parameters": [
                {
                    "name": "n",
                    "type": "integer",
                    "constraints": {
                        "integer": {
                            "default": None,
                            "minimum": None,
                            "maximum": None,
                            "allowed_values": None,
                        }
                    },
                    "metadata": {"display_name": None},
                }
            ]
        }
        written = {"parameters": [{"name": "n", "type": "integer"}]}
        assert normalise_preset(read_back) == normalise_preset(written)

    def test_tag_defaults_are_filled_in(self):
        normalised = normalise_preset({"workload_tags": [{"key": "k", "value": "v"}]})
        assert normalised["workload_tags"] == [
            {"key": "k", "value": "v", "copyable": "true", "namespace": "default"}
        ]

    def test_tag_copyable_false_is_kept(self):
        normalised = normalise_preset(
            {"workload_tags": [{"key": "k", "value": "v", "copyable": "false"}]}
        )
        assert normalised["workload_tags"][0]["copyable"] == "false"

    def test_snapshot_policy_action_default_is_filled_in(self):
        normalised = normalise_preset(
            {"snapshot_configurations": [{"name": "s", "rules": []}]}
        )
        assert normalised["snapshot_configurations"][0]["policy_action"] == (
            "create_or_reuse"
        )

    def test_parameter_reference_collapses_to_the_parameter(self):
        params = _minimal_params()
        params["placement"]["storage_class"] = {"name": None, "parameter": "tier"}
        params["placement"]["targets"] = [{"name": None, "parameter": "peer"}]
        placement = normalise_preset(build_body(params))["placement_configurations"][0]
        assert placement["storage_class"] == {"parameter": "tier"}
        assert placement["targets"] == [{"parameter": "peer"}]

    def test_named_reference_keeps_only_the_name(self):
        preset = {
            "placement_configurations": [
                {
                    "name": "p",
                    "storage_class": {
                        "id": "x",
                        "name": "flasharray-x",
                        "resource_type": "storage-classes",
                    },
                    "targets": [{"name": "arrayB", "resource_type": "remote-arrays"}],
                }
            ],
            "periodic_replication_configurations": [
                {"name": "r", "remote_targets": [{"id": "y", "name": "arrayB"}]}
            ],
        }
        normalised = normalise_preset(preset)
        placement = normalised["placement_configurations"][0]
        assert placement["storage_class"] == {"name": "flasharray-x"}
        assert placement["targets"] == [{"name": "arrayB"}]
        assert normalised["periodic_replication_configurations"][0][
            "remote_targets"
        ] == [{"name": "arrayB"}]

    def test_replication_target_parameter_collapses(self):
        params = _params()
        params["parameters"] = [
            _param("peer", "resource_reference", resource_type="remote-arrays"),
            _param("env", "string"),
        ]
        params["replications"][0]["target"] = {"name": None, "parameter": "peer"}
        params["placement"]["targets"] = None
        normalised = normalise_preset(build_body(params))
        assert normalised["periodic_replication_configurations"][0][
            "remote_targets"
        ] == [{"parameter": "peer"}]

    def test_resource_reference_constraint_keeps_allowed_values_and_default_name(
        self,
    ):
        preset = {
            "parameters": [
                {
                    "name": "tier",
                    "type": "resource_reference",
                    "constraints": {
                        "resource_reference": {
                            "allowed_values": [
                                {"resource_type": "storage-classes", "id": ""}
                            ],
                            "default": {
                                "name": "flasharray-x",
                                "id": "abc",
                                "resource_type": "storage-classes",
                            },
                        }
                    },
                }
            ]
        }
        constraints = normalise_preset(preset)["parameters"][0]["constraints"]
        assert constraints == {
            "resource_reference": {
                "allowed_values": [{"resource_type": "storage-classes"}],
                "default": "flasharray-x",
            }
        }
        # What the module writes reads back as the same thing
        params = _params()
        params["parameters"] = [
            _param(
                "tier",
                "resource_reference",
                resource_type="storage-classes",
                default="flasharray-x",
            )
        ]
        params["placement"]["storage_class"] = {"name": None, "parameter": "tier"}
        params["tags"] = None
        written = normalise_preset(build_body(params))["parameters"][0]
        assert written["constraints"] == constraints

    def test_a_restricted_resource_reference_is_not_the_unrestricted_one(self):
        # Purity//FA 6.10.6 refuses a named allowed value ("Must not be set."),
        # so the module only ever writes the single resource_type entry. A fleet
        # that holds named entries, from a newer array or another tool, has a
        # different parameter, and the comparison has to say so. Order and ids
        # are not part of the difference
        def constraint(*allowed):
            return {
                "parameters": [
                    {
                        "name": "tier",
                        "type": "resource_reference",
                        "constraints": {
                            "resource_reference": {"allowed_values": list(allowed)}
                        },
                    }
                ]
            }

        unrestricted = normalise_preset(
            constraint({"resource_type": "storage-classes"})
        )
        restricted = normalise_preset(
            constraint(
                {"resource_type": "storage-classes", "name": "flasharray-x", "id": "1"},
                {"resource_type": "storage-classes", "name": "flasharray-c", "id": "2"},
            )
        )
        assert restricted != unrestricted
        assert restricted["parameters"][0]["constraints"] == {
            "resource_reference": {
                "allowed_values": [
                    {"resource_type": "storage-classes", "name": "flasharray-c"},
                    {"resource_type": "storage-classes", "name": "flasharray-x"},
                ]
            }
        }
        reordered = normalise_preset(
            constraint(
                {"resource_type": "storage-classes", "name": "flasharray-c"},
                {"resource_type": "storage-classes", "name": "flasharray-x", "id": "9"},
            )
        )
        assert reordered == restricted

    def test_lists_without_order_are_sorted(self):
        preset = {
            "volume_configurations": [
                {
                    "name": "b",
                    "snapshot_configurations": ["y", "x"],
                    "periodic_replication_configurations": ["q", "p"],
                    "placement_configurations": ["m", "l"],
                },
                {"name": "a"},
            ],
            "workload_tags": [
                {"key": "z", "value": "1"},
                {"key": "a", "value": "1", "namespace": "other"},
                {"key": "a", "value": "1"},
            ],
            "parameters": [{"name": "two"}, {"name": "one"}],
        }
        normalised = normalise_preset(preset)
        volumes = normalised["volume_configurations"]
        assert [v["name"] for v in volumes] == ["a", "b"]
        assert volumes[1]["snapshot_configurations"] == ["x", "y"]
        assert volumes[1]["periodic_replication_configurations"] == ["p", "q"]
        assert volumes[1]["placement_configurations"] == ["l", "m"]
        assert [(t["namespace"], t["key"]) for t in normalised["workload_tags"]] == [
            ("default", "a"),
            ("default", "z"),
            ("other", "a"),
        ]
        assert [p["name"] for p in normalised["parameters"]] == ["one", "two"]

    def test_rule_order_is_kept(self):
        rules = [{"every": "2", "keep_for": "2"}, {"every": "1", "keep_for": "1"}]
        normalised = normalise_preset(
            {"snapshot_configurations": [{"name": "s", "rules": rules}]}
        )
        assert normalised["snapshot_configurations"][0]["rules"] == rules

    def test_does_not_change_its_input(self):
        preset = _server_form(build_body(_params()))
        before = copy.deepcopy(preset)
        normalise_preset(preset)
        assert preset == before

    def test_false_and_zero_are_values(self):
        preset = {
            "workload_tags": [{"key": "k", "value": "v", "copyable": False}],
            "parameters": [
                {
                    "name": "n",
                    "type": "boolean",
                    "constraints": {"boolean": {"default": False}},
                }
            ],
        }
        normalised = normalise_preset(preset)
        # A boolean read back is written as the text the API uses
        assert normalised["workload_tags"][0]["copyable"] == "false"
        assert normalised["parameters"][0]["constraints"] == {
            "boolean": {"default": False}
        }

    def test_read_back_of_a_written_preset_equals_the_written_one(self):
        for params in (_params(), _minimal_params()):
            body = build_body(params)
            stored = _server_form(body)
            desired = normalise_preset(carry_over_naming(body, stored))
            assert normalise_preset(stored) == desired

    def test_numbers_read_back_as_integers_are_not_a_change(self):
        body = build_body(_params())
        read_back = _server_form(body)
        for config in read_back["volume_configurations"]:
            config["count"] = int(config["count"])
            config["provisioned_size"] = int(config["provisioned_size"])
        for config in read_back["qos_configurations"]:
            config["iops_limit"] = int(config["iops_limit"])
        for config in read_back["snapshot_configurations"]:
            for rule in config["rules"]:
                rule["every"] = int(rule["every"])
        desired = normalise_preset(carry_over_naming(body, read_back))
        assert normalise_preset(read_back) == desired


CUSTOM_TEMPLATE = (
    "{{workload.name}}-mine-{{functions.pad_left(workload.configuration.index, 3)}}"
)


class TestCarryOverNaming:
    """A naming template the task leaves out is the one the fleet has

    A PUT without naming_patterns resets the template to the array's default
    (seen on Purity//FA 6.10.6: omitted, [] and null all reset it), so the body
    borrows the stored template, and the comparison then sees it on both sides.
    """

    def test_omitted_template_is_taken_from_the_stored_configuration(self):
        body = {"volume_configurations": [{"name": "v", "count": "1"}]}
        stored = {
            "volume_configurations": [
                {"name": "v", "naming_patterns": [{"template": CUSTOM_TEMPLATE}]}
            ]
        }
        carried = carry_over_naming(body, stored)
        assert carried["volume_configurations"][0]["naming_patterns"] == [
            {"template": CUSTOM_TEMPLATE}
        ]
        # Only the template is borrowed, nothing else the array may add
        stored["volume_configurations"][0]["naming_patterns"][0]["id"] = "x"
        carried = carry_over_naming(body, stored)
        assert carried["volume_configurations"][0]["naming_patterns"] == [
            {"template": CUSTOM_TEMPLATE}
        ]

    def test_an_explicit_template_is_not_replaced(self):
        body = {
            "volume_configurations": [
                {"name": "v", "naming_patterns": [{"template": "mine"}]}
            ]
        }
        stored = {
            "volume_configurations": [
                {"name": "v", "naming_patterns": [{"template": "theirs"}]}
            ]
        }
        assert carry_over_naming(body, stored) == body

    def test_a_configuration_the_fleet_does_not_have_gets_nothing(self):
        body = {"volume_configurations": [{"name": "new"}]}
        stored = {
            "volume_configurations": [
                {"name": "old", "naming_patterns": [{"template": "t"}]}
            ]
        }
        assert carry_over_naming(body, stored) == body
        assert carry_over_naming(body, None) == body
        assert carry_over_naming(body, {}) == body

    def test_the_kind_has_to_match_as_well_as_the_name(self):
        # A stored qos named x lends nothing to a volume named x
        body = {"volume_configurations": [{"name": "x"}]}
        stored = {
            "qos_configurations": [
                {"name": "x", "naming_patterns": [{"template": "t"}]}
            ]
        }
        assert carry_over_naming(body, stored) == body

    def test_empty_or_odd_stored_patterns_lend_nothing(self):
        body = {"qos_configurations": [{"name": "q"}]}
        for patterns in (None, [], [{}], [{"template": ""}], ["text"]):
            stored = {
                "qos_configurations": [{"name": "q", "naming_patterns": patterns}]
            }
            assert carry_over_naming(body, stored) == body, patterns

    def test_covers_every_configuration_kind(self):
        body = {section: [{"name": "x"}] for section in CONFIG_SECTIONS}
        stored = {
            section: [{"name": "x", "naming_patterns": [{"template": section}]}]
            for section in CONFIG_SECTIONS
        }
        carried = carry_over_naming(body, stored)
        for section in CONFIG_SECTIONS:
            assert carried[section][0]["naming_patterns"] == [{"template": section}]

    def test_does_not_change_its_inputs(self):
        body = {"volume_configurations": [{"name": "v"}]}
        stored = {
            "volume_configurations": [
                {"name": "v", "naming_patterns": [{"template": "t"}]}
            ]
        }
        body_before, stored_before = copy.deepcopy(body), copy.deepcopy(stored)
        carry_over_naming(body, stored)
        assert body == body_before and stored == stored_before

    def test_omitted_with_a_stored_custom_template_is_no_change(self):
        # Run 1 set a template, run 2 leaves it out: nothing to do
        with_template = _params()
        with_template["volumes"][0]["naming_template"] = CUSTOM_TEMPLATE
        array = _FakeFleet({"app": _stored(with_template)})
        run = _run_main(_params(), array)
        assert run.kind == "exit"
        assert run.result["changed"] is False
        assert array.writes() == []

    def test_omitted_with_the_stored_default_is_no_change(self):
        # _server_form fills the fake array's default template everywhere
        # but the placement, which has none on the array either
        params = _params()
        stored = _stored(params)
        assert all(
            config["naming_patterns"]
            for section in CONFIG_SECTIONS
            if section != "placement_configurations"
            for config in stored.get(section) or []
        )
        assert "naming_patterns" not in stored["placement_configurations"][0]
        run = _run_main(params, _FakeFleet({"app": stored}))
        assert run.result["changed"] is False

    def test_a_change_elsewhere_carries_the_stored_template_into_the_put(self):
        # The point of the carry-over: a PUT for another reason no longer
        # resets the template
        with_template = _params()
        with_template["volumes"][0]["naming_template"] = CUSTOM_TEMPLATE
        with_template["qos"][0]["naming_template"] = "{{workload.name}}-q"
        array = _FakeFleet({"app": _stored(with_template)})
        run = _run_main(_params(description="Changed"), array)
        assert run.result["changed"] is True
        assert run.result["preset"]["changed_sections"] == ["description"]
        assert array.kinds() == ["get", "put", "get"]
        body = run.models["PresetWorkload"].call_args.kwargs
        assert body["volume_configurations"][0]["naming_patterns"] == [
            {"template": CUSTOM_TEMPLATE}
        ]
        assert body["qos_configurations"][0]["naming_patterns"] == [
            {"template": "{{workload.name}}-q"}
        ]
        # The snapshot and replication configurations lend the fake default
        for section in (
            "snapshot_configurations",
            "periodic_replication_configurations",
        ):
            assert body[section][0]["naming_patterns"] == [
                {"template": "{{ workload.name }}-%s" % body[section][0]["name"]}
            ]
        assert array.store["app"]["volume_configurations"][0]["naming_patterns"] == [
            {"template": CUSTOM_TEMPLATE}
        ]
        again = _run_main(_params(description="Changed"), array)
        assert again.result["changed"] is False

    def test_an_explicit_different_template_is_a_change(self):
        with_template = _params()
        with_template["volumes"][0]["naming_template"] = CUSTOM_TEMPLATE
        array = _FakeFleet({"app": _stored(with_template)})
        changed = _params()
        changed["volumes"][0]["naming_template"] = "{{workload.name}}-other"
        run = _run_main(changed, array)
        assert run.result["changed"] is True
        assert run.result["preset"]["changed_sections"] == ["volume_configurations"]
        body = run.models["PresetWorkload"].call_args.kwargs
        assert body["volume_configurations"][0]["naming_patterns"] == [
            {"template": "{{workload.name}}-other"}
        ]
        again = _run_main(changed, array)
        assert again.result["changed"] is False

    def test_setting_the_default_pattern_explicitly_is_the_way_back(self):
        with_template = _params()
        with_template["volumes"][0]["naming_template"] = CUSTOM_TEMPLATE
        array = _FakeFleet({"app": _stored(with_template)})
        default = _params()
        default["volumes"][0]["naming_template"] = "{{ workload.name }}-data"
        run = _run_main(default, array)
        assert run.result["changed"] is True
        assert run.result["preset"]["changed_sections"] == ["volume_configurations"]
        # Leaving it out afterwards keeps the default, and is no change
        again = _run_main(_params(), array)
        assert again.result["changed"] is False

    def test_a_new_configuration_is_sent_without_a_template(self):
        array = _FakeFleet({"app": _stored(_params())})
        params = _params(
            volumes=[
                _volume(
                    count="2",
                    provisioned_size="107374182400",
                    snapshots=["hourly"],
                    replications=["offsite"],
                ),
                _volume("logs"),
            ]
        )
        run = _run_main(params, array)
        assert run.result["changed"] is True
        volumes = run.models["PresetWorkload"].call_args.kwargs["volume_configurations"]
        assert "naming_patterns" in volumes[0]
        assert "naming_patterns" not in volumes[1]
        again = _run_main(params, array)
        assert again.result["changed"] is False

    def test_a_create_sends_no_template_the_task_did_not_give(self):
        array = _FakeFleet()
        run = _run_main(_params(), array)
        body = run.models["PresetWorkloadPost"].call_args.kwargs
        for section in CONFIG_SECTIONS:
            for config in body.get(section) or []:
                assert "naming_patterns" not in config, section

    def test_a_preset_renamed_by_an_earlier_run_lends_its_templates(self):
        with_template = _params()
        with_template["volumes"][0]["naming_template"] = CUSTOM_TEMPLATE
        array = _FakeFleet({"renamed": _stored(with_template, name="renamed")})
        run = _run_main(_params(new_name="renamed", description="Changed"), array)
        assert run.result["changed"] is True
        body = run.models["PresetWorkload"].call_args.kwargs
        assert body["volume_configurations"][0]["naming_patterns"] == [
            {"template": CUSTOM_TEMPLATE}
        ]

    def test_the_diff_shows_the_carried_template_on_both_sides(self):
        with_template = _params()
        with_template["volumes"][0]["naming_template"] = CUSTOM_TEMPLATE
        array = _FakeFleet({"app": _stored(with_template)})
        run = _run_main(_params(description="Changed"), array, diff=True)
        before = json.loads(run.result["diff"]["before"])
        after = json.loads(run.result["diff"]["after"])
        assert before["volume_configurations"][0]["naming_patterns"] == [
            {"template": CUSTOM_TEMPLATE}
        ]
        assert after["volume_configurations"][0]["naming_patterns"] == [
            {"template": CUSTOM_TEMPLATE}
        ]
        assert before["description"] == "A test preset"
        assert after["description"] == "Changed"


class TestSmallHelpers:
    def test_changed_sections(self):
        before = {"a": 1, "b": 2, "c": 3}
        after = {"a": 1, "b": 5, "d": 4}
        assert changed_sections(before, after) == ["b", "c", "d"]

    def test_changed_sections_none(self):
        assert changed_sections({"a": 1}, {"a": 1}) == []

    @pytest.mark.parametrize(
        "preset,reason",
        [
            ({}, None),
            ({"platform_features": None}, None),
            ({"platform_features": []}, None),
            ({"platform_features": ["fa_block"]}, None),
            ({"platform_features": ["fa_file"]}, "platform_features is fa_file"),
            ({"platform_features": ["fb_file"]}, "platform_features is fb_file"),
            ({"directory_configurations": [{"name": "d"}]}, "directory_configurations"),
            ({"export_configurations": [{"name": "e"}]}, "export_configurations"),
            ({"quota_configurations": [{"name": "q"}]}, "quota_configurations"),
            ({"bucket_configurations": [{"name": "b"}]}, "bucket_configurations"),
            ({"lifecycle_configurations": [{"name": "l"}]}, "lifecycle_configurations"),
            ({"directory_configurations": []}, None),
            ({"export_configurations": None}, None),
        ],
    )
    def test_not_a_block_preset(self, preset, reason):
        result = not_a_block_preset(preset)
        if reason is None:
            assert result is None
        else:
            assert reason in result

    def test_error_text_lists_distinct_messages_in_order(self):
        response = _error_response(400, "first", "second", "first", "third")
        assert _error_text(response) == "first; second; third"

    def test_error_text_without_errors(self):
        assert _error_text(Mock(status_code=400, errors=None)) == "Unknown error"
        assert _error_text(Mock(status_code=400, errors=[])) == "Unknown error"

    def test_error_text_skips_errors_without_a_message(self):
        response = Mock(errors=[_ApiObject(message=None), _ApiObject(message="x")])
        assert _error_text(response) == "x"

    @pytest.mark.parametrize(
        "status,message,absent",
        [
            (400, "Preset does not exist.", True),
            (400, "PRESET DOES NOT EXIST", True),
            (404, "Preset does not exist.", True),
            (400, "Configuration for specified name does not exist.", True),
            (400, "Must be a known platform_features type", False),
            (500, "Preset does not exist.", False),
            (403, "Operation not permitted", False),
            (400, "", False),
        ],
    )
    def test_absent_is_told_by_the_message(self, status, message, absent):
        messages = [message] if message else []
        assert _is_absent(_error_response(status, *messages)) is absent


# ---------------------------------------------------------------------------
# decide
# ---------------------------------------------------------------------------


class TestDecide:
    @pytest.mark.parametrize(
        "args,expected",
        [
            # absent
            (
                ("absent", "a", None, True, False, False),
                Decision("", False, None, True, "a"),
            ),
            (
                ("absent", "a", None, False, False, False),
                Decision("", False, None, False, "a"),
            ),
            (
                ("absent", "a", None, True, False, True),
                Decision("", False, None, True, "a"),
            ),
            # create, replace, nothing to do
            (
                ("present", "a", None, False, False, False),
                Decision("", False, "create", False, "a"),
            ),
            (
                ("present", "a", None, True, False, True),
                Decision("", False, "replace", False, "a"),
            ),
            (
                ("present", "a", None, True, False, False),
                Decision("", False, None, False, "a"),
            ),
            # new_name the same as name is no rename
            (
                ("present", "a", "a", False, False, False),
                Decision("", False, "create", False, "a"),
            ),
            (
                ("present", "a", "a", True, False, True),
                Decision("", False, "replace", False, "a"),
            ),
            (
                ("present", "a", "a", True, False, False),
                Decision("", False, None, False, "a"),
            ),
            # rename
            (
                ("present", "a", "b", True, False, False),
                Decision("", True, None, False, "b"),
            ),
            (
                ("present", "a", "b", True, False, True),
                Decision("", True, "replace", False, "b"),
            ),
            # renamed by an earlier run
            (
                ("present", "a", "b", False, True, False),
                Decision("", False, None, False, "b"),
            ),
            (
                ("present", "a", "b", False, True, True),
                Decision("", False, "replace", False, "b"),
            ),
        ],
    )
    def test_table(self, args, expected):
        assert decide(*args) == expected

    def test_rename_when_both_exist_fails(self):
        decision = decide("present", "a", "b", True, True, True)
        assert "Cannot rename preset a to b. Both already exist." == decision.fail
        assert not decision.rename and decision.write is None and not decision.delete

    def test_rename_when_neither_exists_fails(self):
        decision = decide("present", "a", "b", False, False, False)
        assert "Cannot rename preset a to b. Neither exists." == decision.fail
        assert not decision.rename and decision.write is None and not decision.delete

    def test_no_failure_in_the_ordinary_cases(self):
        assert decide("present", "a", None, False, False, False).fail == ""
        assert decide("absent", "a", None, False, False, False).fail == ""


# ---------------------------------------------------------------------------
# main: argument spec
# ---------------------------------------------------------------------------


def _spec_of(params=None):
    run = _run_main(_minimal_params() if params is None else params)
    return run.argument_spec


class TestArgumentSpec:
    def test_check_mode_is_supported(self):
        run = _run_main(_minimal_params())
        assert run.module_kwargs["supports_check_mode"] is True

    def test_workload_type_required_when_present(self):
        run = _run_main(_minimal_params())
        assert run.module_kwargs["required_if"] == [
            ["state", "present", ["workload_type"]]
        ]

    def test_name_is_required_and_state_choices(self):
        spec = _spec_of()
        assert spec["name"]["required"] is True
        assert spec["state"]["choices"] == ["absent", "present"]
        assert spec["state"]["default"] == "present"

    def test_inputs_that_make_the_array_fail_are_closed_by_choices(self):
        spec = _spec_of()
        parameter = spec["parameters"]["options"]
        # The five values Purity//FA 6.10.6 accepted; "claude-bogus" was a 500
        assert parameter["subtype"]["choices"] == [
            "size",
            "iops",
            "bandwidth",
            "time",
            "duration",
        ]
        assert parameter["resource_type"]["choices"] == [
            "storage-classes",
            "remote-arrays",
        ]
        assert parameter["type"]["choices"] == [
            "string",
            "integer",
            "boolean",
            "resource_reference",
        ]
        assert spec["workload_type"]["choices"] == preset_module.WORKLOAD_TYPES

    def test_tag_value_is_required(self):
        tags = _spec_of()["tags"]["options"]
        assert tags["value"]["required"] is True
        assert tags["key"]["required"] is True

    def test_numeric_fields_are_text_so_templates_work(self):
        spec = _spec_of()
        for path in (
            ("volumes", "count"),
            ("volumes", "provisioned_size"),
            ("qos", "iops_limit"),
            ("qos", "bandwidth_limit"),
        ):
            assert spec[path[0]]["options"][path[1]]["type"] == "str", path
        for rules in ("snapshots", "replications"):
            options = spec[rules]["options"]["rules"]["options"]
            assert {options[k]["type"] for k in ("every", "keep_for", "at")} == {"str"}

    def test_no_file_options(self):
        spec = _spec_of()
        for absent in (
            "directories",
            "exports",
            "quotas",
            "buckets",
            "lifecycle",
            "platform_features",
        ):
            assert absent not in spec

    def test_skip_verify_deployable_defaults_off(self):
        spec = _spec_of()
        assert spec["skip_verify_deployable"] == {"type": "bool", "default": False}

    def test_documentation_matches_the_argument_spec(self):
        yaml = pytest.importorskip("yaml")
        doc = yaml.safe_load(preset_module.DOCUMENTATION)["options"]
        spec = _spec_of()

        def compare(documented, actual, path):
            assert sorted(documented) == sorted(actual), path
            for key, option in actual.items():
                where = "%s.%s" % (path, key)
                docs = documented[key]
                assert docs.get("type", "str") == option.get("type", "str"), where
                assert docs.get("elements") == option.get("elements"), where
                assert bool(docs.get("required")) == bool(option.get("required")), where
                assert docs.get("choices") == option.get("choices"), where
                assert docs.get("default") == option.get("default") or str(
                    docs.get("default")
                ) == str(option.get("default")), where
                if "options" in option:
                    compare(docs["suboptions"], option["options"], where)
                else:
                    assert "suboptions" not in docs, where

        compare(doc, spec, "options")

    def test_examples_and_return_parse(self):
        yaml = pytest.importorskip("yaml")
        examples = yaml.safe_load(preset_module.EXAMPLES.replace("!unsafe", ""))
        assert all("everpure.flasharray.purefa_preset" in task for task in examples)
        assert "preset" in yaml.safe_load(preset_module.RETURN)


# ---------------------------------------------------------------------------
# main: reading and creating
# ---------------------------------------------------------------------------


class TestCreate:
    def test_creates_when_the_preset_does_not_exist(self):
        array = _FakeFleet()
        run = _run_main(_params(), array)
        assert run.kind == "exit"
        assert run.result["changed"] is True
        assert array.kinds() == ["get", "post", "get"]

    def test_create_call_arguments(self):
        array = _FakeFleet()
        params = _params()
        run = _run_main(params, array)
        post = [c for c in array.calls if c[0] == "post"][0][1]
        assert sorted(post) == ["context_names", "names", "preset"]
        assert post["names"] == ["app"]
        assert post["context_names"] == [FLEET]
        assert post["preset"].kind == "PresetWorkloadPost"
        assert post["preset"].kwargs == build_body(params)
        run.models["PresetWorkloadPost"].assert_called_once_with(**build_body(params))
        run.models["PresetWorkload"].assert_not_called()
        run.models["PresetWorkloadPatch"].assert_not_called()

    def test_create_never_sends_platform_features_or_name(self):
        array = _FakeFleet()
        run = _run_main(_params(), array)
        kwargs = run.models["PresetWorkloadPost"].call_args.kwargs
        for forbidden in ("platform_features", "name", "id", "context", "revision"):
            assert forbidden not in kwargs

    def test_skip_verify_deployable_is_passed_only_when_asked(self):
        array = _FakeFleet()
        _run_main(_params(skip_verify_deployable=True), array)
        post = [c for c in array.calls if c[0] == "post"][0][1]
        assert post["skip_verify_deployable"] is True
        array = _FakeFleet()
        _run_main(_params(), array)
        post = [c for c in array.calls if c[0] == "post"][0][1]
        assert "skip_verify_deployable" not in post

    def test_every_read_uses_the_fleet_context_and_one_name(self):
        array = _FakeFleet()
        _run_main(_params(), array)
        reads = [c[1] for c in array.calls if c[0] == "get"]
        assert reads
        for read in reads:
            assert read == {"names": ["app"], "context_names": [FLEET]}

    def test_result_after_create(self):
        array = _FakeFleet()
        run = _run_main(_params(), array)
        assert run.result["preset"]["name"] == "app"
        # The revision is read after the write
        assert run.result["preset"]["revision"] == 1
        assert "diff" not in run.result
        assert "volume_configurations" in run.result["preset"]["changed_sections"]
        assert "workload_tags" in run.result["preset"]["changed_sections"]
        assert "name" not in run.result["preset"]["changed_sections"]

    def test_second_run_changes_nothing(self):
        array = _FakeFleet()
        _run_main(_params(), array)
        run = _run_main(_params(), array)
        assert run.kind == "exit"
        assert run.result["changed"] is False
        assert array.kinds() == ["get", "post", "get", "get"]
        assert run.result["preset"]["revision"] == 1
        assert run.result["preset"]["changed_sections"] == []

    def test_minimal_second_run_changes_nothing(self):
        array = _FakeFleet()
        _run_main(_minimal_params(), array)
        run = _run_main(_minimal_params(), array)
        assert run.result["changed"] is False

    def test_unspecified_sections_are_not_sent(self):
        array = _FakeFleet()
        run = _run_main(_minimal_params(), array)
        kwargs = run.models["PresetWorkloadPost"].call_args.kwargs
        assert sorted(kwargs) == [
            "placement_configurations",
            "volume_configurations",
            "workload_type",
        ]

    def test_fleet_prefix_on_name_is_removed(self):
        array = _FakeFleet()
        run = _run_main(_params(name="%s:app" % FLEET), array)
        assert run.result["preset"]["name"] == "app"
        post = [c for c in array.calls if c[0] == "post"][0][1]
        assert post["names"] == ["app"]
        assert list(array.store) == ["app"]

    def test_other_prefix_is_not_removed_and_is_rejected(self):
        # Whether a prefix is the fleet's name is only known once the fleet is
        # read, so this one refusal comes after get_fleets and before any
        # preset is read or written
        array = _FakeFleet()
        run = _run_main(_params(name="other:app"), array)
        assert run.kind == "fail"
        assert run.result["msg"].startswith("Invalid preset name 'other:app'.")
        assert "'%s:'" % FLEET in run.result["msg"]
        assert [c[0] for c in array.calls] == ["get_fleets"]

    def test_other_prefix_on_new_name_is_rejected(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(new_name="other:renamed"), array)
        assert run.kind == "fail"
        assert run.result["msg"].startswith("Invalid preset new_name 'other:renamed'.")
        assert [c[0] for c in array.calls] == ["get_fleets"]

    @pytest.mark.parametrize(
        "name",
        [
            "12345",
            "-app",
            "app-",
            "a" * 64,
            "has space",
            "under_score",
            "dot.name",
            ":app",
            "%s:" % FLEET,
            "%s:12345" % FLEET,
            "%s:a:b" % FLEET,
        ],
    )
    def test_invalid_names_are_refused_before_the_array_is_reached(self, name):
        array = _FakeFleet()
        run = _run_main(_params(name=name), array)
        assert run.kind == "fail"
        assert run.result["msg"].startswith("Invalid preset name '%s'." % name)
        run.get_array.assert_not_called()
        run.api_check.assert_not_called()
        assert array.calls == []

    @pytest.mark.parametrize("name", ["a", "App1", "a-b", "9a", "a" * 63, "1-1"])
    def test_valid_names_are_accepted(self, name):
        run = _run_main(_params(name=name), _FakeFleet())
        assert run.kind == "exit"
        assert run.result["preset"]["name"] == name

    def test_new_name_is_checked_too(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(new_name="999"), array)
        assert run.kind == "fail"
        assert "Invalid preset new_name '999'" in run.result["msg"]
        run.get_array.assert_not_called()
        assert array.calls == []

    def test_array_outside_a_fleet_is_refused(self):
        array = _FakeFleet(fleets=False)
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert "requires a Fusion fleet" in run.result["msg"]
        assert array.writes() == []

    def test_sdk_missing(self):
        array = _FakeFleet()
        run = _run_main(_params(), array, sdk=False)
        assert run.kind == "fail"
        assert "py-pure-client sdk 1.88.0 or later is required" in run.result["msg"]
        run.get_array.assert_not_called()

    def test_failed_create_reports_every_distinct_error(self):
        array = _FakeFleet(
            fail={"post": _error_response(400, "Bad one.", "Bad two.", "Bad one.")}
        )
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert run.result["msg"] == (
            "Creating preset app failed. Error: Bad one.; Bad two."
        )
        assert run.result["changed"] is False
        assert run.result["status_code"] == 400

    def test_a_failed_read_that_is_not_absence_fails(self):
        array = _FakeFleet(fail={"get": _error_response(400, "Something else.")})
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert run.result["msg"].startswith("Reading preset app failed.")
        assert array.writes() == []

    def test_a_server_error_on_read_is_not_taken_for_absence(self):
        array = _FakeFleet(fail={"get": _error_response(500, "Preset does not exist")})
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert array.writes() == []

    def test_validation_failure_stops_before_the_array_is_reached(self):
        run = _run_main(_params(workload_type="Bogus", tags=[_tag(value="")]))
        assert run.kind == "fail"
        assert run.result["msg"].startswith("The preset is not valid. (1) ")
        assert "(2) " in run.result["msg"]
        assert "workload_type 'Bogus'" in run.result["msg"]
        assert "tag 'app' needs a value" in run.result["msg"]
        run.get_array.assert_not_called()

    def test_a_task_with_nothing_block_valid_is_refused(self):
        run = _run_main(_params(placement=None, volumes=None, qos=None))
        assert run.kind == "fail"
        assert "a block preset needs a placement" in run.result["msg"]
        assert "at least one entry in volumes" in run.result["msg"]
        run.get_array.assert_not_called()

    @pytest.mark.parametrize("section", ["snapshots", "replications"])
    def test_a_third_configuration_is_refused_before_the_array_is_reached(
        self, section
    ):
        # The SDK models take two of each and raise for a third, so the validator
        # has to say no first
        make = _snapshot if section == "snapshots" else _replication
        params = _params()
        params[section] = [make("c1"), make("c2"), make("c3")]
        params["volumes"][0][section] = ["c1", "c2", "c3"]
        run = _run_main(params)
        assert run.kind == "fail"
        assert "%s has 3 entries, at most 2 are allowed" % section in (
            run.result["msg"]
        )
        run.get_array.assert_not_called()
        for model in run.models.values():
            model.assert_not_called()

    def test_a_body_the_sdk_model_refuses_fails_cleanly(self):
        # Whatever the model's own checks reject surfaces as fail_json, never a
        # traceback, and nothing is sent
        array = _FakeFleet()
        run = _run_main(
            _params(),
            array,
            reject={
                "PresetWorkloadPost": ValueError(
                    "snapshot_configurations: ensure this value has at most 2 items"
                )
            },
        )
        assert run.kind == "fail"
        assert run.result["msg"] == (
            "Creating preset app failed. The py-pure-client model rejected the "
            "preset: snapshot_configurations: ensure this value has at most 2 items"
        )
        assert run.result["changed"] is False
        assert array.writes() == []
        assert array.store == {}

    def test_a_failed_read_after_the_write_reports_changed(self):
        # The preset was created; only the revision read-back failed
        array = _FakeFleet(fail={"get_after_write": _error_response(500, "Busy.")})
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert run.result["msg"] == "Reading preset app failed. Error: Busy."
        assert run.result["changed"] is True
        assert array.kinds() == ["get", "post", "get"]
        assert list(array.store) == ["app"]

    def test_task_parameters_are_not_changed(self):
        params = _params()
        run = _run_main(params, _FakeFleet())
        assert run.module.params == params


# ---------------------------------------------------------------------------
# main: replace
# ---------------------------------------------------------------------------


class TestReplace:
    def test_identical_preset_is_no_change_and_no_write(self):
        params = _params()
        array = _FakeFleet({"app": _stored(params, revision=7)})
        run = _run_main(params, array)
        assert run.kind == "exit"
        assert run.result["changed"] is False
        assert array.writes() == []
        assert run.result["preset"] == {
            "name": "app",
            "revision": 7,
            "changed_sections": [],
        }

    def test_difference_replaces_with_put(self):
        old = _params()
        array = _FakeFleet({"app": _stored(old, revision=3)})
        new = _params(description="Changed")
        run = _run_main(new, array)
        assert run.result["changed"] is True
        assert array.kinds() == ["get", "put", "get"]
        put = [c for c in array.calls if c[0] == "put"][0][1]
        assert sorted(put) == ["context_names", "names", "preset"]
        assert put["names"] == ["app"]
        assert put["context_names"] == [FLEET]
        assert put["preset"].kind == "PresetWorkload"
        assert run.result["preset"]["changed_sections"] == ["description"]
        assert run.result["preset"]["revision"] == 4

    def test_put_body_is_the_task_not_a_merge_with_the_read_back(self):
        # The task, plus the naming templates the fleet holds for the
        # configurations the task names and nothing else from the read-back
        old = _params()
        stored = _stored(old, revision=3)
        array = _FakeFleet({"app": stored})
        new = _params(description="Changed")
        run = _run_main(new, array)
        kwargs = run.models["PresetWorkload"].call_args.kwargs
        assert kwargs == carry_over_naming(build_body(new), stored)
        assert kwargs["description"] == "Changed"
        for owned in ("name", "id", "context", "revision", "platform_features"):
            assert owned not in kwargs
        stripped = copy.deepcopy(kwargs)
        for section in CONFIG_SECTIONS:
            for config in stripped.get(section) or []:
                config.pop("naming_patterns", None)
        assert stripped == build_body(new)
        run.models["PresetWorkloadPost"].assert_not_called()
        run.models["PresetWorkloadPatch"].assert_not_called()

    def test_skip_verify_deployable_is_passed_on_replace_only_when_asked(self):
        stored = _stored(_params())
        array = _FakeFleet({"app": stored})
        params = _params(description="x", skip_verify_deployable=True)
        run = _run_main(params, array)
        assert run.result["changed"] is True
        put = [c for c in array.calls if c[0] == "put"][0][1]
        assert sorted(put) == [
            "context_names",
            "names",
            "preset",
            "skip_verify_deployable",
        ]
        assert put["skip_verify_deployable"] is True
        assert put["names"] == ["app"]
        assert put["context_names"] == [FLEET]
        run.models["PresetWorkload"].assert_called_once_with(
            **carry_over_naming(build_body(params), stored)
        )
        # The flag is not stored, so the second run finds nothing to do
        again = _run_main(params, array)
        assert again.result["changed"] is False
        assert array.kinds().count("put") == 1
        array = _FakeFleet({"app": _stored(_params())})
        _run_main(_params(description="x"), array)
        put = [c for c in array.calls if c[0] == "put"][0][1]
        assert "skip_verify_deployable" not in put

    def test_a_read_back_item_that_is_a_plain_dict_is_accepted(self):
        class _DictFleet(_FakeFleet):
            def get_presets_workload(self, **kwargs):
                self.calls.append(("get", kwargs))
                name = kwargs["names"][0]
                if name not in self.store:
                    return _error_response(400, "Preset does not exist.")
                return _ok([copy.deepcopy(self.store[name])])

        params = _params()
        run = _run_main(params, _DictFleet({"app": _stored(params, revision=2)}))
        assert run.kind == "exit"
        assert run.result["changed"] is False
        assert run.result["preset"]["revision"] == 2

    def test_leaving_a_section_out_removes_it(self):
        array = _FakeFleet({"app": _stored(_params(), revision=1)})
        trimmed = _params(
            snapshots=None,
            volumes=[
                _volume(
                    count="2",
                    provisioned_size="107374182400",
                    replications=["offsite"],
                )
            ],
        )
        run = _run_main(trimmed, array)
        assert run.result["changed"] is True
        assert "snapshot_configurations" in run.result["preset"]["changed_sections"]
        kwargs = run.models["PresetWorkload"].call_args.kwargs
        assert "snapshot_configurations" not in kwargs
        again = _run_main(trimmed, array)
        assert again.result["changed"] is False

    def test_each_section_change_is_noticed(self):
        base = _params()
        variants = {
            "workload_type": _params(workload_type="Custom"),
            "description": _params(description="x"),
            "placement_configurations": _params(
                placement={
                    "name": "pl",
                    "storage_class": _reference("flasharray-c"),
                    "qos": "q1",
                    "targets": [_reference("arrayB")],
                }
            ),
            "qos_configurations": _params(qos=[_qos(iops_limit="60000")]),
            "snapshot_configurations": _params(
                snapshots=[_snapshot(rules=[_rule("3600000", "172800000")])]
            ),
            "periodic_replication_configurations": _params(
                replications=[_replication(target="arrayC")]
            ),
            "volume_configurations": _params(
                volumes=[
                    _volume(
                        count="3",
                        provisioned_size="107374182400",
                        snapshots=["hourly"],
                        replications=["offsite"],
                    )
                ]
            ),
            "workload_tags": _params(
                tags=[
                    _tag("app", "mysql"),
                    _tag("environment", "{{ parameters.env }}", copyable=False),
                ]
            ),
            "parameters": _params(parameters=[_param("env", "string", default="test")]),
        }
        for section, params in variants.items():
            stored = _stored(base)
            array = _FakeFleet({"app": stored})
            run = _run_main(params, array)
            assert run.result["changed"] is True, section
            assert section in run.result["preset"]["changed_sections"], section
            assert array.kinds() == ["get", "put", "get"], section
            # The whole task is what was PUT, with the fleet's naming templates
            # carried over, and the PUT settles the matter
            assert run.models["PresetWorkload"].call_args.kwargs == (
                carry_over_naming(build_body(params), stored)
            ), section
            again = _run_main(params, array)
            assert again.result["changed"] is False, section
            assert array.kinds().count("put") == 1, section

    def test_changing_a_numeric_field_by_value_is_noticed(self):
        base = _params()
        array = _FakeFleet({"app": _stored(base)})
        run = _run_main(
            _params(
                volumes=[
                    _volume(
                        count="2",
                        provisioned_size="214748364800",
                        snapshots=["hourly"],
                        replications=["offsite"],
                    )
                ]
            ),
            array,
        )
        assert run.result["changed"] is True

    def test_reordering_is_not_a_change(self):
        params = _params(
            tags=[_tag("b", "2"), _tag("a", "1")],
            parameters=[
                _param("z", "string", default="1"),
                _param("y", "string", default="2"),
            ],
        )
        params["tags"].append(_tag("c", "{{ parameters.z }}{{ parameters.y }}"))
        array = _FakeFleet({"app": _stored(params)})
        reordered = copy.deepcopy(params)
        reordered["tags"].reverse()
        reordered["parameters"].reverse()
        run = _run_main(reordered, array)
        assert run.result["changed"] is False

    def test_failed_replace_reports_error(self):
        array = _FakeFleet(
            {"app": _stored(_params())},
            fail={"put": _error_response(400, "Unused configuration in the preset.")},
        )
        run = _run_main(_params(description="x"), array)
        assert run.kind == "fail"
        assert run.result["msg"] == (
            "Replacing preset app failed. Error: Unused configuration in the preset."
        )

    def test_refuses_to_replace_a_file_preset(self):
        stored = _stored(_params())
        stored["directory_configurations"] = [{"name": "root"}]
        array = _FakeFleet({"app": stored})
        run = _run_main(_params(description="x"), array)
        assert run.kind == "fail"
        assert "Preset app is not a block preset (it has directory_configurations)" in (
            run.result["msg"]
        )
        assert array.writes() == []

    def test_refuses_to_replace_a_preset_with_file_platform_feature(self):
        stored = _stored(_params())
        stored["platform_features"] = ["fa_file"]
        array = _FakeFleet({"app": stored})
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert "platform_features is fa_file" in run.result["msg"]
        assert array.writes() == []

    def test_refusal_applies_even_when_the_content_is_identical(self):
        stored = _stored(_params())
        stored["bucket_configurations"] = [{"name": "b"}]
        array = _FakeFleet({"app": stored})
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert array.writes() == []

    def test_new_naming_template_replaces(self):
        base = _params()
        array = _FakeFleet({"app": _stored(base)})
        changed = _params()
        changed["volumes"][0]["naming_template"] = "{{ workload.name }}-mine"
        run = _run_main(changed, array)
        assert run.result["changed"] is True
        again = _run_main(changed, array)
        assert again.result["changed"] is False

    def test_server_naming_default_is_not_a_change(self):
        # The stored preset has naming_patterns on every configuration
        params = _params()
        stored = _stored(params)
        assert all(
            c.get("naming_patterns")
            for c in stored["volume_configurations"] + stored["qos_configurations"]
        )
        run = _run_main(params, _FakeFleet({"app": stored}))
        assert run.result["changed"] is False


# ---------------------------------------------------------------------------
# main: rename
# ---------------------------------------------------------------------------


class TestRename:
    def test_rename_uses_patch_and_nothing_else_when_content_is_the_same(self):
        params = _params(new_name="renamed")
        array = _FakeFleet({"app": _stored(_params(), revision=2)})
        run = _run_main(params, array)
        assert run.kind == "exit"
        assert run.result["changed"] is True
        assert array.kinds() == ["get", "get", "patch", "get"]
        patch_call = [c for c in array.calls if c[0] == "patch"][0][1]
        assert sorted(patch_call) == ["context_names", "names", "preset"]
        assert patch_call["names"] == ["app"]
        assert patch_call["context_names"] == [FLEET]
        assert patch_call["preset"].kind == "PresetWorkloadPatch"
        assert patch_call["preset"].kwargs == {"name": "renamed"}
        run.models["PresetWorkloadPatch"].assert_called_once_with(name="renamed")
        run.models["PresetWorkload"].assert_not_called()
        run.models["PresetWorkloadPost"].assert_not_called()
        assert list(array.store) == ["renamed"]
        assert run.result["preset"]["name"] == "renamed"
        assert run.result["preset"]["changed_sections"] == ["name"]

    def test_rename_and_change_content_replaces_under_the_old_name_then_renames(
        self,
    ):
        # The PUT goes first, to the name the preset has, so that a refused PUT
        # leaves the fleet untouched. The PATCH rename is the last write
        params = _params(new_name="renamed", description="Changed")
        stored = _stored(_params(), revision=2)
        array = _FakeFleet({"app": stored})
        run = _run_main(params, array)
        assert run.kind == "exit"
        assert run.result["changed"] is True
        assert array.kinds() == ["get", "get", "put", "patch", "get"]
        put = [c for c in array.calls if c[0] == "put"][0][1]
        assert put["names"] == ["app"]
        assert put["context_names"] == [FLEET]
        expected_body = carry_over_naming(build_body(params), stored)
        assert put["preset"].kwargs == expected_body
        patch_call = [c for c in array.calls if c[0] == "patch"][0][1]
        assert patch_call["names"] == ["app"]
        assert patch_call["context_names"] == [FLEET]
        assert patch_call["preset"].kwargs == {"name": "renamed"}
        run.models["PresetWorkload"].assert_called_once_with(**expected_body)
        run.models["PresetWorkloadPatch"].assert_called_once_with(name="renamed")
        run.models["PresetWorkloadPost"].assert_not_called()
        # The revision is read back under the new name
        assert array.calls[-1][1]["names"] == ["renamed"]
        assert run.result["preset"]["name"] == "renamed"
        assert run.result["preset"]["revision"] == 3
        assert run.result["preset"]["changed_sections"] == ["name", "description"]
        assert list(array.store) == ["renamed"]
        assert array.store["renamed"]["description"] == "Changed"
        again = _run_main(params, array)
        assert again.result["changed"] is False
        assert array.writes()[-1][0] == "patch"

    def test_rename_put_body_has_no_name(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(new_name="renamed", description="Changed"), array)
        assert "name" not in run.models["PresetWorkload"].call_args.kwargs

    def test_rename_is_idempotent(self):
        array = _FakeFleet({"app": _stored(_params(), revision=2)})
        first = _run_main(_params(new_name="renamed"), array)
        assert first.result["changed"] is True
        second = _run_main(_params(new_name="renamed"), array)
        assert second.kind == "exit"
        assert second.result["changed"] is False
        assert array.kinds().count("patch") == 1
        assert second.result["preset"]["name"] == "renamed"

    def test_rename_already_done_still_applies_content_changes(self):
        array = _FakeFleet({"renamed": _stored(_params(), name="renamed")})
        run = _run_main(_params(new_name="renamed", description="Changed"), array)
        assert run.result["changed"] is True
        assert array.kinds() == ["get", "get", "put", "get"]
        put = [c for c in array.calls if c[0] == "put"][0][1]
        assert put["names"] == ["renamed"]
        assert run.result["preset"]["changed_sections"] == ["description"]

    def test_rename_fails_when_both_exist(self):
        array = _FakeFleet(
            {
                "app": _stored(_params()),
                "renamed": _stored(_params(), name="renamed"),
            }
        )
        run = _run_main(_params(new_name="renamed"), array)
        assert run.kind == "fail"
        assert run.result["msg"] == (
            "Cannot rename preset app to renamed. Both already exist."
        )
        assert array.writes() == []

    def test_rename_fails_when_neither_exists(self):
        array = _FakeFleet()
        run = _run_main(_params(new_name="renamed"), array)
        assert run.kind == "fail"
        assert run.result["msg"] == (
            "Cannot rename preset app to renamed. Neither exists."
        )
        assert array.writes() == []

    def test_new_name_equal_to_name_is_no_rename(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(new_name="app"), array)
        assert run.result["changed"] is False
        assert array.kinds() == ["get"]

    def test_new_name_with_fleet_prefix(self):
        array = _FakeFleet({"app": _stored(_params())})
        _run_main(_params(new_name="%s:renamed" % FLEET), array)
        assert list(array.store) == ["renamed"]

    def test_rename_of_a_file_preset_is_refused(self):
        stored = _stored(_params())
        stored["directory_configurations"] = [{"name": "d"}]
        array = _FakeFleet({"app": stored})
        run = _run_main(_params(new_name="renamed"), array)
        assert run.kind == "fail"
        assert array.writes() == []

    def test_failed_rename_reports_error(self):
        array = _FakeFleet(
            {"app": _stored(_params())},
            fail={"patch": _error_response(400, "Name is already in use.")},
        )
        run = _run_main(_params(new_name="renamed"), array)
        assert run.kind == "fail"
        assert run.result["msg"] == (
            "Renaming preset app to renamed failed. Error: Name is already in use."
        )
        # Nothing happened before the PATCH, so nothing changed
        assert run.result["changed"] is False
        assert list(array.store) == ["app"]

    def test_a_refused_replace_before_the_rename_changes_nothing(self):
        # The PUT is refused, so the PATCH is never sent. The preset keeps its
        # name and its content, and the task says nothing changed
        array = _FakeFleet(
            {"app": _stored(_params())},
            fail={"put": _error_response(400, "Bad.")},
        )
        run = _run_main(_params(new_name="renamed", description="x"), array)
        assert run.kind == "fail"
        assert run.result["msg"] == "Replacing preset app failed. Error: Bad."
        assert run.result["changed"] is False
        assert run.result["status_code"] == 400
        assert array.kinds() == ["get", "get", "put"]
        put = [c for c in array.calls if c[0] == "put"][0][1]
        assert put["names"] == ["app"]
        run.models["PresetWorkloadPatch"].assert_not_called()
        assert list(array.store) == ["app"]
        assert array.store["app"]["description"] == "A test preset"
        # With the refusal gone, the next run does the whole job
        again = _run_main(
            _params(new_name="renamed", description="x"), _FakeFleet(array.store)
        )
        assert again.kind == "exit"
        assert again.result["changed"] is True
        assert again.result["preset"]["changed_sections"] == ["name", "description"]

    def test_a_refused_rename_after_the_replace_is_a_change(self):
        # The PUT went through; the PATCH was then refused. The task fails, says
        # the fleet was changed, because it was, and says which step failed
        array = _FakeFleet(
            {"app": _stored(_params())},
            fail={"patch": _error_response(400, "Name is already in use.")},
        )
        run = _run_main(_params(new_name="renamed", description="x"), array)
        assert run.kind == "fail"
        assert run.result["msg"] == (
            "The content of preset app was replaced, but renaming it to renamed "
            "failed. Error: Name is already in use."
        )
        assert run.result["changed"] is True
        assert run.result["status_code"] == 400
        assert array.kinds() == ["get", "get", "put", "patch"]
        put = [c for c in array.calls if c[0] == "put"][0][1]
        assert put["names"] == ["app"]
        patch_call = [c for c in array.calls if c[0] == "patch"][0][1]
        assert patch_call["names"] == ["app"]
        assert patch_call["preset"].kwargs == {"name": "renamed"}
        assert list(array.store) == ["app"]
        assert array.store["app"]["description"] == "x"
        # The next run finds the content in place and only renames
        again = _run_main(
            _params(new_name="renamed", description="x"), _FakeFleet(array.store)
        )
        assert again.kind == "exit"
        assert again.result["changed"] is True
        assert again.array.kinds() == ["get", "get", "patch", "get"]
        assert again.result["preset"]["changed_sections"] == ["name"]

    def test_a_refused_rename_with_403_after_the_replace_keeps_the_hint(self):
        array = _FakeFleet(
            {"app": _stored(_params())},
            fail={"patch": _error_response(403, "Operation not permitted")},
        )
        run = _run_main(_params(new_name="renamed", description="x"), array)
        assert run.kind == "fail"
        assert run.result["msg"].startswith(
            "The content of preset app was replaced, but renaming it to renamed "
            "failed. Error: Operation not permitted. Writing a preset needs"
        )
        assert run.result["changed"] is True
        assert run.result["status_code"] == 403

    def test_a_body_the_model_refuses_changes_nothing_even_with_a_rename(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(
            _params(new_name="renamed", description="x"),
            array,
            reject={"PresetWorkload": ValueError("no")},
        )
        assert run.kind == "fail"
        assert run.result["msg"] == (
            "Replacing preset app failed. The py-pure-client model rejected the "
            "preset: no"
        )
        assert run.result["changed"] is False
        assert array.kinds() == ["get", "get"]
        assert list(array.store) == ["app"]

    def test_new_name_with_absent_is_refused_before_the_array_is_reached(self):
        run = _run_main(_params(state="absent", new_name="renamed"))
        assert run.kind == "fail"
        assert run.result["msg"] == "new_name can only be used with state present"
        run.get_array.assert_not_called()


# ---------------------------------------------------------------------------
# main: delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_absent_deletes(self):
        array = _FakeFleet({"app": _stored(_params(), revision=4)})
        run = _run_main(_params(state="absent"), array)
        assert run.kind == "exit"
        assert run.result["changed"] is True
        assert array.kinds() == ["get", "delete"]
        call = [c for c in array.calls if c[0] == "delete"][0][1]
        assert call == {"names": ["app"], "context_names": [FLEET]}
        assert array.store == {}
        assert run.result["preset"]["name"] == "app"
        assert run.result["preset"]["revision"] is None
        assert "volume_configurations" in run.result["preset"]["changed_sections"]
        for model in run.models.values():
            model.assert_not_called()

    def test_absent_when_it_does_not_exist_is_no_change(self):
        array = _FakeFleet()
        run = _run_main(_params(state="absent"), array)
        assert run.result["changed"] is False
        assert array.writes() == []
        assert run.result["preset"]["changed_sections"] == []

    def test_absent_is_idempotent(self):
        array = _FakeFleet({"app": _stored(_params())})
        _run_main(_params(state="absent"), array)
        run = _run_main(_params(state="absent"), array)
        assert run.result["changed"] is False
        assert array.kinds().count("delete") == 1

    def test_absent_needs_no_preset_description(self):
        params = {
            "fa_url": "x",
            "api_token": "t",
            "name": "app",
            "new_name": None,
            "state": "absent",
            "workload_type": None,
            "description": None,
            "placement": None,
            "volumes": None,
            "qos": None,
            "snapshots": None,
            "replications": None,
            "parameters": None,
            "tags": None,
            "skip_verify_deployable": False,
        }
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(params, array)
        assert run.kind == "exit"
        assert run.result["changed"] is True
        assert array.store == {}

    def test_delete_of_a_file_preset_is_refused(self):
        stored = _stored(_params())
        stored["directory_configurations"] = [{"name": "d"}]
        array = _FakeFleet({"app": stored})
        run = _run_main(_params(state="absent"), array)
        assert run.kind == "fail"
        assert "not a block preset" in run.result["msg"]
        assert "will not delete" in run.result["msg"]
        assert array.writes() == []

    def test_failed_delete_reports_error(self):
        array = _FakeFleet(
            {"app": _stored(_params())},
            fail={"delete": _error_response(400, "Cannot delete.")},
        )
        run = _run_main(_params(state="absent"), array)
        assert run.kind == "fail"
        assert run.result["msg"] == "Deleting preset app failed. Error: Cannot delete."

    def test_delete_with_fleet_prefix(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(state="absent", name="%s:app" % FLEET), array)
        assert run.result["changed"] is True
        assert array.store == {}

    def test_absent_is_not_validated_as_a_preset(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(
            _params(state="absent", workload_type="Bogus", volumes=[]), array
        )
        assert run.kind == "exit"
        assert run.result["changed"] is True


# ---------------------------------------------------------------------------
# main: check mode and diff
# ---------------------------------------------------------------------------


class TestCheckMode:
    def test_create_in_check_mode_writes_nothing(self):
        array = _FakeFleet()
        run = _run_main(_params(), array, check_mode=True)
        assert run.result["changed"] is True
        assert array.writes() == []
        assert array.kinds() == ["get"]
        assert array.store == {}
        assert run.result["preset"]["revision"] is None
        for model in run.models.values():
            model.assert_not_called()

    def test_replace_in_check_mode_writes_nothing(self):
        array = _FakeFleet({"app": _stored(_params(), revision=5)})
        run = _run_main(_params(description="x"), array, check_mode=True)
        assert run.result["changed"] is True
        assert array.writes() == []
        assert array.kinds() == ["get"]
        assert array.store["app"]["revision"] == 5
        assert run.result["preset"]["changed_sections"] == ["description"]
        assert run.result["preset"]["revision"] == 5

    def test_rename_in_check_mode_writes_nothing(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(
            _params(new_name="renamed", description="x"), array, check_mode=True
        )
        assert run.result["changed"] is True
        assert array.writes() == []
        assert list(array.store) == ["app"]
        assert run.result["preset"]["name"] == "renamed"
        assert run.result["preset"]["changed_sections"] == ["name", "description"]

    def test_delete_in_check_mode_writes_nothing(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(state="absent"), array, check_mode=True)
        assert run.result["changed"] is True
        assert array.writes() == []
        assert list(array.store) == ["app"]

    def test_no_change_in_check_mode(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(), array, check_mode=True)
        assert run.result["changed"] is False
        assert array.writes() == []

    def test_validation_still_applies_in_check_mode(self):
        run = _run_main(_params(workload_type="Bogus"), check_mode=True)
        assert run.kind == "fail"

    def test_refusals_still_apply_in_check_mode(self):
        array = _FakeFleet()
        run = _run_main(_params(new_name="renamed"), array, check_mode=True)
        assert run.kind == "fail"
        assert "Neither exists" in run.result["msg"]


class TestDiff:
    def test_no_diff_unless_asked(self):
        run = _run_main(_params(), _FakeFleet())
        assert "diff" not in run.result

    def test_create_diff_is_empty_before_and_full_after(self):
        params = _params()
        run = _run_main(params, _FakeFleet(), check_mode=True, diff=True)
        diff = run.result["diff"]
        assert json.loads(diff["before"]) == {}
        assert json.loads(diff["after"]) == normalise_preset(build_body(params))
        assert diff["before_header"] == "preset app"
        assert diff["after_header"] == "preset app"

    def test_replace_diff_shows_before_and_after(self):
        old = _params()
        array = _FakeFleet({"app": _stored(old)})
        new = _params(description="Changed")
        run = _run_main(new, array, check_mode=True, diff=True)
        diff = run.result["diff"]
        before = json.loads(diff["before"])
        after = json.loads(diff["after"])
        assert before["description"] == "A test preset"
        assert after["description"] == "Changed"
        # The fleet's naming templates, which the task never named, are carried
        # over and so shown the same on both sides
        for before_config, after_config in zip(
            before["volume_configurations"], after["volume_configurations"]
        ):
            assert before_config["naming_patterns"] == after_config["naming_patterns"]

    def test_diff_is_text_with_sorted_keys_and_trailing_newline(self):
        run = _run_main(_params(), _FakeFleet(), diff=True)
        assert run.result["diff"]["after"].endswith("}\n")
        parsed = json.loads(run.result["diff"]["after"])
        assert run.result["diff"]["after"] == (
            json.dumps(parsed, indent=2, sort_keys=True) + "\n"
        )

    def test_delete_diff_is_empty_after(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(state="absent"), array, diff=True)
        assert json.loads(run.result["diff"]["after"]) == {}
        assert json.loads(run.result["diff"]["before"])["workload_type"] == "PostgreSQL"

    def test_rename_diff_shows_the_name(self):
        # Ansible prints nothing for a diff whose texts are equal, headers or not,
        # so a rename of an otherwise identical preset carries the name
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(new_name="renamed"), array, diff=True)
        diff = run.result["diff"]
        assert diff["before_header"] == "preset app"
        assert diff["after_header"] == "preset renamed"
        assert diff["before"] != diff["after"]
        before = json.loads(diff["before"])
        after = json.loads(diff["after"])
        assert before.pop("name") == "app"
        assert after.pop("name") == "renamed"
        assert before == after

    def test_no_name_in_the_diff_without_a_rename(self):
        for params, store in (
            (_params(), {"app": _stored(_params())}),
            (_params(description="x"), {"app": _stored(_params())}),
            (_params(), {}),
            # An earlier run made the rename, so this run renames nothing
            (_params(new_name="renamed"), {"renamed": _stored(_params(), "renamed")}),
        ):
            run = _run_main(params, _FakeFleet(store), diff=True)
            assert "name" not in json.loads(run.result["diff"]["before"])
            assert "name" not in json.loads(run.result["diff"]["after"])

    def test_no_change_diff_is_identical_both_sides(self):
        array = _FakeFleet({"app": _stored(_params())})
        run = _run_main(_params(), array, diff=True)
        assert run.result["diff"]["before"] == run.result["diff"]["after"]


# ---------------------------------------------------------------------------
# main: fleet identity and REST version
# ---------------------------------------------------------------------------

HINT = "needs a fleet-wide (directory) identity"


class TestFleetIdentity:
    @pytest.mark.parametrize("kind", ["post", "put", "patch", "delete"])
    def test_403_on_a_write_adds_the_directory_identity_hint(self, kind):
        forbidden = _error_response(403, "Operation not permitted")
        stored = {"app": _stored(_params())}
        fail = {kind: forbidden}
        if kind == "post":
            array, params = _FakeFleet(fail=fail), _params()
        elif kind == "put":
            array, params = _FakeFleet(stored, fail), _params(description="x")
        elif kind == "patch":
            array, params = _FakeFleet(stored, fail), _params(new_name="renamed")
        else:
            array, params = _FakeFleet(stored, fail), _params(state="absent")
        run = _run_main(params, array)
        assert run.kind == "fail"
        assert "Operation not permitted" in run.result["msg"]
        assert "Writing a preset needs a fleet-wide (directory) identity" in (
            run.result["msg"]
        )
        assert "local array user can read presets but not change them" in (
            run.result["msg"]
        )
        assert run.result["status_code"] == 403

    def test_403_with_no_message_still_gets_the_hint(self):
        array = _FakeFleet(fail={"post": _error_response(403)})
        run = _run_main(_params(), array)
        assert "Unknown error" in run.result["msg"]
        assert "directory) identity" in run.result["msg"]

    def test_other_write_failures_get_no_hint(self):
        array = _FakeFleet(fail={"post": _error_response(400, "Bad.")})
        run = _run_main(_params(), array)
        assert "directory" not in run.result["msg"]

    def test_403_on_a_read_gets_no_write_hint(self):
        array = _FakeFleet(fail={"get": _error_response(403, "Forbidden")})
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert run.result["msg"].startswith("Reading preset app failed.")
        assert "directory" not in run.result["msg"]

    def test_fleet_name_comes_from_get_fleets_and_is_the_context(self):
        array = _FakeFleet()
        _run_main(_params(), array)
        assert array.calls[0] == ("get_fleets", {})
        for kind, kwargs in array.calls[1:]:
            assert kwargs["context_names"] == [FLEET], kind


class TestRestGating:
    def test_module_minimum_is_checked(self):
        # Every body may carry policy_action, naming_patterns and rule suffixes,
        # which the API defines from 2.51, so that is the floor
        run = _run_main(_minimal_params(), _FakeFleet())
        run.api_check.assert_called_once_with(
            run.array, "2.51", run.module, "Workload presets"
        )

    def test_skip_verify_deployable_needs_no_check_of_its_own(self):
        # It arrived with 2.51, the floor
        run = _run_main(_minimal_params(skip_verify_deployable=True), _FakeFleet())
        assert [c.args[1:] for c in run.api_check.call_args_list] == [
            ("2.51", run.module, "Workload presets"),
        ]

    def test_placement_targets_need_2_54(self):
        params = _minimal_params(skip_verify_deployable=True)
        params["placement"]["targets"] = [_reference("arrayB")]
        run = _run_main(params, _FakeFleet())
        assert [c.args[1:] for c in run.api_check.call_args_list] == [
            ("2.51", run.module, "Workload presets"),
            ("2.54", run.module, "Placement targets"),
        ]

    def test_check_happens_before_any_preset_call(self):
        array = _FakeFleet()
        seen = []

        def check(arr, version, module, feature):
            seen.append((version, list(array.calls)))

        run = _run_main(_minimal_params(), array, api_check=check)
        assert run.kind == "exit"
        assert seen[0] == ("2.51", [])

    def test_an_old_array_stops_the_run(self):
        array = _FakeFleet()

        def refuse(arr, version, module, feature):
            raise _Fail(
                {"msg": "%s requires API version %s or higher" % (feature, version)}
            )

        run = _run_main(_minimal_params(), array, api_check=refuse)
        assert run.kind == "fail"
        assert "requires API version 2.51 or higher" in run.result["msg"]
        assert array.calls == []

    def test_no_fleet_check_when_nothing_gated_is_used(self):
        run = _run_main(_minimal_params(), _FakeFleet())
        assert len(run.api_check.call_args_list) == 1

    def test_the_rest_versions_in_the_notes_are_the_ones_checked(self):
        yaml = pytest.importorskip("yaml")
        doc = yaml.safe_load(preset_module.DOCUMENTATION)
        notes = " ".join(doc["notes"])
        match = re.search(
            r"REST API ([0-9.]+) or higher, ([0-9.]+) for I\(placement\.targets\)",
            notes,
        )
        assert match, notes
        floor, targets = match.groups()
        run = _run_main(_minimal_params(), _FakeFleet())
        assert run.api_check.call_args.args[1] == floor
        params = _minimal_params()
        params["placement"]["targets"] = [_reference("arrayB")]
        run = _run_main(params, _FakeFleet())
        assert run.api_check.call_args.args[1] == targets
        # No option claims a REST version of its own below the floor
        skip = " ".join(doc["options"]["skip_verify_deployable"]["description"])
        assert "REST" not in skip

    def test_the_sdk_floor_is_the_same_everywhere_it_is_written(self):
        # The module names the floor in its failure message; the collection
        # names it in requirements.txt, the README and the shared doc
        # fragment. They drift apart unless something looks.
        root = pathlib.Path(__file__).resolve().parents[4]
        floors = {}
        for relative in (
            "requirements.txt",
            "README.md",
            "plugins/doc_fragments/everpure.py",
        ):
            path = root / relative
            if not path.is_file():
                # A built artifact, or a copied plugins/ and tests/ tree
                pytest.skip("%s is not in this tree, not a full checkout" % relative)
            text = path.read_text(encoding="utf-8")
            floors[relative] = re.findall(r"py-pure-client\s*>=\s*([0-9.]+)", text)
        for relative, found in floors.items():
            assert found == [preset_module.MIN_SDK_VERSION], (relative, found)


# ---------------------------------------------------------------------------
# A preset read back from a real fleet
# ---------------------------------------------------------------------------

SN1 = "sn1-x50r2-f07-30"
DEFAULT_VOLUME_TEMPLATE = (
    "{{functions.left(workload.name, 25)}}-"
    "{{functions.left(workload.configuration.name, 25)}}-"
    "{{functions.pad_left(workload.configuration.index, 4)}}"
)
DEFAULT_TEMPLATE = (
    "{{functions.left(workload.name, 25)}}-"
    "{{functions.left(workload.configuration.name, 25)}}"
)


def _test1_read_back():
    """The lab preset ansibledev:test1 as py-pure-client 1.96.0 returned it

    client.get_presets_workload(names=["test1"], context_names=["ansibledev"])
    on Purity//FA 6.10.6, REST 2.54, with the item's to_dict(), which leaves out
    every null field and keeps empty text and empty lists.
    """
    with (FIXTURES / "purefa_preset_test1.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _test1_params(**overrides):
    """The task that describes the lab preset test1, written from its fields"""
    params = _params(
        name="test1",
        workload_type="SAP",
        description="test1 description",
        parameters=[
            _param(
                "volsize",
                "integer",
                subtype="size",
                default="1073741824",
                allowed_values=["1073741824", "2147483648"],
                minimum=1073741824,
                maximum=3221225472,
            ),
            _param(
                "stringpar",
                "string",
                description="stringpar",
                default="stringpardef",
                allowed_values=["stringpardef", "anyother"],
            ),
            _param("boolpar", "boolean", description="boolpar decp", default="true"),
            _param(
                "resourcepar",
                "resource_reference",
                description="par resource",
                resource_type="remote-arrays",
                default=SN1,
            ),
            _param(
                "resourcerefpar",
                "resource_reference",
                description="ref resource oar",
                resource_type="storage-classes",
                default="flasharray-c",
            ),
        ],
        placement={
            "name": "default-placement",
            "storage_class": {"name": None, "parameter": "resourcerefpar"},
            "qos": "default-qos",
            "targets": None,
        },
        qos=[_qos("default-qos", iops_limit="1000000", bandwidth_limit="2621440000")],
        snapshots=[
            _snapshot("testsnap", rules=[_rule("86400000", "172800000", "39600000")])
        ],
        replications=[
            _replication("testrepl", SN1, rules=[_rule("900000", "86400000")]),
            _replication("par1", rules=[_rule("3600000", "7200000")]),
        ],
        volumes=[
            _volume("test", count="2", replications=["par1"]),
            _volume(
                "test1",
                count="2",
                provisioned_size="2147483648",
                replications=["testrepl"],
            ),
            _volume(
                "testvol",
                provisioned_size="{{ parameters.volsize }}",
                snapshots=["testsnap"],
                replications=["testrepl"],
            ),
        ],
        tags=[
            _tag("tag1", "{{ parameters.volsize }}"),
            _tag("athing", "{{ parameters.stringpar }}"),
            _tag("boolkey", "{{ parameters.boolpar }}"),
        ],
    )
    params["replications"][1]["target"] = {"name": None, "parameter": "resourcepar"}
    params.update(overrides)
    return params


class TestLabReadBack:
    """normalise_preset of a real read-back against the body of the matching task

    The other idempotency tests use _server_form, the module's own model of what
    the array returns. This one uses what the array returned.
    """

    def test_the_fixture_is_the_lab_preset(self):
        preset = _test1_read_back()
        assert preset["name"] == "test1"
        assert preset["revision"] == 8
        assert preset["context"]["name"] == FLEET
        assert not_a_block_preset(preset) is None
        # The shapes the review called unproven on hardware are all here
        assert preset["snapshot_configurations"][0]["rules"][0]["at"] == "39600000"
        assert preset["periodic_replication_configurations"][0]["remote_targets"]
        assert {p["type"] for p in preset["parameters"]} == {
            "integer",
            "string",
            "boolean",
            "resource_reference",
        }

    def test_the_matching_task_is_valid(self):
        assert validate_preset(_test1_params()) == []

    def test_normalised_read_back_equals_the_body_of_the_matching_task(self):
        preset = _test1_read_back()
        body = carry_over_naming(build_body(_test1_params()), preset)
        assert normalise_preset(preset) == normalise_preset(body)

    def test_the_naming_templates_are_what_carry_over_supplies(self):
        # Without the carry-over the only difference is the array's templates,
        # which are the defaults Purity//FA 6.10.6 fills in
        preset = _test1_read_back()
        bare = normalise_preset(build_body(_test1_params()))
        full = normalise_preset(preset)
        assert bare != full
        # A placement names nothing, so the array gives it no template
        assert "naming_patterns" not in full["placement_configurations"][0]
        for section in CONFIG_SECTIONS:
            if section == "placement_configurations":
                continue
            assert len(full[section]) == len(bare[section]) > 0
            for stored, built in zip(full[section], bare[section]):
                expected = (
                    DEFAULT_VOLUME_TEMPLATE
                    if section == "volume_configurations"
                    else DEFAULT_TEMPLATE
                )
                assert stored.pop("naming_patterns") == [{"template": expected}]
                assert "naming_patterns" not in built
        assert bare == full

    def test_the_documented_default_patterns_are_the_ones_the_array_fills_in(self):
        # The DOCUMENTATION folds each long pattern over several lines, and
        # YAML joins them back with single spaces. What it joins has to be the
        # pattern the fixture shows the array filling in, and the fold has to
        # keep every line well inside the 160 columns ansible-test allows
        yaml = pytest.importorskip("yaml")
        options = yaml.safe_load(preset_module.DOCUMENTATION)["options"]

        def documented(section):
            return " ".join(
                options[section]["suboptions"]["naming_template"]["description"]
            )

        assert DEFAULT_VOLUME_TEMPLATE in documented("volumes")
        assert DEFAULT_TEMPLATE in documented("qos")
        assert DEFAULT_VOLUME_TEMPLATE not in documented("qos")
        for section in ("snapshots", "replications"):
            assert "same as for I(qos)" in documented(section)
        longest = max(len(line) for line in preset_module.DOCUMENTATION.splitlines())
        assert longest <= 120, longest

    def test_the_matching_task_changes_nothing_on_the_fleet(self):
        array = _FakeFleet({"test1": _test1_read_back()})
        run = _run_main(_test1_params(), array)
        assert run.kind == "exit"
        assert run.result["changed"] is False
        assert array.writes() == []
        assert run.result["preset"] == {
            "name": "test1",
            "revision": 8,
            "changed_sections": [],
        }

    @pytest.mark.parametrize(
        "section,change",
        [
            (
                "snapshot_configurations",
                _set("snapshots.0.rules", [_rule("86400000", "172800000", "39600001")]),
            ),
            (
                "snapshot_configurations",
                _set("snapshots.0.rules", [_rule("86400000", "172800000")]),
            ),
            (
                "snapshot_configurations",
                _set("snapshots.0.policy_action", "always_create"),
            ),
            (
                "periodic_replication_configurations",
                _set("replications.0.target", _reference("slc6")),
            ),
            (
                "periodic_replication_configurations",
                # By name instead of through the parameter, which then goes
                _many(
                    _set("replications.1.target", _reference(SN1)),
                    _drop_param("resourcepar"),
                ),
            ),
            ("parameters", _set("parameters.0.subtype", "iops")),
            ("parameters", _set("parameters.0.subtype", None)),
            ("parameters", _set("parameters.2.default", "false")),
            ("parameters", _set("parameters.3.default", "slc6")),
            ("parameters", _set("parameters.4.default", None)),
            ("parameters", _set("parameters.1.allowed_values", ["stringpardef"])),
            (
                "placement_configurations",
                # By name instead of through the parameter, which then goes
                _many(
                    _set("placement.storage_class", _reference("flasharray-c")),
                    _drop_param("resourcerefpar"),
                ),
            ),
            ("qos_configurations", _set("qos.0.bandwidth_limit", "2621440512")),
            ("volume_configurations", _set("volumes.0.count", "3")),
            (
                "workload_tags",
                # A fixed value instead of the parameter, which then goes
                _many(_set("tags.2.value", "true"), _drop_param("boolpar")),
            ),
        ],
        ids=[
            "at",
            "at-removed",
            "policy-action",
            "replication-target-name",
            "replication-target-parameter",
            "subtype",
            "subtype-removed",
            "boolean-default",
            "reference-default",
            "reference-default-removed",
            "string-allowed-values",
            "storage-class-by-name",
            "bandwidth",
            "volume-count",
            "tag-value",
        ],
    )
    def test_each_field_of_the_read_back_is_compared(self, section, change):
        params = _test1_params()
        change(params)
        assert validate_preset(params) == []
        array = _FakeFleet({"test1": _test1_read_back()})
        run = _run_main(params, array)
        assert run.kind == "exit"
        assert run.result["changed"] is True
        assert section in run.result["preset"]["changed_sections"]
        assert array.kinds() == ["get", "put", "get"]


# ---------------------------------------------------------------------------
# main: strings with templates reach the array untouched
# ---------------------------------------------------------------------------


class TestTemplates:
    def test_parameter_template_strings_are_sent_as_written(self):
        params = _params()
        params["parameters"] = [
            _param("size", "integer", default="1073741824", minimum=512),
            _param("copies", "integer", default="2"),
            _param("env", "string", default="dev"),
        ]
        params["volumes"][0]["provisioned_size"] = "{{ parameters.size }}"
        params["volumes"][0]["count"] = "{{ parameters.copies }}"
        array = _FakeFleet()
        run = _run_main(params, array)
        assert run.kind == "exit"
        volume = run.models["PresetWorkloadPost"].call_args.kwargs[
            "volume_configurations"
        ][0]
        assert volume["provisioned_size"] == "{{ parameters.size }}"
        assert volume["count"] == "{{ parameters.copies }}"
        again = _run_main(params, array)
        assert again.result["changed"] is False

    def test_reference_parameters_are_idempotent(self):
        params = _params()
        params["parameters"] = [
            _param("tier", "resource_reference", resource_type="storage-classes"),
            _param("peer", "resource_reference", resource_type="remote-arrays"),
            _param("env", "string", default="dev"),
        ]
        params["placement"]["storage_class"] = {"name": None, "parameter": "tier"}
        params["placement"]["targets"] = [{"name": None, "parameter": "peer"}]
        params["replications"][0]["target"] = {"name": None, "parameter": "peer"}
        array = _FakeFleet()
        first = _run_main(params, array)
        assert first.kind == "exit"
        second = _run_main(params, array)
        assert second.result["changed"] is False


class TestNumericAndTagSpelling:
    def test_numeric_text_is_stripped_and_unpadded_in_the_body(self):
        params = _params()
        params["volumes"][0]["count"] = " 02 "
        params["volumes"][0]["provisioned_size"] = " 1073741824"
        params["qos"][0]["iops_limit"] = "5000 "
        body = build_body(params)
        volume = body["volume_configurations"][0]
        assert volume["count"] == "2"
        assert volume["provisioned_size"] == "1073741824"
        assert body["qos_configurations"][0]["iops_limit"] == "5000"

    def test_templates_are_not_touched_by_numeric_cleaning(self):
        params = _params()
        params["parameters"] = [_param("size", "integer", default="1073741824")]
        params["volumes"][0]["provisioned_size"] = "{{ parameters.size }}"
        body = build_body(params)
        volume = body["volume_configurations"][0]
        assert volume["provisioned_size"] == "{{ parameters.size }}"

    def test_padded_numbers_do_not_count_as_a_difference(self):
        params = _params()
        array = _FakeFleet({"app": _stored(params)})
        padded = _params()
        padded["volumes"][0]["count"] = "0%s" % padded["volumes"][0]["count"]
        run = _run_main(padded, array)
        assert run.result["changed"] is False

    def test_boolean_copyable_read_back_matches_text(self):
        stored = _stored(_params())
        for tag in stored["workload_tags"]:
            tag["copyable"] = tag["copyable"] == "true"
        run = _run_main(_params(), _FakeFleet({"app": stored}))
        assert run.result["changed"] is False

    def test_fleet_read_error_is_reported_with_its_text(self):
        array = _FakeFleet()
        array.get_fleets = lambda: _error_response(401, "Unauthorized.")
        run = _run_main(_params(), array)
        assert run.kind == "fail"
        assert "Reading the fleet failed" in run.result["msg"]
        assert "Unauthorized." in run.result["msg"]
