# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""purefa_preset against the real py-pure-client models and the real Ansible
argument-spec validator.

Every other test module puts mocks for pypureclient and ansible into sys.modules,
and pytest imports every test module before it runs any, so the mocks are in place
by the time anything here runs. The real packages are imported with the mocks set
aside for a moment, and a test skips when its package is not installed (CI gets
ansible-core through pytest-ansible but not py-pure-client).
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
import importlib
import sys
from contextlib import contextmanager

import pytest

from tests.unit.plugins.modules.test_purefa_preset import (
    _minimal_params,
    _param,
    _params,
    _replication,
    _rule,
    _run_main,
    _snapshot,
    _tag,
    _test1_params,
    _test1_read_back,
    _volume,
)
import plugins.modules.purefa_preset as preset_module
from plugins.modules.purefa_preset import (
    build_body,
    carry_over_naming,
    validate_preset,
)


def _under(name, roots):
    return any(name == root or name.startswith(root + ".") for root in roots)


@contextmanager
def _real(name, *roots):
    """Import the real package name with the mocks under roots set aside

    The mocks go back afterwards, so the other test modules are not disturbed.
    Whatever the caller needs from the real package has to be taken while the
    block is open, because the package's lazy submodule imports would find the
    mocks again.
    """
    saved = {
        key: sys.modules.pop(key) for key in list(sys.modules) if _under(key, roots)
    }
    try:
        yield importlib.import_module(name)
    finally:
        for key in list(sys.modules):
            if _under(key, roots):
                del sys.modules[key]
        sys.modules.update(saved)


def _load_sdk():
    try:
        with _real("pypureclient.flasharray", "pypureclient") as flasharray:
            version = sys.modules["pypureclient"].__version__
            models = {
                name: getattr(flasharray, name)
                for name in (
                    "PresetWorkload",
                    "PresetWorkloadPatch",
                    "PresetWorkloadPost",
                )
            }
    except ImportError:
        return None
    return version, models


def _load_validator():
    try:
        with _real("ansible.module_utils.common.arg_spec", "ansible") as arg_spec:
            return arg_spec.ArgumentSpecValidator
    except ImportError:
        return None


SDK = _load_sdk()
VALIDATOR = _load_validator()


def _version_tuple(text):
    return tuple(int(part) for part in text.split(".")[:3])


@pytest.fixture
def sdk():
    """The three real model classes, or a skip"""
    if SDK is None:
        pytest.skip("py-pure-client is not installed")
    version, models = SDK
    floor = preset_module.MIN_SDK_VERSION
    if _version_tuple(version) < _version_tuple(floor):
        pytest.skip("py-pure-client %s is older than the floor %s" % (version, floor))
    return models


@pytest.fixture
def validator():
    """The real ArgumentSpecValidator built from the module's own argument_spec"""
    if VALIDATOR is None:
        pytest.skip("ansible-core is not installed")
    run = _run_main(_minimal_params())
    spec = copy.deepcopy(run.argument_spec)
    # The shared connection options come from the (mocked) module_utils
    spec.update(fa_url=dict(type="str"), api_token=dict(type="str", no_log=True))
    return VALIDATOR(spec, required_if=run.module_kwargs["required_if"])


def _rich_params():
    """Every kind of parameter and reference, templates in every field that takes one"""
    params = _params(
        parameters=[
            _param(
                "vol_size",
                "integer",
                subtype="size",
                display_name="Volume size",
                description="Size of each data volume",
                default="1073741824",
                minimum=1073741824,
                maximum=1099511627776,
            ),
            _param("copies", "integer", default="2", allowed_values=["1", "2", "4"]),
            _param("env", "string", default="dev", allowed_values=["dev", "test"]),
            _param("enc", "boolean", default="true"),
            _param(
                "tier",
                "resource_reference",
                resource_type="storage-classes",
                default="flasharray-x",
            ),
            _param("peer", "resource_reference", resource_type="remote-arrays"),
        ],
        placement={
            "name": "pl",
            "storage_class": {"name": None, "parameter": "tier"},
            "qos": "q1",
            "targets": [{"name": None, "parameter": "peer"}],
        },
        volumes=[
            _volume(
                count="{{ parameters.copies }}",
                provisioned_size="{{ parameters.vol_size }}",
                snapshots=["hourly"],
                replications=["offsite"],
                naming_template=(
                    "{{workload.name}}-data-"
                    "{{functions.pad_left(workload.configuration.index, 3)}}"
                ),
            ),
            _volume("logs", placement="pl"),
        ],
        snapshots=[
            _snapshot(
                policy_action="always_create",
                rules=[
                    _rule("3600000", "86400000"),
                    _rule("86400000", "604800000", suffix="daily"),
                ],
            )
        ],
        replications=[
            _replication(
                rules=[
                    _rule("86400000", "604800000", "3600000"),
                    _rule("172800000", "1209600000"),
                ]
            )
        ],
        tags=[
            _tag("environment", "{{ parameters.env }}"),
            _tag("encrypted", "{{ parameters.enc }}", namespace="team", copyable=False),
        ],
    )
    params["replications"][0]["target"] = {"name": None, "parameter": "peer"}
    return params


class TestRealModels:
    @pytest.mark.parametrize("case", ["full", "minimal", "rich"])
    def test_models_accept_the_body_and_send_it_unchanged(self, sdk, case):
        # The models are strict about types and drop or refuse unknown keys, so
        # what the module builds has to come out of them exactly as it went in
        params = {"full": _params, "minimal": _minimal_params, "rich": _rich_params}[
            case
        ]()
        assert validate_preset(params) == []
        body = build_body(params)
        for name in ("PresetWorkloadPost", "PresetWorkload"):
            model = sdk[name](**body)
            assert model.to_dict() == body, name
            assert model.as_request_dict() == body, name

    def test_the_body_for_the_lab_preset_is_accepted_with_its_carried_templates(
        self, sdk
    ):
        # The body built from the task that matches the lab's test1, with the
        # naming templates the fleet holds carried into it, is what a PUT would
        # send; the models accept it and send it unchanged
        preset = _test1_read_back()
        body = carry_over_naming(build_body(_test1_params()), preset)
        # Every configuration but the placement, which the array gives none
        assert all(
            "naming_patterns" in config
            for section in preset_module.CONFIG_SECTIONS
            if section != "placement_configurations"
            for config in body[section]
        )
        for name in ("PresetWorkloadPost", "PresetWorkload"):
            model = sdk[name](**body)
            assert model.to_dict() == body, name
            assert model.as_request_dict() == body, name

    @pytest.mark.parametrize("subtype", preset_module.SUBTYPES)
    def test_every_subtype_choice_passes_the_models(self, sdk, subtype):
        params = _params()
        params["parameters"] = [_param("size", "integer", subtype=subtype)]
        params["volumes"][0]["provisioned_size"] = "{{ parameters.size }}"
        params["tags"] = None
        body = build_body(params)
        assert sdk["PresetWorkloadPost"](**body).to_dict() == body

    def test_patch_model_carries_only_the_name(self, sdk):
        patch = sdk["PresetWorkloadPatch"](name="renamed")
        assert patch.as_request_dict() == {"name": "renamed"}

    @pytest.mark.parametrize("section", ["snapshots", "replications"])
    def test_models_refuse_a_third_configuration_so_the_validator_must(
        self, sdk, section
    ):
        # The reason for MAX_SNAPSHOT_CONFIGS and MAX_REPLICATION_CONFIGS
        make = _snapshot if section == "snapshots" else _replication
        params = _params()
        params[section] = [make("c1"), make("c2"), make("c3")]
        params["volumes"][0][section] = ["c1", "c2", "c3"]
        assert any(
            "%s has 3 entries, at most 2 are allowed" % section in error
            for error in validate_preset(params)
        )
        body = build_body(params)
        for name in ("PresetWorkloadPost", "PresetWorkload"):
            with pytest.raises(ValueError):
                sdk[name](**body)

    def test_models_want_text_where_the_module_sends_text(self, sdk):
        # Why count and provisioned_size are stringified in build_body
        body = build_body(_minimal_params())
        body["volume_configurations"][0]["count"] = 1
        with pytest.raises(ValueError):
            sdk["PresetWorkloadPost"](**body)


OMIT = object()


def _task(**overrides):
    """A task as a playbook would write it, before AnsibleModule fills it in

    An override of OMIT leaves the option out of the task altogether.
    """
    task = {
        "name": "app",
        "workload_type": "Custom",
        "placement": {"storage_class": {"name": "flasharray-x"}},
        "volumes": [{"name": "data", "provisioned_size": "1073741824"}],
    }
    for key, value in overrides.items():
        if value is OMIT:
            task.pop(key, None)
        else:
            task[key] = value
    return task


class TestRealArgumentSpec:
    def test_every_example_validates_and_passes_the_module_validator(self, validator):
        yaml = pytest.importorskip("yaml")
        examples = yaml.safe_load(preset_module.EXAMPLES.replace("!unsafe", ""))
        for task in examples:
            args = task["everpure.flasharray.purefa_preset"]
            result = validator.validate(args)
            assert result.error_messages == [], task["name"]
            if result.validated_parameters["state"] == "present":
                assert validate_preset(result.validated_parameters) == [], task["name"]

    @pytest.mark.parametrize(
        "change,expected",
        [
            (
                {"placement": {"storage_class": {"name": "a", "parameter": "b"}}},
                "mutually exclusive: name|parameter",
            ),
            (
                {"placement": {"storage_class": {}}},
                "one of the following is required: name, parameter",
            ),
            (
                {
                    "placement": {
                        "storage_class": {"name": "a"},
                        "targets": [{"name": "a", "parameter": "b"}],
                    }
                },
                "mutually exclusive: name|parameter",
            ),
            (
                {
                    "replications": [
                        {
                            "name": "r",
                            "target": {"name": "a", "parameter": "b"},
                            "rules": [{"every": "1", "keep_for": "1"}],
                        }
                    ]
                },
                "mutually exclusive: name|parameter",
            ),
            (
                {"workload_type": OMIT},
                "state is present but all of the following are missing: workload_type",
            ),
            ({"workload_type": "Bogus"}, "value of workload_type must be one of"),
            ({"parameters": [{"name": "p"}]}, "missing required arguments: type"),
            ({"tags": [{"key": "k"}]}, "missing required arguments: value"),
        ],
        ids=[
            "storage-class-both",
            "storage-class-neither",
            "target-both",
            "replication-target-both",
            "present-without-workload-type",
            "bogus-workload-type",
            "parameter-without-type",
            "tag-without-value",
        ],
    )
    def test_the_spec_refuses_what_the_docs_say_it_refuses(
        self, validator, change, expected
    ):
        result = validator.validate(_task(**change))
        assert any(
            expected in message for message in result.error_messages
        ), result.error_messages

    def test_absent_needs_only_the_name(self, validator):
        result = validator.validate({"name": "app", "state": "absent"})
        assert result.error_messages == []

    def test_defaults_and_coercion_are_what_the_module_assumes(self, validator):
        task = _task(
            volumes=[{"name": "data", "provisioned_size": 1073741824, "count": 2}],
            snapshots=[
                {"name": "s", "rules": [{"every": "3600000", "keep_for": 86400000}]}
            ],
            tags=[{"key": "k", "value": 5}],
        )
        task["volumes"][0]["snapshots"] = ["s"]
        result = validator.validate(task)
        assert result.error_messages == []
        params = result.validated_parameters
        assert params["state"] == "present"
        assert params["skip_verify_deployable"] is False
        assert params["placement"]["name"] == "default-placement"
        assert params["volumes"][0]["provisioned_size"] == "1073741824"
        assert params["volumes"][0]["count"] == "2"
        assert params["snapshots"][0]["policy_action"] == "create_or_reuse"
        assert params["snapshots"][0]["rules"][0]["keep_for"] == "86400000"
        assert params["tags"][0] == {
            "key": "k",
            "value": "5",
            "namespace": "default",
            "copyable": True,
        }
        assert validate_preset(params) == []
        volume = build_body(params)["volume_configurations"][0]
        assert volume["count"] == "2"
        assert volume["provisioned_size"] == "1073741824"

    def test_a_template_passes_the_spec_as_text(self, validator):
        task = _task(
            parameters=[{"name": "size", "type": "integer"}],
            volumes=[{"name": "data", "provisioned_size": "{{ parameters.size }}"}],
        )
        result = validator.validate(task)
        assert result.error_messages == []
        assert result.validated_parameters["volumes"][0]["provisioned_size"] == (
            "{{ parameters.size }}"
        )
