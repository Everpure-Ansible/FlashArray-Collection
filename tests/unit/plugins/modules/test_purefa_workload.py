# Copyright: (c) 2026, Pure Storage Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_workload module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

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
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    MagicMock()
)
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.common"] = (
    MagicMock()
)
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.error_handlers"
] = MagicMock()

from plugins.modules.purefa_workload import (
    IGNORED_OPTIONS,
    SEARCH_WHOLE_FLEET,
    _build_workload_parameters,
    _workload_completed,
    _workload_facts,
    delete_workload,
    eradicate_workload,
    recover_workload,
    rename_workload,
    create_workload,
    expand_workload,
    connect_or_disconnect_volumes,
)


class _ApiObject:
    """Stands in for an API object, which Mock cannot.

    Reading a field whose value is null raises AttributeError on the objects the
    SDK builds, rather than returning None, and so does reading a field they do not
    define. Mock returns a value for everything, so a Mock-based fixture cannot
    express a workload the array described with nulls - which is why a crash on a
    null status_details went unnoticed.
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


def _api_workload(**overrides):
    """A Workload as the array really sends it, nulls and all

    The defaults mirror a GET response captured from a live array, where
    status_details and time_remaining both come back null even though the POST that
    created the same workload reported status_details as [].
    """
    fields = {
        "name": "test-workload",
        "context": _ApiObject(name="arrayB"),
        "preset": _ApiObject(name="test-fleet:test-preset"),
        "status": "ready",
        "status_details": None,
        "destroyed": False,
        "created": CREATED_MS,
        "time_remaining": None,
    }
    fields.update(overrides)
    return _ApiObject(**fields)


def _mock_preset_parameter(name, parameter_type):
    preset_parameter = Mock()
    preset_parameter.name = name
    preset_parameter.type = parameter_type
    return preset_parameter


def _mock_get_arrays(name="local-array"):
    """Response for get_arrays(), which returns only the array being addressed"""
    local_array = Mock()
    local_array.name = name
    return Mock(items=[local_array])


# The array reports creation time as epoch milliseconds. Not returned by the
# module - purefa_info reports a workload's own properties - but still set on the
# fixtures, so that reading a workload that has one goes down the same path a real
# one would.
CREATED_MS = 1754587211000


def _mock_workload(
    name="test-workload",
    context="arrayB",
    preset="test-fleet:test-preset",
    status="ready",
    destroyed=False,
    time_remaining=None,
    status_details=None,
):
    """A Workload object as returned by get/post/patch_workloads"""
    workload = Mock()
    # Mock(name=...) sets the mock's own name, so .name must be assigned separately
    workload.name = name
    workload.context = Mock()
    workload.context.name = context
    workload.preset = Mock()
    workload.preset.name = preset
    workload.status = status
    workload.status_details = [] if status_details is None else status_details
    workload.destroyed = destroyed
    workload.created = CREATED_MS
    workload.time_remaining = time_remaining
    return workload


def _mock_workload_response(status_code=200, **kwargs):
    """Response wrapping a single Workload, as post/patch_workloads return

    errors is empty rather than left to Mock. A real response only carries the
    attribute when something went wrong (responses.py: it is set only when not
    None), and a reader that asks whether this answer is complete must not be told
    "yes, and here are some errors" by a fixture that never had any.
    """
    return Mock(status_code=status_code, items=[_mock_workload(**kwargs)], errors=[])


#: Volume names _mock_volumes_response() reports for the workload by default
WORKLOAD_VOLUMES = ["wl-vol1", "wl-vol2"]


def _mock_volumes_response(names=None, status_code=200):
    """Response for get_volumes(), whose items only need a name"""
    volumes = []
    for name in WORKLOAD_VOLUMES if names is None else names:
        volume = Mock()
        volume.name = name
        volumes.append(volume)
    return Mock(status_code=status_code, items=volumes)


def _mock_connections_response(volume_names, host="host1", status_code=200):
    """Response for get_connections(), keyed off conn.volume.name"""
    connections = []
    for name in volume_names:
        connection = Mock()
        connection.volume = Mock()
        connection.volume.name = name
        connection.host = Mock()
        connection.host.name = host
        connections.append(connection)
    return Mock(status_code=status_code, items=connections)


#: The fleet the tests run against. context and placement must name one of these,
#: and "test-fleet" itself is deliberately not a member - naming the fleet is the
#: mistake the validation exists to catch.
FLEET_MEMBERS = ("arrayA", "arrayB", "pod1", "MUCFA21", "MUCFA22")


def _mock_not_found_response(status_code=400):
    """The array's answer for a workload that is not there.

    The message matters as much as the status. Several different 400s come back
    from a workload read and only this one means absence, so a bare Mock without
    an explanation is treated as a real error rather than as "not there".
    """
    return Mock(
        status_code=status_code,
        items=[],
        errors=[Mock(message="Workload does not exist.")],
    )


def _mock_fleet_members(names=FLEET_MEMBERS):
    """Response for get_fleets_members(), whose items wrap the name in .member"""
    members = []
    for name in names:
        member = Mock()
        member.member = Mock()
        member.member.name = name
        members.append(member)
    return Mock(status_code=200, items=members)


def _mock_array(volume_names=None, connected=None, host="host1"):
    """A Mock array with the reads every fact-returning path performs stubbed

    volume_names is what get_volumes reports for the workload; connected is every
    volume the host can see, anywhere on the array.

    get_connections honours the volume_names it is asked for, as the real endpoint
    does, so a test cannot accidentally pass by relying on an unscoped read.
    """
    array = Mock()
    array.get_volumes.return_value = _mock_volumes_response(volume_names)
    array.get_fleets_members.return_value = _mock_fleet_members()
    all_connected = [] if connected is None else connected

    def get_connections(volume_names=None, **kwargs):
        requested = all_connected if volume_names is None else volume_names
        return _mock_connections_response(
            [name for name in all_connected if name in requested], host
        )

    array.get_connections.side_effect = get_connections
    return array


def _mock_recommendation(target="arrayB", status="completed"):
    """A calculated placement recommendation, as get_..._recommendations returns"""
    result = Mock(status=status)
    placement_target = Mock()
    placement_target.name = target
    result.results = [Mock()]
    result.results[0].placements = [Mock()]
    result.results[0].placements[0].targets = [placement_target]
    return result


def _expected_facts(
    name="test-workload",
    context="arrayB",
    status="ready",
    destroyed=False,
    time_remaining=None,
    volumes=None,
):
    """The fact dict _workload_facts() builds for the matching _mock_workload()

    What the task did, not everything the array knows: a workload's own
    properties are purefa_info's job. Flat, with the name as a field rather than
    the key, and the module-owned completed flag derived from the status. Also
    used for check-mode predictions, where the volumes cannot be known in
    advance.
    """
    return {
        "name": name,
        "context": context,
        "status": status,
        "completed": status in ("ready", "destroyed"),
        "destroyed": destroyed,
        "time_remaining": time_remaining,
        "volumes": list(WORKLOAD_VOLUMES) if volumes is None else volumes,
    }


def _params(**overrides):
    """Module params with the defaults every path reads already filled in"""
    params = {
        "name": "test-workload",
        "context": "arrayB",
        "state": "present",
        "preset": None,
        "placement": None,
        "rename": None,
        "host": "",
        "volume_count": None,
        "volume_configuration": None,
        "eradicate": False,
        "recommendation": False,
        # Read by _warn_about_ignored_options on every main() path, and filled in
        # by AnsibleModule from the argument spec whether or not a task sets it
        "parameters": None,
        # wait is on by default, and host cannot be used without it
        "wait": True,
        "wait_timeout": 300,
    }
    params.update(overrides)
    return params


#: The fleet the main()-level tests run against, as _read_fleet_name() reports it
FLEET_NAME = "test-fleet"


def _mock_fleet(homes, fleet=FLEET_NAME):
    """An array in a fleet whose members hold the workload where homes says

    homes maps a member to the fields its copy differs by, so {"arrayB": {}} is a live
    workload on arrayB and {"arrayB": {"destroyed": True}} a destroyed one. Every
    other member, and every other name, answers as the array does for a workload that
    is not there.

    The fleet-wide context answers in one call, as a real array supporting it does;
    the per-member fallback behind it is exercised by asking about an empty fleet.
    """
    array = _mock_array()
    array.get_rest_version.return_value = "2.40"
    fleet_item = Mock()
    fleet_item.name = fleet
    array.get_fleets.return_value = Mock(status_code=200, items=[fleet_item])
    array.get_arrays.return_value = _mock_get_arrays("MUCFA21")
    array.get_presets_workload.return_value = Mock(status_code=200, items=[Mock()])

    def get_workloads(names=None, context_names=None, **kwargs):
        asked = (context_names or [None])[0]
        if (names or [None])[0] != "test-workload":
            return _mock_not_found_response()
        if asked == f"{fleet}.arrays":
            if not homes:
                return _mock_not_found_response()
            return Mock(
                status_code=200,
                items=[
                    _mock_workload(**{"context": member, **fields})
                    for member, fields in homes.items()
                ],
                errors=[],
            )
        if asked in homes:
            return _mock_workload_response(**{"context": asked, **homes[asked]})
        return _mock_not_found_response()

    array.get_workloads.side_effect = get_workloads
    return array


#: Every function main() dispatches an action to. Stubbed together, so that a test
#: about which one runs does not also have to stand up the reads it would perform.
ACTION_FUNCTIONS = (
    "create_workload",
    "expand_workload",
    "recover_workload",
    "rename_workload",
    "connect_or_disconnect_volumes",
    "delete_workload",
    "eradicate_workload",
)


def _run_main(module, array, stub=ACTION_FUNCTIONS, refused=False):
    """Run main() with this module and array standing in for the real ones

    The SDK presence and the version comparison are patched out, as every
    main()-level test needs them, and each action function is replaced by a Mock,
    returned by name - so a test can assert which action ran and which array it was
    handed, without the action itself performing any reads.

    refused says the run is expected to end in a refusal: fail_json is given the
    SystemExit a real one raises, since without it main() carries on past the refusal,
    and the exit is caught here so the caller can still assert on what did and did not
    happen.
    """
    from plugins.modules.purefa_workload import main

    if refused:
        module.fail_json.side_effect = SystemExit
    with ExitStack() as patches:
        for target, replacement in (
            ("HAS_PURESTORAGE", True),
            ("get_array", Mock(return_value=array)),
            ("AnsibleModule", Mock(return_value=module)),
            ("LooseVersion", lambda version: float(version) if version else 0.0),
        ):
            patches.enter_context(
                patch(f"plugins.modules.purefa_workload.{target}", replacement)
            )
        actions = {
            name: patches.enter_context(
                patch(f"plugins.modules.purefa_workload.{name}")
            )
            for name in stub
        }
        if refused:
            with pytest.raises(SystemExit):
                main()
        else:
            main()
    return actions


def _bound_arguments(action, call):
    """A recorded call to one of main()'s action functions, by parameter name

    They are called positionally and they do not all take the same things, so a test
    that cares about one particular argument binds the call against the real signature
    rather than counting places - which also means a reordered signature shows up as
    the wrong value, not as a test that quietly asserts about something else. Read
    after the patch is undone, when the module attribute is the real function again.
    """
    import inspect
    import plugins.modules.purefa_workload as module_under_test

    bound = inspect.signature(getattr(module_under_test, action)).bind(
        *call.args, **call.kwargs
    )
    bound.apply_defaults()
    return bound.arguments


def _create_as_main_does(
    module, array, preset_config, fleet=FLEET_NAME, member=None, others=None
):
    """Create the way main()'s create arm does: the placement settled first

    Deciding where a new workload goes and creating it there are two steps now -
    _choose_placement answers the question, including by asking Fusion, and
    create_workload is handed the answer - so a test about the whole round trip has
    to make both calls to see it.

    member is what _resolve_member_to_search returned, so it defaults to
    SEARCH_WHOLE_FLEET: a create that names a member and does not ask Fusion is
    handed it back unchanged, which is the case that needs no help from this.
    """
    from plugins.modules.purefa_workload import _choose_placement

    return create_workload(
        module,
        array,
        _choose_placement(module, array, fleet, member, preset_config),
        preset_config,
        others=others,
    )


class TestDeleteWorkload:
    """Test cases for delete_workload function"""

    def test_delete_workload_check_mode(self):
        """Check mode predicts the destroyed workload the run would leave"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params()
        mock_array = _mock_array()

        delete_workload(mock_module, mock_array, "arrayB", _mock_workload())

        mock_array.patch_workloads.assert_not_called()
        # wait is on, so a real run would settle on destroyed
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(status="destroyed", destroyed=True)
        )

    def test_delete_workload_check_mode_without_wait(self):
        """Without waiting a real run returns mid-flight, so that is predicted"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(wait=False)
        mock_array = _mock_array()

        delete_workload(mock_module, mock_array, "arrayB", _mock_workload())

        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(status="destroying", destroyed=True)
        )

    def test_delete_with_eradicate_check_mode_names_what_would_be_destroyed(self):
        """An eradicate leaves no facts to read, so only the target is named"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(eradicate=True)
        mock_array = _mock_array()

        delete_workload(mock_module, mock_array, "arrayB", _mock_workload())

        mock_array.patch_workloads.assert_not_called()
        mock_array.delete_workloads.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload={"name": "test-workload", "context": "arrayB"}
        )


class TestEradicateWorkload:
    """Test cases for eradicate_workload function"""

    def test_eradicate_workload_check_mode(self):
        """A dry run names the workload and the array it would be eradicated on

        There are no facts to read off something that will not exist, but "which
        array" is the whole question a --check on an eradicate is asking.
        """
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params()
        mock_array = _mock_array()

        eradicate_workload(mock_module, mock_array, "arrayB")

        mock_array.delete_workloads.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload={"name": "test-workload", "context": "arrayB"}
        )


class TestRecoverWorkload:
    """Test cases for recover_workload function"""

    def test_recover_workload_check_mode(self):
        """Check mode predicts the recovered workload, not the destroyed one read"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params()
        mock_array = _mock_array()

        recover_workload(
            mock_module,
            mock_array,
            "arrayB",
            _mock_workload(status="destroyed", destroyed=True),
        )

        mock_array.patch_workloads.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(status="ready", destroyed=False)
        )

    def test_recover_workload_check_mode_without_wait(self):
        """Without waiting a real run returns while still recovering"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(wait=False)
        mock_array = _mock_array()

        recover_workload(
            mock_module,
            mock_array,
            "arrayB",
            _mock_workload(status="destroyed", destroyed=True),
        )

        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(status="recovering", destroyed=False)
        )


class TestRenameWorkload:
    """Test cases for rename_workload function"""

    def test_rename_workload_check_mode(self):
        """Check mode predicts the new name, not the one the workload has now"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(name="old-workload", rename="new-workload")
        mock_array = _mock_array()

        rename_workload(
            mock_module, mock_array, "arrayB", _mock_workload(name="old-workload")
        )

        mock_array.patch_workloads.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(name="new-workload")
        )
        # The volumes are still read under the name the workload answers to now
        assert (
            mock_array.get_volumes.call_args.kwargs["filter"]
            == "workload.name='old-workload'"
        )


class TestCreateWorkload:
    """Test cases for create_workload function"""

    def test_create_workload_check_mode(self):
        """Check mode predicts the workload the run would create

        Nothing exists to read, so every value is either a parameter, unknowable,
        or - for the creation time - approximately now. Only the volume names stay
        empty, because the array generates those and a guess could be bound to.
        """
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(preset="test-preset", context="pod1")
        mock_array = _mock_array()
        mock_preset_config = Mock()
        mock_preset_config.parameters = []
        mock_preset_config.periodic_replication_configurations = []
        mock_preset_config.placement_configurations = []
        mock_preset_config.qos_configurations = []
        mock_preset_config.snapshot_configurations = []
        mock_preset_config.volume_configurations = []
        mock_preset_config.workload_tags = []

        create_workload(mock_module, mock_array, "pod1", mock_preset_config)

        mock_array.post_workloads.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=True,
            workload=_expected_facts(
                context="pod1",
                status="ready",
                volumes=[],
            ),
        )

    def test_create_workload_check_mode_without_wait(self):
        """Without waiting a real run returns while the workload is creating"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(preset="test-preset", context="pod1", wait=False)
        mock_array = _mock_array()

        create_workload(mock_module, mock_array, "pod1", Mock(parameters=[]))

        mock_module.exit_json.assert_called_once_with(
            changed=True,
            workload=_expected_facts(
                context="pod1",
                status="creating",
                volumes=[],
            ),
        )


class TestWorkloadCompleted:
    """Test cases for the lifecycle classification both wait and facts use"""

    @pytest.mark.parametrize("status", ["ready", "destroyed"])
    def test_terminal_statuses_are_complete(self, status):
        """Nothing is in flight for a workload in a terminal status"""
        mock_module = Mock()

        assert _workload_completed(mock_module, _mock_workload(status=status)) is True
        mock_module.warn.assert_not_called()

    @pytest.mark.parametrize(
        "status", ["creating", "destroying", "eradicating", "recovering"]
    )
    def test_transient_statuses_are_incomplete(self, status):
        """A transient status is in flight, and is expected, so does not warn"""
        mock_module = Mock()

        assert _workload_completed(mock_module, _mock_workload(status=status)) is False
        mock_module.warn.assert_not_called()

    def test_unrecognised_status_is_incomplete_and_warns(self):
        """An unknown status can never be mistaken for success"""
        mock_module = Mock()

        result = _workload_completed(mock_module, _mock_workload(status="quiescing"))

        assert result is False
        mock_module.warn.assert_called_once()
        warning = mock_module.warn.call_args[0][0]
        assert "quiescing" in warning
        assert "test-workload" in warning

    def test_missing_status_is_incomplete_and_warns(self):
        """A Workload model without a status at all is still safe"""
        mock_module = Mock()
        workload = _mock_workload()
        del workload.status

        assert _workload_completed(mock_module, workload) is False
        mock_module.warn.assert_called_once()


class TestBuildWorkloadParameters:
    """Test cases for workload parameter normalization"""

    @patch("plugins.modules.purefa_workload.WorkloadParameter")
    @patch("plugins.modules.purefa_workload.WorkloadParameterValue")
    @patch("plugins.modules.purefa_workload.WorkloadParameterValueResourceReference")
    def test_build_workload_parameters_resource_reference(
        self,
        mock_resource_reference,
        mock_parameter_value,
        mock_parameter,
    ):
        """Test resource reference workload parameters are normalized"""
        mock_module = Mock()
        mock_module.params = {
            "preset": "fleet:Oracle",
            "parameters": [
                {
                    "name": "replication_target",
                    "value": {"resource_reference": {"name": "slcfax2"}},
                }
            ],
        }
        mock_preset_config = Mock()
        mock_preset_config.parameters = [
            _mock_preset_parameter("replication_target", "resource_reference")
        ]

        result = _build_workload_parameters(mock_module, mock_preset_config)

        assert result == [mock_parameter.return_value]
        mock_resource_reference.assert_called_once_with(name="slcfax2")
        mock_parameter_value.assert_called_once_with(
            resource_reference=mock_resource_reference.return_value
        )
        mock_parameter.assert_called_once_with(
            name="replication_target", value=mock_parameter_value.return_value
        )

    @patch("plugins.modules.purefa_workload.WorkloadParameter")
    @patch("plugins.modules.purefa_workload.WorkloadParameterValue")
    def test_build_workload_parameters_boolean_false(
        self, mock_parameter_value, mock_parameter
    ):
        """Test boolean false is treated as a supplied value"""
        mock_module = Mock()
        mock_module.params = {
            "preset": "fleet:Oracle",
            "parameters": [{"name": "enable_replication", "value": {"boolean": False}}],
        }
        mock_preset_config = Mock()
        mock_preset_config.parameters = [
            _mock_preset_parameter("enable_replication", "boolean")
        ]

        result = _build_workload_parameters(mock_module, mock_preset_config)

        assert result == [mock_parameter.return_value]
        mock_parameter_value.assert_called_once_with(boolean=False)
        mock_parameter.assert_called_once_with(
            name="enable_replication", value=mock_parameter_value.return_value
        )

    @patch("plugins.modules.purefa_workload.WorkloadParameter")
    @patch("plugins.modules.purefa_workload.WorkloadParameterValue")
    def test_build_workload_parameters_boolean_false_ignores_none_value_types(
        self, mock_parameter_value, mock_parameter
    ):
        """Test Ansible-normalized None value types are ignored for booleans"""
        mock_module = Mock()
        mock_module.params = {
            "preset": "fleet:Oracle",
            "parameters": [
                {
                    "name": "enable_replication",
                    "value": {
                        "string": None,
                        "integer": None,
                        "boolean": False,
                        "resource_reference": None,
                    },
                }
            ],
        }
        mock_preset_config = Mock()
        mock_preset_config.parameters = [
            _mock_preset_parameter("enable_replication", "boolean")
        ]

        result = _build_workload_parameters(mock_module, mock_preset_config)

        assert result == [mock_parameter.return_value]
        mock_parameter_value.assert_called_once_with(boolean=False)
        mock_parameter.assert_called_once_with(
            name="enable_replication", value=mock_parameter_value.return_value
        )

    def test_build_workload_parameters_rejects_multiple_value_types(self):
        """Test multiple parameter value types are rejected"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "preset": "fleet:Oracle",
            "parameters": [
                {
                    "name": "replication_target",
                    "value": {"string": "slcfax2", "integer": 1},
                }
            ],
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_preset_config = Mock()
        mock_preset_config.parameters = [
            _mock_preset_parameter("replication_target", "string")
        ]

        with pytest.raises(SystemExit):
            _build_workload_parameters(mock_module, mock_preset_config)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_workload.WorkloadParameter")
    @patch("plugins.modules.purefa_workload.WorkloadParameterValue")
    @patch("plugins.modules.purefa_workload.WorkloadParameterValueResourceReference")
    def test_build_workload_parameters_resource_reference_ignores_none_fields(
        self,
        mock_resource_reference,
        mock_parameter_value,
        mock_parameter,
    ):
        """Test Ansible-normalized None fields are ignored for resource references"""
        mock_module = Mock()
        mock_module.params = {
            "preset": "fleet:Oracle",
            "parameters": [
                {
                    "name": "replication_target",
                    "value": {
                        "string": None,
                        "integer": None,
                        "boolean": None,
                        "resource_reference": {
                            "id": None,
                            "name": "slcfax2",
                            "resource_type": None,
                        },
                    },
                }
            ],
        }
        mock_preset_config = Mock()
        mock_preset_config.parameters = [
            _mock_preset_parameter("replication_target", "resource_reference")
        ]

        result = _build_workload_parameters(mock_module, mock_preset_config)

        assert result == [mock_parameter.return_value]
        mock_resource_reference.assert_called_once_with(name="slcfax2")
        mock_parameter_value.assert_called_once_with(
            resource_reference=mock_resource_reference.return_value
        )
        mock_parameter.assert_called_once_with(
            name="replication_target", value=mock_parameter_value.return_value
        )

    def test_build_workload_parameters_rejects_invalid_resource_reference(self):
        """Test invalid resource references are rejected"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "preset": "fleet:Oracle",
            "parameters": [
                {
                    "name": "replication_target",
                    "value": {"resource_reference": {"id": "123", "name": "slcfax2"}},
                }
            ],
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_preset_config = Mock()
        mock_preset_config.parameters = [
            _mock_preset_parameter("replication_target", "resource_reference")
        ]

        with pytest.raises(SystemExit):
            _build_workload_parameters(mock_module, mock_preset_config)

        mock_module.fail_json.assert_called_once()


class TestConnectOrDisconnectVolumes:
    """Test cases for connect_or_disconnect_volumes function"""

    @patch("plugins.modules.purefa_workload._wait_for_status")
    def test_connect_volumes_check_mode(self, mock_wait_for_status):
        """Check mode reports the change without posting a connection"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(context="pod1", host="host1")
        # The host sees neither workload volume yet
        mock_array = _mock_array(connected=[])
        mock_wait_for_status.return_value = None

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "connect", _mock_workload()
        )

        mock_array.post_connections.assert_not_called()
        # Only host connections would change, so the workload is described as read
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts()
        )

    @patch("plugins.modules.purefa_workload._wait_for_status")
    def test_disconnect_volumes_check_mode(self, mock_wait_for_status):
        """Check mode reports the change without deleting a connection"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=WORKLOAD_VOLUMES)

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "disconnect", _mock_workload()
        )

        mock_array.delete_connections.assert_not_called()
        # A disconnect never waits for a status - nothing about it is async
        mock_wait_for_status.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts()
        )

    @patch("plugins.modules.purefa_workload._wait_for_status")
    def test_connect_volumes_no_change(self, mock_wait_for_status):
        """Nothing is posted when the host already sees every workload volume"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=WORKLOAD_VOLUMES)
        mock_wait_for_status.return_value = None

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "connect", _mock_workload()
        )

        mock_array.post_connections.assert_not_called()
        # Nothing changed, but the workload is still described
        mock_module.exit_json.assert_called_once_with(
            changed=False, workload=_expected_facts()
        )

    @patch("plugins.modules.purefa_workload._wait_for_status")
    def test_disconnect_volumes_no_change(self, mock_wait_for_status):
        """Nothing is deleted when the host sees none of the workload volumes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=[])

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "disconnect", _mock_workload()
        )

        mock_array.delete_connections.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=False, workload=_expected_facts()
        )

    @patch("plugins.modules.purefa_workload._wait_for_connections")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload._wait_for_status")
    def test_connect_waits_for_ready_before_connecting(
        self, mock_wait_for_status, mock_check_response, mock_wait_for_connections
    ):
        """ "All connected" only means something once the volume set has settled"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=[])
        mock_wait_for_status.return_value = _mock_workload(context="pod1")

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "connect", _mock_workload(context="pod1")
        )

        mock_wait_for_status.assert_called_once_with(
            mock_module, mock_array, "pod1", "ready"
        )
        # ...and only then is the volume set read and the connection posted
        mock_array.post_connections.assert_called_once()
        mock_wait_for_connections.assert_called_once()


class TestDeleteWorkloadSuccess:
    """Additional test cases for delete_workload function"""

    @patch("plugins.modules.purefa_workload.check_response")
    def test_delete_workload_success(self, mock_check_response):
        """Test delete_workload successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=False)
        mock_array = _mock_array()
        # The PATCH response reports the post-delete state
        mock_array.patch_workloads.return_value = _mock_workload_response(
            status="destroying", destroyed=True, time_remaining=86400000
        )

        delete_workload(mock_module, mock_array, "pod1")

        mock_array.patch_workloads.assert_called_once()
        mock_module.exit_json.assert_called_once_with(
            changed=True,
            workload=_expected_facts(
                status="destroying", destroyed=True, time_remaining=86400000
            ),
        )


class TestEradicateWorkloadSuccess:
    """Additional test cases for eradicate_workload function"""

    @patch("plugins.modules.purefa_workload.check_response")
    def test_eradicate_workload_success(self, mock_check_response):
        """Test eradicate_workload successfully eradicates"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1")
        mock_array = _mock_array()
        mock_array.delete_workloads.return_value = Mock(status_code=200)

        eradicate_workload(mock_module, mock_array, "pod1")

        mock_array.delete_workloads.assert_called_once()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload={"name": "test-workload", "context": "pod1"}
        )


class TestRecoverWorkloadSuccess:
    """Additional test cases for recover_workload function"""

    @patch("plugins.modules.purefa_workload.check_response")
    def test_recover_workload_success(self, mock_check_response):
        """Test recover_workload successfully recovers without host"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=False)
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            status="recovering"
        )

        recover_workload(mock_module, mock_array, "pod1")

        mock_array.patch_workloads.assert_called_once()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(status="recovering")
        )


class TestRenameWorkloadSuccess:
    """Additional test cases for rename_workload function"""

    @patch("plugins.modules.purefa_workload.check_response")
    def test_rename_workload_success(self, mock_check_response):
        """Test rename_workload successfully renames"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            name="old-workload", rename="new-workload", context="pod1"
        )
        mock_array = _mock_array()
        # The PATCH response is keyed by the new name
        mock_array.patch_workloads.return_value = _mock_workload_response(
            name="new-workload"
        )

        rename_workload(mock_module, mock_array, "pod1")

        mock_array.patch_workloads.assert_called_once()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(name="new-workload")
        )
        assert "old-workload" not in mock_module.exit_json.call_args.kwargs["workload"]


class TestCreateWorkloadSuccess:
    """Test cases for create_workload function success scenarios"""

    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_workload_success(self, mock_check_response):
        """Test create_workload successfully creates"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(preset="test-preset", context="pod1", wait=False)
        mock_array = _mock_array()
        # A freshly created workload is still provisioning
        mock_array.post_workloads.return_value = _mock_workload_response(
            context="pod1", status="creating"
        )
        mock_preset_config = Mock()
        mock_preset_config.parameters = []
        mock_preset_config.periodic_replication_configurations = Mock()
        mock_preset_config.placement_configurations = Mock()
        mock_preset_config.qos_configurations = Mock()
        mock_preset_config.snapshot_configurations = Mock()
        mock_preset_config.volume_configurations = Mock()
        mock_preset_config.workload_tags = Mock()

        create_workload(mock_module, mock_array, "pod1", mock_preset_config)

        mock_array.post_workloads.assert_called_once()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(context="pod1", status="creating")
        )

    @patch("plugins.modules.purefa_workload._build_workload_parameters")
    @patch("plugins.modules.purefa_workload.WorkloadPlacementRecommendation")
    @patch("plugins.modules.purefa_workload.WorkloadPost")
    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_workload_passes_parameters_to_recommendation_and_create(
        self,
        mock_check_response,
        mock_wait_for_recommendation,
        mock_workload_post,
        mock_recommendation,
        mock_build_workload_parameters,
    ):
        """Test create_workload passes parameters into recommendation and create APIs"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            recommendation=True,
            # Fusion's recommendation replaces this requested placement
            placement="arrayA",
            wait=False,
        )
        mock_array = _mock_array()
        mock_array.post_workloads.return_value = _mock_workload_response(
            context="arrayB", status="creating"
        )
        mock_calc = Mock()
        mock_calc.name = "calc-1"
        mock_array.post_workloads_placement_recommendations.return_value = Mock(
            status_code=200, items=[mock_calc]
        )
        mock_wait_for_recommendation.return_value = _mock_recommendation("arrayB")
        mock_build_workload_parameters.return_value = [Mock(name="param-1")]
        mock_preset_config = Mock()

        _create_as_main_does(mock_module, mock_array, mock_preset_config)

        # Built once for the question and once for the create - a pure function of
        # the task's options and the preset, so each payload is built where it is
        # used rather than threaded through the other
        assert mock_build_workload_parameters.call_count == 2
        mock_build_workload_parameters.assert_called_with(
            mock_module, mock_preset_config
        )
        mock_recommendation.assert_called_once_with(
            parameters=mock_build_workload_parameters.return_value
        )
        mock_workload_post.assert_called_once_with(
            parameters=mock_build_workload_parameters.return_value
        )
        mock_array.post_workloads.assert_called_once_with(
            names=["test-workload"],
            preset_names=["test-preset"],
            workload=mock_workload_post.return_value,
            context_names=["arrayB"],
        )
        # The fact names the array Fusion chose, not the requested placement
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(context="arrayB", status="creating")
        )
        assert mock_module.exit_json.call_args.kwargs["workload"]["context"] == "arrayB"

    def test_create_workload_check_mode_sends_no_create(self):
        """Test create_workload posts nothing in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(preset="test-preset", context="pod1")
        mock_array = _mock_array()
        mock_preset_config = Mock()
        mock_preset_config.parameters = []

        create_workload(mock_module, mock_array, "pod1", mock_preset_config)

        mock_array.post_workloads.assert_not_called()
        # The contract keeps its shape, so result.workload.context works under --check
        assert set(mock_module.exit_json.call_args.kwargs["workload"]) == set(
            _expected_facts()
        )


class TestExpandWorkloadSuccess:
    """Test cases for expand_workload function success scenarios"""

    @patch("plugins.modules.purefa_workload._wait_for_volumes")
    @patch("plugins.modules.purefa_workload._connect_host")
    @patch("plugins.modules.purefa_workload._create_volume")
    def test_expand_workload_success(
        self, mock_create_vol, mock_connect_host, mock_wait_for_volumes
    ):
        """Test expand_workload successfully expands"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            volume_configuration="vol-config1",
            volume_count=2,
            host="host1",
        )
        mock_array = _mock_array()
        mock_wait_for_volumes.return_value = _mock_workload()
        # Create volume config that matches
        mock_vol_config = Mock()
        mock_vol_config.name = "vol-config1"
        volume_configs = [mock_vol_config]

        expand_workload(
            mock_module, mock_array, "pod1", volume_configs, _mock_workload()
        )

        assert mock_create_vol.call_count == 2
        # The host is reconciled against the full volume set, not just the new
        # volumes - only the ones it cannot see get posted, inside _connect_host
        mock_connect_host.assert_called_once_with(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts()
        )

    @patch("plugins.modules.purefa_workload._create_volume")
    def test_expand_workload_no_match_fails(self, mock_create_vol):
        """Test expand_workload fails when no volume config matches"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            volume_configuration="nonexistent-config",
            volume_count=2,
        )
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = _mock_array()
        # Create volume config with different name
        mock_vol_config = Mock()
        mock_vol_config.name = "other-config"
        volume_configs = [mock_vol_config]

        with pytest.raises(SystemExit):
            expand_workload(
                mock_module, mock_array, "pod1", volume_configs, _mock_workload()
            )

        mock_create_vol.assert_not_called()
        mock_module.fail_json.assert_called_once()
        msg = mock_module.fail_json.call_args.kwargs["msg"]
        assert "does not exist for preset" in msg
        assert "nonexistent-config" in msg

    @patch("plugins.modules.purefa_workload._wait_for_volumes")
    @patch("plugins.modules.purefa_workload._create_volume")
    def test_expand_workload_zero_count_does_not_blame_the_configuration(
        self, mock_create_vol, mock_wait_for_volumes
    ):
        """A count of zero is not evidence that the configuration is missing

        main() rejects volume_count: 0 before this is reached. This pins the other
        half of that fix: the "does not exist for preset" failure is driven by
        whether the configuration matched, not by whether a volume was created.
        """
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            volume_configuration="vol-config1",
            volume_count=0,
        )
        mock_module.fail_json.side_effect = SystemExit
        mock_array = _mock_array()
        mock_wait_for_volumes.return_value = _mock_workload()
        vol_config = Mock()
        vol_config.name = "vol-config1"

        expand_workload(mock_module, mock_array, "pod1", [vol_config], _mock_workload())

        mock_module.fail_json.assert_not_called()
        mock_create_vol.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=False, workload=_expected_facts()
        )


class TestDeleteWorkloadWithEradicate:
    """Test cases for delete_workload with eradicate option"""

    @patch("plugins.modules.purefa_workload.eradicate_workload")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_delete_workload_with_eradicate(
        self, mock_check_response, mock_eradicate_workload
    ):
        """Test delete_workload with eradicate flag"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", eradicate=True)
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            destroyed=True
        )

        delete_workload(mock_module, mock_array, "pod1")

        mock_array.patch_workloads.assert_called_once()
        # The array delete_workload acted on is handed on, not looked up again
        mock_eradicate_workload.assert_called_once_with(mock_module, mock_array, "pod1")

    @patch("plugins.modules.purefa_workload.check_response")
    def test_delete_workload_with_eradicate_reports_only_the_target(
        self, mock_check_response
    ):
        """delete+eradicate exits via eradicate_workload, so that is what reports"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        # The real exit_json terminates the module, so eradicate_workload's exit
        # is the only one that ever runs on this path
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = _params(context="pod1", eradicate=True)
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            destroyed=True
        )
        mock_array.delete_workloads.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            delete_workload(mock_module, mock_array, "pod1")

        mock_array.delete_workloads.assert_called_once()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload={"name": "test-workload", "context": "pod1"}
        )

    @patch("plugins.modules.purefa_workload.check_response")
    def test_delete_workload_without_eradicate(self, mock_check_response):
        """Test delete_workload without eradicate flag"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=False)
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            destroyed=True
        )

        delete_workload(mock_module, mock_array, "pod1")

        mock_array.patch_workloads.assert_called_once()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(destroyed=True)
        )


class TestRecoverWorkloadWithHost:
    """Test cases for recover_workload with host option"""

    @patch("plugins.modules.purefa_workload._wait_for_status")
    @patch("plugins.modules.purefa_workload._connect_host")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_recover_workload_with_host(
        self, mock_check_response, mock_connect_host, mock_wait_for_status
    ):
        """Test recover_workload with host connection"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response()
        mock_wait_for_status.return_value = _mock_workload()

        recover_workload(mock_module, mock_array, "pod1")

        mock_array.patch_workloads.assert_called_once()
        # Recovered volumes may have kept their connections, so the diff inside
        # _connect_host is what stops this reposting and failing
        mock_connect_host.assert_called_once_with(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts()
        )


class TestConnectOrDisconnectVolumesSuccess:
    """Test cases for connect_or_disconnect_volumes success paths"""

    @patch("plugins.modules.purefa_workload._wait_for_connections")
    @patch("plugins.modules.purefa_workload.ConnectionPost")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload._wait_for_status")
    def test_connect_volumes_success(
        self,
        mock_wait_for_status,
        mock_check_response,
        mock_connection_post,
        mock_wait_for_connections,
    ):
        """Test connect_or_disconnect_volumes connects the missing volumes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=[])
        mock_wait_for_status.return_value = _mock_workload()

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "connect", _mock_workload()
        )

        mock_array.post_connections.assert_called_once_with(
            host_names=["host1"],
            volume_names=WORKLOAD_VOLUMES,
            context_names=["pod1"],
            connection=mock_connection_post.return_value,
        )
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts()
        )

    @patch("plugins.modules.purefa_workload._wait_for_connections")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_disconnect_volumes_success(
        self, mock_check_response, mock_wait_for_connections
    ):
        """Test connect_or_disconnect_volumes disconnects the attached volumes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=WORKLOAD_VOLUMES)

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "disconnect", _mock_workload()
        )

        mock_array.delete_connections.assert_called_once_with(
            host_names=["host1"],
            volume_names=WORKLOAD_VOLUMES,
            context_names=["pod1"],
        )
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts()
        )


class TestCreateVolume:
    """Test cases for _create_volume helper function"""

    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.VolumePost")
    @patch("plugins.modules.purefa_workload.WorkloadConfigurationReference")
    def test_create_volume_success(
        self, mock_workload_config, mock_volume_post, mock_check_response
    ):
        """Test _create_volume creates a volume"""
        from plugins.modules.purefa_workload import _create_volume

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(volume_configuration="vol-config", context="pod1")
        mock_array = _mock_array()
        created_volume = Mock()
        created_volume.name = "test-workload-vol1"
        mock_array.post_volumes.return_value = Mock(
            status_code=200, items=[created_volume]
        )

        result = _create_volume(mock_module, mock_array, "pod1")

        mock_array.post_volumes.assert_called_once()
        mock_check_response.assert_called_once()
        # The array generates the name, so it has to come back for a wait to use
        assert result == "test-workload-vol1"


class TestDisconnectHost:
    """Test cases for _disconnect_host

    The invariant here is the one that destroys data if it regresses: only the
    workload's own volumes may ever be disconnected.
    """

    @patch("plugins.modules.purefa_workload.check_response")
    def test_never_widens_beyond_the_workload(self, mock_check_response):
        """A host's connections outside the workload are left strictly alone"""
        from plugins.modules.purefa_workload import _disconnect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1", wait=False)
        mock_array = _mock_array()
        # Deliberately make the read over-return a volume that has nothing to do
        # with this workload, so the intersection guard is what is under test
        mock_array.get_connections.side_effect = None
        mock_array.get_connections.return_value = _mock_connections_response(
            WORKLOAD_VOLUMES + ["other-vol"]
        )

        changed = _disconnect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        assert changed is True
        mock_array.delete_connections.assert_called_once_with(
            host_names=["host1"],
            volume_names=WORKLOAD_VOLUMES,
            context_names=["pod1"],
        )
        # volume_names is always sent, and never names a foreign volume
        call_kwargs = mock_array.delete_connections.call_args.kwargs
        assert "other-vol" not in call_kwargs["volume_names"]
        assert call_kwargs["volume_names"]

    @patch("plugins.modules.purefa_workload.check_response")
    def test_deletes_only_what_is_attached(self, mock_check_response):
        """Converges from a partially attached host rather than failing"""
        from plugins.modules.purefa_workload import _disconnect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1", wait=False)
        mock_array = _mock_array(connected=["wl-vol1"])

        changed = _disconnect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        assert changed is True
        mock_array.delete_connections.assert_called_once_with(
            host_names=["host1"],
            volume_names=["wl-vol1"],
            context_names=["pod1"],
        )

    def test_no_op_when_nothing_is_attached(self):
        """Nothing to remove means no call and no change"""
        from plugins.modules.purefa_workload import _disconnect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1", wait=False)
        mock_array = _mock_array(connected=[])

        changed = _disconnect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        assert changed is False
        mock_array.delete_connections.assert_not_called()

    def test_check_mode_reports_without_acting(self):
        """Check mode returns the diff result but touches nothing"""
        from plugins.modules.purefa_workload import _disconnect_host

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=WORKLOAD_VOLUMES)

        changed = _disconnect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        assert changed is True
        mock_array.delete_connections.assert_not_called()

    def test_no_volumes_reads_and_writes_nothing(self):
        """A workload with no volumes yet cannot have connections to remove"""
        from plugins.modules.purefa_workload import _disconnect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1", wait=False)
        mock_array = _mock_array()

        assert (
            _disconnect_host(mock_module, mock_array, "test-workload", "pod1", [])
            is False
        )
        mock_array.get_connections.assert_not_called()
        mock_array.delete_connections.assert_not_called()


class TestConnectHost:
    """Test cases for _connect_host"""

    @patch("plugins.modules.purefa_workload.ConnectionPost")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_never_reposts_and_never_widens(
        self, mock_check_response, mock_connection_post
    ):
        """Only the volumes the host cannot see are posted

        post_connections has no allow_errors, so reposting wl-vol1 would fail the
        task. This is the regression that makes expand-with-host unusable.
        """
        from plugins.modules.purefa_workload import _connect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1", wait=False)
        # Already on one workload volume, plus one that is none of our business.
        # The read is left unscoped on purpose, so the set difference is what
        # keeps other-vol out of the POST.
        mock_array = _mock_array()
        mock_array.get_connections.side_effect = None
        mock_array.get_connections.return_value = _mock_connections_response(
            ["wl-vol1", "other-vol"]
        )

        changed = _connect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        assert changed is True
        mock_array.post_connections.assert_called_once_with(
            host_names=["host1"],
            volume_names=["wl-vol2"],
            context_names=["pod1"],
            connection=mock_connection_post.return_value,
        )

    @patch("plugins.modules.purefa_workload.check_response")
    def test_no_op_when_fully_connected(self, mock_check_response):
        """Already seeing everything means no call and no change"""
        from plugins.modules.purefa_workload import _connect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1", wait=False)
        mock_array = _mock_array(connected=WORKLOAD_VOLUMES)

        changed = _connect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        assert changed is False
        mock_array.post_connections.assert_not_called()

    def test_check_mode_reports_without_acting(self):
        """Check mode returns the diff result but touches nothing"""
        from plugins.modules.purefa_workload import _connect_host

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=[])

        changed = _connect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        assert changed is True
        mock_array.post_connections.assert_not_called()

    def test_no_volumes_posts_nothing(self):
        """A workload with no volumes yet has nothing to connect

        The old helper reached post_connections with volume_names=[], which the
        array rejects.
        """
        from plugins.modules.purefa_workload import _connect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1", wait=False)
        mock_array = _mock_array()

        assert (
            _connect_host(mock_module, mock_array, "test-workload", "pod1", []) is False
        )
        mock_array.get_connections.assert_not_called()
        mock_array.post_connections.assert_not_called()


class TestScopedReads:
    """Test cases for the two shared read helpers"""

    @patch("plugins.modules.purefa_workload.check_response")
    def test_volume_names_are_checked_and_sorted(self, mock_check_response):
        """The volume read goes through check_response, unlike the old helpers"""
        from plugins.modules.purefa_workload import _workload_volume_names

        mock_module = Mock()
        mock_module.params = _params()
        mock_array = _mock_array(volume_names=["wl-vol2", "wl-vol1"])

        result = _workload_volume_names(
            mock_module, mock_array, "test-workload", "pod1"
        )

        assert result == ["wl-vol1", "wl-vol2"]
        mock_array.get_volumes.assert_called_once_with(
            filter="workload.name='test-workload'", context_names=["pod1"]
        )
        mock_check_response.assert_called_once()

    @patch("plugins.modules.purefa_workload.check_response")
    def test_connections_are_scoped_to_one_host_and_many_volumes(
        self, mock_check_response
    ):
        """The SDK rejects multiple names on two objects at once"""
        from plugins.modules.purefa_workload import _connected_volume_names

        mock_module = Mock()
        mock_module.params = _params()
        mock_array = _mock_array(connected=["wl-vol1"])

        result = _connected_volume_names(
            mock_module, mock_array, "pod1", WORKLOAD_VOLUMES, "host1"
        )

        assert result == {"wl-vol1"}
        mock_array.get_connections.assert_called_once_with(
            host_names=["host1"],
            volume_names=WORKLOAD_VOLUMES,
            context_names=["pod1"],
        )
        assert len(mock_array.get_connections.call_args.kwargs["host_names"]) == 1
        mock_check_response.assert_called_once()


class TestMain:
    """Test cases for main() function"""

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_no_purestorage_sdk(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails when purestorage SDK not available"""
        import pytest
        from plugins.modules.purefa_workload import main

        # Need to patch at module level to override HAS_PURESTORAGE
        with patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", False):
            mock_module = Mock()
            mock_module.fail_json.side_effect = SystemExit(1)
            mock_ansible_module.return_value = mock_module

            with pytest.raises(SystemExit):
                main()

            mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_api_version_too_old(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails when API version is too old"""
        import pytest
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = _params(context="")
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.0"  # Too old (needs 2.40)
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @pytest.mark.parametrize("volume_count", [0, -1])
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_invalid_volume_count(
        self, mock_ansible_module, mock_get_array, volume_count
    ):
        """Test main() fails when volume_count is not positive

        0 is the regression: the guard tested truthiness, so the one value it
        exists to reject short-circuited past it and surfaced as a claim that the
        volume configuration did not exist for the preset.
        """
        from plugins.modules.purefa_workload import main

        mock_module = Mock()
        mock_module.params = _params(state="expand", volume_count=volume_count)
        mock_module.fail_json.side_effect = SystemExit
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "volume_count" in mock_module.fail_json.call_args.kwargs["msg"]
        # Fails before any API call, so nothing was asked of the array
        mock_get_array.assert_not_called()

    @patch("plugins.modules.purefa_workload.create_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_fleet_check_fails(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
        mock_create_workload,
    ):
        """Test main() calls check_response for fleet"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = _params(preset="test-preset")
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        mock_array.get_workloads.return_value = _mock_not_found_response(404)
        mock_preset_config = Mock()
        mock_array.get_presets_workload.return_value = Mock(
            status_code=200, items=[mock_preset_config]
        )
        mock_get_array.return_value = mock_array

        main()

        mock_check_response.assert_called()

    @patch("plugins.modules.purefa_workload.delete_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_state_absent_delete(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
        mock_delete_workload,
    ):
        """Test main() calls delete_workload when state=absent"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        # The member comes from _params() as arrayB: there is no default context,
        # so one has to be named
        mock_module.params = _params(state="absent", preset="test-preset")
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        # Workload exists and not destroyed. The context has to be a real name:
        # the removal path sweeps the fleet to report copies elsewhere, and reads
        # each result's context to name them.
        mock_workload = _mock_workload(context="arrayB", destroyed=False)
        mock_array.get_workloads.return_value = Mock(
            status_code=200, items=[mock_workload]
        )
        mock_get_array.return_value = mock_array

        main()

        mock_delete_workload.assert_called_once()

    @patch("plugins.modules.purefa_workload.eradicate_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_state_absent_eradicate(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
        mock_eradicate_workload,
    ):
        """Test main() calls eradicate_workload when state=absent and eradicate=true"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        # The member comes from _params() as arrayB: there is no default context,
        # so one has to be named
        mock_module.params = _params(
            state="absent", preset="test-preset", eradicate=True
        )
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        # Workload exists and is destroyed. A real context name matters here: the
        # removal path sweeps the fleet and names any copies it finds.
        mock_workload = _mock_workload(context="arrayB", destroyed=True)
        mock_array.get_workloads.return_value = Mock(
            status_code=200, items=[mock_workload]
        )
        mock_get_array.return_value = mock_array

        main()

        mock_eradicate_workload.assert_called_once()

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_no_change(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
    ):
        """Test main() exits with no change when no action needed"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        # The member comes from _params() as arrayB: there is no default context,
        # so one has to be named
        mock_module.params = _params(state="absent", preset="test-preset")
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        # Workload does not exist - nothing to delete, nothing to describe
        mock_array.get_workloads.return_value = _mock_not_found_response(404)
        mock_get_array.return_value = mock_array

        main()

        mock_module.exit_json.assert_called_once_with(changed=False, workload={})

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_no_change_existing_workload_returns_fact(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
    ):
        """An unchanged existing workload is still described on the no-change exit"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        # The member comes from _params() as arrayB: there is no default context,
        # so one has to be named
        mock_module.params = _params(preset="test-preset")
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        # Workload exists, is healthy, and no action applies to it
        mock_array.get_workloads.return_value = _mock_workload_response(
            context="local-array"
        )
        mock_get_array.return_value = mock_array

        main()

        mock_module.exit_json.assert_called_once_with(
            changed=False, workload=_expected_facts(context="local-array")
        )

    @patch("plugins.modules.purefa_workload.create_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_rename_missing_workload_fails(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
        mock_create_workload,
    ):
        """Renaming a workload that is not there fails, rather than creating one
        under the old name - the repeat-rename trap"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = _params(preset="test-preset", rename="new-workload")
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        # The old name is not there to rename
        mock_array.get_workloads.return_value = _mock_not_found_response(404)
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        assert "nothing to rename" in mock_module.fail_json.call_args.kwargs["msg"]
        mock_create_workload.assert_not_called()
        mock_array.get_presets_workload.assert_not_called()

    @patch("plugins.modules.purefa_workload.recover_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_rename_destroyed_workload_fails(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
        mock_recover_workload,
    ):
        """Renaming a destroyed workload fails, rather than silently recovering it
        under the old name and dropping the rename"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = _params(preset="test-preset", rename="new-workload")
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        mock_workload = _mock_workload(context="arrayB", destroyed=True)
        mock_array.get_workloads.return_value = Mock(
            status_code=200, items=[mock_workload]
        )
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        assert "nothing to rename" in mock_module.fail_json.call_args.kwargs["msg"]
        mock_recover_workload.assert_not_called()

    @patch("plugins.modules.purefa_workload.recover_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_state_present_destroyed_recovers_without_rename(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
        mock_recover_workload,
    ):
        """A destroyed workload is still recovered when no rename is requested -
        the new destroyed+rename branch must not swallow the ordinary recover path"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = _params(preset="test-preset")
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        mock_workload = _mock_workload(context="arrayB", destroyed=True)
        mock_array.get_workloads.return_value = Mock(
            status_code=200, items=[mock_workload]
        )
        mock_get_array.return_value = mock_array

        main()

        mock_recover_workload.assert_called_once()

    @patch("plugins.modules.purefa_workload.create_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_main_state_present_not_found_creates_without_rename(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_response,
        mock_loose_version,
        mock_create_workload,
    ):
        """A missing workload is still created when no rename is requested - the
        new not-found+rename branch must not swallow the ordinary create path"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = _params(preset="test-preset")
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet_response = Mock(status_code=200)
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_fleet_response.items = [mock_fleet]
        mock_array.get_fleets.return_value = mock_fleet_response
        mock_array.get_arrays.return_value = _mock_get_arrays()
        mock_array.get_workloads.return_value = _mock_not_found_response(404)
        mock_preset_config = Mock()
        mock_array.get_presets_workload.return_value = Mock(
            status_code=200, items=[mock_preset_config]
        )
        mock_get_array.return_value = mock_array

        main()

        mock_create_workload.assert_called_once()


class TestMainContextDefault:
    """Naming neither context nor placement means the fleet

    Everything except a create acts on a workload that already exists, so the
    member holding it is looked up rather than stated - and a fleet-wide lookup
    gives the same answer whichever member was addressed, which is the property
    the old refusal was protecting. A create is the one operation with nothing to
    look up, and so the one that still cannot default.

    Asserted on the context_names actually sent, because main() no longer writes
    module.params: context and placement are read once and never written.
    """

    def _run_main(self, mock_ansible_module, mock_get_array, params, fails=False):
        from plugins.modules.purefa_workload import main

        mock_module = Mock()
        mock_module.params = _params(
            state="absent",
            preset="test-preset",
            # Omitted, which is now a request to search the whole fleet
            context=None,
        )
        mock_module.params.update(params)
        # A real fail_json ends the module. Without this the mock returns and main()
        # carries on past a refusal, which reads as the refusal not having happened.
        if fails:
            mock_module.fail_json.side_effect = SystemExit
        mock_ansible_module.return_value = mock_module

        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_array.get_fleets.return_value = Mock(status_code=200, items=[mock_fleet])
        mock_array.get_arrays.return_value = _mock_get_arrays("MUCFA21")
        # Workload does not exist, so main() exits without acting on it
        mock_array.get_workloads.return_value = _mock_not_found_response(404)
        mock_get_array.return_value = mock_array

        main()

        return mock_module, mock_array

    def _contexts_read(self, mock_array):
        return [
            call.kwargs.get("context_names", [None])[0]
            for call in mock_array.get_workloads.call_args_list
        ]

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_neither_context_nor_placement_searches_the_fleet(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """The reported bug, inverted: this used to be refused outright, which is
        why 6 of the module's own 11 EXAMPLES failed as written"""
        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module, mock_array = self._run_main(
            mock_ansible_module, mock_get_array, {}
        )

        mock_module.fail_json.assert_not_called()
        assert "test-fleet.arrays" in self._contexts_read(mock_array)

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_naming_nothing_on_a_create_is_refused(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """The one refusal left. A create cannot look its target up, because there
        is nothing there yet - so it is the only operation that must be told."""
        from plugins.modules.purefa_workload import _CREATE_NEEDS_A_MEMBER

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        with pytest.raises(SystemExit):
            self._run_main(
                mock_ansible_module, mock_get_array, {"state": "present"}, fails=True
            )
        mock_module = mock_ansible_module.return_value

        assert mock_module.fail_json.call_args.kwargs[
            "msg"
        ] == _CREATE_NEEDS_A_MEMBER.format(name="test-workload", fleet="test-fleet")

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_an_empty_context_is_refused_rather_than_meaning_the_fleet(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """An empty string is what a computed context comes out as when the
        variable behind it is undefined, and the fleet default would make that a
        fleet-wide destroy. An omission is deliberate; an empty string is not."""
        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        with pytest.raises(SystemExit):
            self._run_main(mock_ansible_module, mock_get_array, {"context": ""}, True)
        mock_module = mock_ansible_module.return_value
        mock_array = mock_get_array.return_value

        assert "empty string" in mock_module.fail_json.call_args.kwargs["msg"]
        # Refused before anything was read
        mock_array.get_workloads.assert_not_called()

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_placement_names_the_member_read(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """The two options are the same thing to the array, so either settles it"""
        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        _unused, mock_array = self._run_main(
            mock_ansible_module, mock_get_array, {"placement": "arrayB"}
        )

        assert self._contexts_read(mock_array)[0] == "arrayB"
        mock_array.get_arrays.assert_not_called()

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_an_explicit_context_is_the_member_read(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """A named member narrows the search to it, and is never widened"""
        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        _unused, mock_array = self._run_main(
            mock_ansible_module, mock_get_array, {"context": "arrayA"}
        )

        assert self._contexts_read(mock_array)[0] == "arrayA"
        mock_array.get_arrays.assert_not_called()


class TestWaitDisabled:
    """wait: false is the fire-and-forget opt-out, available without a host"""

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_does_not_poll(self, mock_check_response, mock_wait_for):
        """Test create_workload issues no polls when wait is false"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(preset="test-preset", context="pod1", wait=False)
        mock_array = _mock_array()
        mock_array.post_workloads.return_value = _mock_workload_response(
            context="pod1", status="creating"
        )

        create_workload(mock_module, mock_array, "pod1", Mock(parameters=[]))

        mock_wait_for.assert_not_called()
        # The immediate POST response is what gets reported
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(context="pod1", status="creating")
        )

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_delete_does_not_poll(self, mock_check_response, mock_wait_for):
        """Test delete_workload issues no polls when wait is false"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=False)
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            context="pod1", status="destroying", destroyed=True
        )

        delete_workload(mock_module, mock_array, "pod1", _mock_workload())

        mock_wait_for.assert_not_called()

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_rename_never_waits(self, mock_check_response, mock_wait_for):
        """A rename is not asynchronous, so it does not wait even when asked"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            name="old-workload", rename="new-workload", context="pod1", wait=True
        )
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            name="new-workload", context="pod1"
        )

        rename_workload(
            mock_module, mock_array, "pod1", _mock_workload(name="old-workload")
        )

        mock_wait_for.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(name="new-workload", context="pod1")
        )

    @patch("plugins.modules.purefa_workload.wait_for", return_value=None)
    @patch("plugins.modules.purefa_workload._create_volume", return_value=None)
    def test_expand_wait_is_a_no_op_in_check_mode(self, mock_create_vol, mock_wait_for):
        """Waiting short-circuits, and the workload falls back to the one given

        wait_for returns None under check mode, so _wait_for_volumes has nothing to
        report and hands back the workload it was passed. Without that fallback the
        caller would be building facts from None.
        """
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            volume_configuration="vol-config1",
            volume_count=1,
        )
        vol_config = Mock()
        vol_config.name = "vol-config1"
        mock_array = _mock_array()

        expand_workload(mock_module, mock_array, "pod1", [vol_config], _mock_workload())

        # The facts describe the workload handed in, not None
        assert (
            mock_module.exit_json.call_args.kwargs["workload"]["name"]
            == "test-workload"
        )
        mock_array.get_workloads.assert_not_called()

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_host_less_eradicate_does_not_poll(
        self, mock_check_response, mock_wait_for
    ):
        """Test eradicate_workload issues no polls when wait is false"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=False)
        mock_array = _mock_array()
        mock_array.delete_workloads.return_value = Mock(status_code=200)

        eradicate_workload(mock_module, mock_array, "pod1")

        mock_wait_for.assert_not_called()


class TestWaitForCreate:
    """Test cases for waiting on workload provisioning"""

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_waits_for_ready(self, mock_check_response, mock_wait_for):
        """Test create_workload waits for the workload to become ready"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(preset="test-preset", context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.post_workloads.return_value = _mock_workload_response(
            context="pod1", status="creating"
        )
        # The settled state the wait resolves to
        mock_wait_for.return_value = _mock_workload(context="pod1", status="ready")

        create_workload(mock_module, mock_array, "pod1", Mock(parameters=[]))

        wait_kwargs = mock_wait_for.call_args.kwargs
        assert wait_kwargs["timeout"] == 300
        assert wait_kwargs["description"] == "workload test-workload to become ready"
        # The facts describe the settled workload, not the immediate POST response
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(context="pod1", status="ready")
        )

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_probe_reads_workload_in_action_context(
        self, mock_check_response, mock_wait_for
    ):
        """Test the poll reads the workload through the context of the action"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(preset="test-preset", context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.post_workloads.return_value = _mock_workload_response(context="pod1")
        mock_array.get_workloads.return_value = _mock_workload_response(context="pod1")
        mock_wait_for.return_value = _mock_workload(context="pod1")

        create_workload(mock_module, mock_array, "pod1", Mock(parameters=[]))

        probe = mock_wait_for.call_args.kwargs["probe"]
        probe()

        mock_array.get_workloads.assert_called_once_with(
            names=["test-workload"],
            context_names=["pod1"],
            # Required whenever the context is a fleet member other than the array
            # being addressed, and harmless when it is not
            allow_errors=True,
        )

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_is_done_only_when_ready(self, mock_check_response, mock_wait_for):
        """Test the wait predicate accepts ready and nothing else"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(preset="test-preset", context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.post_workloads.return_value = _mock_workload_response(context="pod1")
        mock_wait_for.return_value = _mock_workload(context="pod1")

        create_workload(mock_module, mock_array, "pod1", Mock(parameters=[]))

        is_done = mock_wait_for.call_args.kwargs["is_done"]
        assert is_done(_mock_workload(status="ready")) is True
        assert is_done(_mock_workload(status="creating")) is False
        # Terminal, but not the state a create is waiting for
        assert is_done(_mock_workload(status="destroyed")) is False
        # A workload that has gone missing mid-provision is not done
        assert is_done(None) is False

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_timeout_detail_quotes_array_diagnostics(
        self, mock_check_response, mock_wait_for
    ):
        """Test the timeout message can quote status_details verbatim"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(preset="test-preset", context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.post_workloads.return_value = _mock_workload_response(context="pod1")
        mock_wait_for.return_value = _mock_workload(context="pod1")

        create_workload(mock_module, mock_array, "pod1", Mock(parameters=[]))

        detail = mock_wait_for.call_args.kwargs["detail"]
        workload = _mock_workload(status_details=["creating volume foo-vol1"])
        assert detail(workload) == "creating volume foo-vol1"
        assert detail(None) == ""

    @patch("plugins.modules.purefa_workload._build_workload_parameters")
    @patch("plugins.modules.purefa_workload.WorkloadPlacementRecommendation")
    @patch("plugins.modules.purefa_workload.WorkloadPost")
    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_with_recommendation_polls_the_chosen_target(
        self,
        mock_check_response,
        mock_wait_for,
        mock_wait_for_recommendation,
        mock_workload_post,
        mock_recommendation,
        mock_build_workload_parameters,
    ):
        """Test the poll follows the placement Fusion chose, not the requested one"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            recommendation=True,
            placement="arrayA",
            wait=True,
        )
        mock_array = _mock_array()
        mock_calc = Mock()
        mock_calc.name = "calc-1"
        mock_array.post_workloads_placement_recommendations.return_value = Mock(
            status_code=200, items=[mock_calc]
        )
        mock_wait_for_recommendation.return_value = _mock_recommendation("arrayB")
        mock_array.post_workloads.return_value = _mock_workload_response(
            context="arrayB", status="creating"
        )
        mock_wait_for.return_value = _mock_workload(context="arrayB", status="ready")

        _create_as_main_does(mock_module, mock_array, Mock())

        # The poll runs after the create, by which point the workload is there
        mock_array.get_workloads.reset_mock()
        mock_array.get_workloads.return_value = _mock_workload_response(
            context="arrayB"
        )
        mock_wait_for.call_args.kwargs["probe"]()
        mock_array.get_workloads.assert_called_once_with(
            names=["test-workload"],
            context_names=["arrayB"],
            # Required whenever the context is a fleet member other than the array
            # being addressed, and harmless when it is not
            allow_errors=True,
        )
        # The headline case: the caller learns where Fusion put the workload
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(context="arrayB", status="ready")
        )


class TestWaitForRecover:
    """Test cases for waiting on workload recovery"""

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_recover_waits_for_ready(self, mock_check_response, mock_wait_for):
        """Test recover_workload waits for the workload to become ready"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            context="pod1", status="recovering"
        )
        mock_wait_for.return_value = _mock_workload(context="pod1", status="ready")

        recover_workload(
            mock_module,
            mock_array,
            "pod1",
            _mock_workload(status="destroyed", destroyed=True),
        )

        assert (
            mock_wait_for.call_args.kwargs["description"]
            == "workload test-workload to become ready"
        )
        is_done = mock_wait_for.call_args.kwargs["is_done"]
        assert is_done(_mock_workload(status="recovering")) is False
        assert is_done(_mock_workload(status="ready")) is True
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(context="pod1", status="ready")
        )


class TestWaitForDelete:
    """Test cases for waiting on workload deletion"""

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_delete_waits_for_destroyed(self, mock_check_response, mock_wait_for):
        """Test delete_workload waits for the workload to reach destroyed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            context="pod1", status="destroying", destroyed=True
        )
        mock_wait_for.return_value = _mock_workload(
            context="pod1",
            status="destroyed",
            destroyed=True,
            time_remaining=86400000,
        )

        delete_workload(mock_module, mock_array, "pod1", _mock_workload())

        assert (
            mock_wait_for.call_args.kwargs["description"]
            == "workload test-workload to become destroyed"
        )
        is_done = mock_wait_for.call_args.kwargs["is_done"]
        assert is_done(_mock_workload(status="destroying", destroyed=True)) is False
        assert is_done(_mock_workload(status="destroyed", destroyed=True)) is True
        # A destroyed workload is complete but still counting down to eradication,
        # and time_remaining stays in raw milliseconds
        mock_module.exit_json.assert_called_once_with(
            changed=True,
            workload=_expected_facts(
                context="pod1",
                status="destroyed",
                destroyed=True,
                time_remaining=86400000,
            ),
        )


class TestWaitForEradicate:
    """Test cases for waiting on workload eradication"""

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_eradicate_waits_for_absence(self, mock_check_response, mock_wait_for):
        """Eradication is done when the workload is gone, not when a status says so"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.delete_workloads.return_value = Mock(status_code=200)

        eradicate_workload(mock_module, mock_array, "pod1")

        assert (
            mock_wait_for.call_args.kwargs["description"]
            == "workload test-workload to be eradicated"
        )
        is_done = mock_wait_for.call_args.kwargs["is_done"]
        assert is_done(None) is True
        assert is_done(_mock_workload(status="eradicating")) is False
        # Nothing remains to read, so only the target is named
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload={"name": "test-workload", "context": "pod1"}
        )

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_eradicate_probe_treats_404_as_absent(
        self, mock_check_response, mock_wait_for
    ):
        """Test a 404 from the poll is the success condition, not an error"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.delete_workloads.return_value = Mock(status_code=200)
        mock_array.get_workloads.return_value = _mock_not_found_response(404)

        eradicate_workload(mock_module, mock_array, "pod1")

        probe = mock_wait_for.call_args.kwargs["probe"]
        assert probe() is None
        mock_check_response.assert_called_once()  # only the DELETE was checked

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_eradicate_probe_checks_failed_reads(
        self, mock_check_response, mock_wait_for
    ):
        """Test a non-200, non-404 read is reported rather than tracebacked over"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=True)
        mock_array = _mock_array()
        mock_array.delete_workloads.return_value = Mock(status_code=200)
        mock_array.get_workloads.return_value = Mock(status_code=500, items=[])

        eradicate_workload(mock_module, mock_array, "pod1")
        mock_check_response.reset_mock()

        probe = mock_wait_for.call_args.kwargs["probe"]
        try:
            probe()
        except IndexError:
            # check_response is stubbed here, so the real fail_json exit is absent
            pass

        mock_check_response.assert_called_once()


class TestWaitForExpand:
    """Test cases for waiting on workload expansion"""

    def _run_expand(self, mock_wait_for, mock_create_vol, mock_array):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            volume_configuration="vol-config1",
            volume_count=2,
            wait=True,
        )
        mock_create_vol.side_effect = list(WORKLOAD_VOLUMES)
        vol_config = Mock()
        vol_config.name = "vol-config1"
        mock_wait_for.return_value = {
            "workload": _mock_workload(context="pod1", status="ready"),
            "volumes": set(WORKLOAD_VOLUMES),
        }

        expand_workload(
            mock_module,
            mock_array,
            "pod1",
            [vol_config],
            _mock_workload(context="pod1"),
        )

        return mock_module

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload._create_volume")
    def test_expand_waits_on_volumes_and_workload(self, mock_create_vol, mock_wait_for):
        """Test expand waits for both the new volumes and the workload status"""
        mock_array = _mock_array()
        mock_array.get_workloads.return_value = _mock_workload_response(context="pod1")

        mock_module = self._run_expand(mock_wait_for, mock_create_vol, mock_array)

        wait_kwargs = mock_wait_for.call_args.kwargs
        assert wait_kwargs["timeout"] == 300
        assert "test-workload" in wait_kwargs["description"]

        ready = _mock_workload(status="ready")
        is_done = wait_kwargs["is_done"]
        # Both halves satisfied
        assert is_done({"workload": ready, "volumes": set(WORKLOAD_VOLUMES)}) is True
        # A volume this task created has not appeared yet
        assert is_done({"workload": ready, "volumes": {"wl-vol1"}}) is False
        # The volumes exist, but the preset is still deriving configuration
        assert (
            is_done(
                {
                    "workload": _mock_workload(status="creating"),
                    "volumes": set(WORKLOAD_VOLUMES),
                }
            )
            is False
        )
        # The settled workload is what gets reported
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload=_expected_facts(context="pod1", status="ready")
        )

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload._create_volume")
    def test_expand_probe_targets_the_created_volumes(
        self, mock_create_vol, mock_wait_for
    ):
        """Test the poll names the volumes this task created, not a volume count"""
        mock_array = _mock_array()
        mock_array.get_workloads.return_value = _mock_workload_response(context="pod1")

        self._run_expand(mock_wait_for, mock_create_vol, mock_array)

        # The facts read has already happened, so isolate the probe's own call
        mock_array.get_volumes.reset_mock()
        state = mock_wait_for.call_args.kwargs["probe"]()

        mock_array.get_volumes.assert_called_once_with(
            names=WORKLOAD_VOLUMES, context_names=["pod1"]
        )
        assert state["volumes"] == set(WORKLOAD_VOLUMES)
        assert state["workload"].name == "test-workload"

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload._create_volume")
    def test_expand_probe_tolerates_unresolvable_volume_names(
        self, mock_create_vol, mock_wait_for
    ):
        """A name that does not resolve yet means not created, not failed"""
        mock_array = _mock_array()
        mock_array.get_workloads.return_value = _mock_workload_response(context="pod1")

        self._run_expand(mock_wait_for, mock_create_vol, mock_array)

        # Set only now, so the facts read during expand still succeeded
        mock_array.get_volumes.return_value = _mock_volumes_response(
            names=[], status_code=400
        )
        state = mock_wait_for.call_args.kwargs["probe"]()

        assert state["volumes"] == set()
        mock_array.get_workloads.assert_called_once()


class TestHostRequiresWait:
    """host cannot be honoured without waiting, so the combination is rejected

    Connecting means the host sees *every* volume in the workload, which cannot
    be established while the volume set is still growing.
    """

    @pytest.mark.parametrize("state", ["present", "expand", "absent"])
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_host_with_wait_false_fails(
        self, mock_ansible_module, mock_get_array, state
    ):
        """Test main() rejects host with wait: false before touching the array"""
        from plugins.modules.purefa_workload import main

        mock_module = Mock()
        mock_module.params = _params(state=state, host="host1", wait=False)
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "wait" in mock_module.fail_json.call_args.kwargs["msg"]
        # Fails before any API call, so nothing was asked of the array
        mock_get_array.assert_not_called()

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_wait_false_without_host_is_allowed(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Fire-and-forget stays available to tasks that ask for no host work"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0
        mock_module = Mock()
        mock_module.params = _params(
            state="absent", preset="test-preset", volume_count=None, wait=False
        )
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_array.get_fleets.return_value = Mock(status_code=200, items=[mock_fleet])
        mock_array.get_arrays.return_value = _mock_get_arrays()
        mock_array.get_workloads.return_value = _mock_not_found_response(404)
        mock_get_array.return_value = mock_array

        main()

        mock_module.fail_json.assert_not_called()

    def test_wait_defaults_to_true_in_the_argument_spec(self):
        """The default has to be true for host to work without being asked for"""
        import plugins.modules.purefa_workload as module_under_test

        source = open(module_under_test.__file__).read()
        assert 'wait=dict(type="bool", default=True)' in source
        assert 'wait_timeout=dict(type="int", default=300)' in source


class TestCheckingOptionCombinations:
    """Step 1: everything answerable from the task alone, before any API call

    Nothing that depends on what the array holds belongs here - that is
    _decide_action's job, once there is something to decide about. These three are
    all decidable from the task, which is why they are checked before the array is
    even reached.
    """

    def _check(self, **params):
        from plugins.modules.purefa_workload import _check_option_combinations

        module = Mock(params=_params(**params))
        module.fail_json.side_effect = SystemExit
        _check_option_combinations(module)
        return module

    def _refuse(self, **params):
        from plugins.modules.purefa_workload import _check_option_combinations

        module = Mock(params=_params(**params))
        module.fail_json.side_effect = SystemExit
        with pytest.raises(SystemExit):
            _check_option_combinations(module)
        return module.fail_json.call_args.kwargs["msg"]

    def test_a_plain_task_is_accepted(self):
        module = self._check()

        module.fail_json.assert_not_called()

    def test_a_host_cannot_be_used_without_waiting(self):
        message = self._refuse(host="host1", wait=False)

        assert "wait" in message

    def test_waiting_can_still_be_turned_off_without_a_host(self):
        module = self._check(wait=False)

        module.fail_json.assert_not_called()

    @pytest.mark.parametrize("volume_count", [0, -1])
    def test_a_volume_count_that_adds_nothing_is_refused(self, volume_count):
        message = self._refuse(state="expand", volume_count=volume_count)

        assert "positive integer" in message

    def test_an_unset_volume_count_is_not_a_zero(self):
        module = self._check(volume_count=None)

        module.fail_json.assert_not_called()

    @pytest.mark.parametrize("state", ["absent", "expand"])
    def test_a_rename_on_any_other_state_is_refused(self, state):
        """Silently ignored today, so a task asking to both rename and delete reads
        as having renamed"""
        message = self._refuse(state=state, rename="new-workload")

        assert "rename" in message and state in message

    def test_a_rename_on_a_present_state_is_the_supported_one(self):
        module = self._check(state="present", rename="new-workload")

        module.fail_json.assert_not_called()

    def test_a_host_cannot_be_connected_by_a_rename(self):
        """A rename does not read host, so the two together promise a rename that
        also connects. Refused rather than warned about, unlike the options in
        IGNORED_OPTIONS: there is no reading of it to report."""
        message = self._refuse(rename="new-workload", host="host1")

        assert "host" in message and "rename" in message

    def test_a_host_on_its_own_is_the_supported_one(self):
        module = self._check(host="host1")

        module.fail_json.assert_not_called()

    @pytest.mark.parametrize("state", ["present", "expand"])
    def test_an_eradicate_on_any_state_but_absent_is_refused(self, state):
        """Accepted and ignored today, so a task reads as "make sure this exists,
        and destroy it for good" and does neither of the two things it names"""
        message = self._refuse(state=state, eradicate=True)

        assert "eradicate" in message and state in message

    def test_an_eradicate_on_a_removal_is_the_supported_one(self):
        module = self._check(state="absent", eradicate=True)

        module.fail_json.assert_not_called()

    def test_nothing_here_can_ask_the_array_anything(self):
        """It is handed no array, which is the enforcement rather than the
        convention: it runs before get_array(), and none of these questions needs
        one"""
        import inspect

        from plugins.modules.purefa_workload import _check_option_combinations

        signature = inspect.signature(_check_option_combinations)

        assert list(signature.parameters) == ["module"]


class TestOptionsTheActionDoesNotRead:
    """An option set on a task that does not read it is said, not dropped

    Being accepted and silently doing nothing is what this module was reported for,
    in placement's case. None of this is answerable from the task alone - a create
    and a no-op are the same task until the workload has been looked up - which is
    why it is asked once the action is known, and why each warning can name the
    action rather than the state that was asked for.
    """

    #: A value for each option in the table, so a case can be built from the table
    #: itself rather than from a second list that could drift from it
    VALUES = {
        "volume_count": 2,
        "volume_configuration": "config1",
        "parameters": [{"name": "size", "value": {"string": "1G"}}],
    }

    #: Every action main() can dispatch, so "does not read it" is tested against
    #: all of them rather than against one representative
    ACTIONS = (
        "create",
        "expand",
        "recover",
        "rename",
        "connect",
        "disconnect",
        "delete",
        "eradicate",
        "nothing",
    )

    def _warnings(self, action, **params):
        from plugins.modules.purefa_workload import _warn_about_ignored_options

        module = Mock(params=_params(**params))
        _warn_about_ignored_options(module, action)
        return [call.args[0] for call in module.warn.call_args_list]

    def test_the_table_names_an_action_this_module_actually_dispatches(self):
        """A typo in the table would silently warn on every single run"""
        for _option, read_by, _why in IGNORED_OPTIONS:
            assert read_by in self.ACTIONS

    def test_every_option_in_the_table_has_a_value_to_test_with(self):
        assert {option for option, _read_by, _why in IGNORED_OPTIONS} == set(
            self.VALUES
        )

    @pytest.mark.parametrize("option, read_by, _why", IGNORED_OPTIONS)
    def test_the_one_action_that_reads_it_says_nothing(self, option, read_by, _why):
        assert self._warnings(read_by, **{option: self.VALUES[option]}) == []

    @pytest.mark.parametrize("option, read_by, _why", IGNORED_OPTIONS)
    def test_every_other_action_says_so(self, option, read_by, _why):
        for action in self.ACTIONS:
            if action == read_by:
                continue
            warnings = self._warnings(action, **{option: self.VALUES[option]})

            assert len(warnings) == 1, (action, warnings)
            assert option in warnings[0]
            # The action, not the state: which one a state: present task turned out
            # to be is the whole reason this is asked here rather than up front
            assert action in warnings[0]

    @pytest.mark.parametrize("option, _read_by, _why", IGNORED_OPTIONS)
    def test_an_option_the_task_never_set_is_not_reported(self, option, _read_by, _why):
        """The defaults are falsy, and warning about a default would make every
        task noisy enough that the real warnings stop being read"""
        for action in self.ACTIONS:
            assert self._warnings(action) == []

    def test_each_option_is_reported_on_its_own(self):
        """Two ignored options are two warnings. Honest, and it keeps the table a
        table rather than a set of combinations"""
        warnings = self._warnings("nothing", volume_count=2, volume_configuration="c1")

        assert len(warnings) == 2

    @pytest.mark.parametrize("option", ["eradicate", "host", "wait", "recommendation"])
    def test_the_options_deliberately_left_out_stay_out(self, option):
        """eradicate is refused where it cannot apply, and _decide_action has its
        own word for the one case where it is accepted and ignored. host selects
        the action rather than being read by one. wait defaults to true, so listing
        it would warn on every rename anyone ever runs. recommendation reads like
        placement but cannot do what placement did - every path that ignores it
        takes its member from the lookup, so there is no wrong target to warn
        about, and a warning would only fire on the converged second run of a
        recommendation-based create."""
        assert option not in {name for name, _read_by, _why in IGNORED_OPTIONS}

    def test_a_converged_recommendation_create_says_nothing(self):
        """The second run of the commonest task there is. It resolves to a no-op
        because the first run's workload was found, and that is success, not an
        option being dropped."""
        assert self._warnings("nothing", recommendation=True) == []


class TestReadingTheFleetName:
    """Every workload operation is scoped to a fleet, so the name is settled once"""

    def _read(self, response):
        from plugins.modules.purefa_workload import _read_fleet_name

        module = Mock(params=_params())
        module.fail_json.side_effect = SystemExit
        array = _mock_array()
        array.get_fleets.return_value = response
        return module, array

    def _fleets(self, *names, status_code=200):
        fleets = []
        for name in names:
            fleet = Mock()
            fleet.name = name
            fleets.append(fleet)
        return Mock(status_code=status_code, items=fleets)

    def test_the_fleet_this_array_belongs_to_is_returned(self):
        from plugins.modules.purefa_workload import _read_fleet_name

        module, array = self._read(self._fleets("test-fleet"))

        assert _read_fleet_name(module, array) == "test-fleet"
        module.fail_json.assert_not_called()

    def test_an_array_in_no_fleet_is_refused(self):
        """An array outside a fleet has no workloads to manage, so this is a hard
        requirement rather than something to fall back from"""
        from plugins.modules.purefa_workload import _read_fleet_name

        module, array = self._read(self._fleets())

        with pytest.raises(SystemExit):
            _read_fleet_name(module, array)
        assert "fleet" in module.fail_json.call_args.kwargs["msg"]

    def test_a_failed_read_is_not_taken_for_an_array_without_a_fleet(self):
        from plugins.modules.purefa_workload import _read_fleet_name

        module, array = self._read(self._fleets("test-fleet", status_code=500))

        with pytest.raises(SystemExit):
            _read_fleet_name(module, array)


class TestReadingThePresetForTheAction:
    """Only a create and an expand build volumes, so only they read a preset

    Asking the action rather than restating the conditions that produced it is what
    stops a task missing both a preset and the workload from reporting the preset -
    and stops an expand that will fail anyway from paying for the read first.
    """

    FLEET = "test-fleet"

    def _read(self, action, **params):
        from plugins.modules.purefa_workload import _read_preset

        module = Mock(params=_params(**params))
        module.fail_json.side_effect = SystemExit
        array = _mock_array()
        preset_config = Mock()
        array.get_presets_workload.return_value = Mock(
            status_code=200, items=[preset_config]
        )
        with patch("plugins.modules.purefa_workload.check_response"):
            result = _read_preset(module, array, self.FLEET, action)
        return result, module, array, preset_config

    @pytest.mark.parametrize("action", ["create", "expand"])
    def test_the_preset_is_read_for_the_actions_that_build_volumes(self, action):
        result, _unused, array, preset_config = self._read(action, preset="test-preset")

        assert result is preset_config
        array.get_presets_workload.assert_called_once_with(
            names=["test-fleet:test-preset"]
        )

    @pytest.mark.parametrize(
        "action",
        [
            "recover",
            "rename",
            "connect",
            "disconnect",
            "delete",
            "eradicate",
            "nothing",
            "fail",
        ],
    )
    def test_no_preset_is_read_for_anything_else(self, action):
        """Every other outcome works from the workload the array already has, so a
        task that names no preset is not incomplete"""
        result, module, array, _unused = self._read(action)

        assert result is None
        array.get_presets_workload.assert_not_called()
        module.fail_json.assert_not_called()

    @pytest.mark.parametrize("action", ["create", "expand"])
    def test_a_missing_preset_is_refused_where_it_is_needed(self, action):
        with pytest.raises(SystemExit):
            self._read(action, preset=None)

    def test_the_preset_is_qualified_with_the_fleet(self):
        """Presets are fleet objects, named "<fleet>:<preset>" by the API"""
        _unused, module, _unused, _unused = self._read("create", preset="test-preset")

        assert module.params["preset"] == "test-fleet:test-preset"

    def test_the_name_is_left_alone_on_a_path_that_never_reads_it(self):
        """It was qualified before any state was consulted once, so a delete died
        in string concatenation rather than deleting"""
        _unused, module, _unused, _unused = self._read("delete", preset="test-preset")

        assert module.params["preset"] == "test-preset"

    def test_the_actions_that_read_a_preset_are_declared_once(self):
        from plugins.modules.purefa_workload import ACTIONS, PRESET_ACTIONS

        assert PRESET_ACTIONS == {"create", "expand"}
        assert PRESET_ACTIONS <= set(ACTIONS)


class TestAskingAboutAnotherName:
    """A rename involves two names, and the fleet has to be asked about both

    Renaming foo to bar on arrayA where bar already exists on arrayB produces two
    bars. Every reader defaults to the task's own name, so no existing caller has to
    say so.
    """

    FLEET = "test-fleet"

    def _array(self, homes):
        """homes maps a member to the names it holds"""
        array = _mock_array()

        def get_workloads(names=None, context_names=None, **kwargs):
            asked_name = (names or [None])[0]
            asked = (context_names or [None])[0]
            if asked == f"{self.FLEET}.arrays":
                found = [member for member, held in homes.items() if asked_name in held]
                if not found:
                    return _mock_not_found_response()
                return Mock(
                    status_code=200,
                    items=[
                        _mock_workload(name=asked_name, context=member)
                        for member in found
                    ],
                    errors=[],
                )
            if asked_name in homes.get(asked, ()):
                return _mock_workload_response(name=asked_name, context=asked)
            return _mock_not_found_response()

        array.get_workloads.side_effect = get_workloads
        return array

    def test_the_sweep_asks_about_the_name_it_was_given(self):
        from plugins.modules.purefa_workload import _find_across_fleet

        array = self._array({"arrayA": ["test-workload"], "arrayB": ["new-workload"]})

        found = _find_across_fleet(
            Mock(params=_params()), array, self.FLEET, "new-workload"
        )

        assert list(found) == ["arrayB"]

    def test_the_sweep_defaults_to_the_task_own_name(self):
        from plugins.modules.purefa_workload import _find_across_fleet

        array = self._array({"arrayA": ["test-workload"], "arrayB": ["new-workload"]})

        found = _find_across_fleet(Mock(params=_params()), array, self.FLEET)

        assert list(found) == ["arrayA"]

    def test_the_per_member_fallback_asks_about_the_same_name(self):
        """The fleet-wide context is not documented, so the sweep behind it has to
        ask the same question - about the name given, not the task's"""
        from plugins.modules.purefa_workload import _find_across_fleet

        array = self._array({"arrayB": ["new-workload"]})
        # No fleet-wide answer at all, so every member is asked individually
        original = array.get_workloads.side_effect

        def get_workloads(names=None, context_names=None, **kwargs):
            if (context_names or [None])[0] == f"{self.FLEET}.arrays":
                return _mock_not_found_response()
            return original(names=names, context_names=context_names, **kwargs)

        array.get_workloads.side_effect = get_workloads

        found = _find_across_fleet(
            Mock(params=_params()), array, self.FLEET, "new-workload"
        )

        assert list(found) == ["arrayB"]

    def test_the_warning_names_the_name_it_asked_about(self):
        from plugins.modules.purefa_workload import (
            WorkloadLookup,
            _warn_about_copies_elsewhere,
        )

        module = Mock(params=_params(context="arrayA", rename="new-workload"))
        array = self._array({"arrayA": ["test-workload"], "arrayB": ["new-workload"]})
        # The rename is being done on arrayA, where the old name was found
        lookup = WorkloadLookup(
            matches={"arrayA": _mock_workload(context="arrayA")}, swept=False
        )

        _warn_about_copies_elsewhere(module, array, self.FLEET, lookup, "new-workload")

        warning = module.warn.call_args[0][0]
        assert "new-workload" in warning
        assert "arrayB" in warning

    def test_copies_of_another_name_are_looked_up_rather_than_reused(self):
        """A sweep already done answers only for the name it was made about"""
        from plugins.modules.purefa_workload import _copies_elsewhere, WorkloadLookup

        module = Mock(params=_params(context=None))
        array = self._array({"arrayA": ["test-workload"], "arrayB": ["new-workload"]})
        # The lookup swept for test-workload and found it on arrayA
        lookup = WorkloadLookup(
            matches={"arrayA": _mock_workload(context="arrayA")}, swept=True
        )

        assert _copies_elsewhere(module, array, self.FLEET, lookup) == []
        assert _copies_elsewhere(module, array, self.FLEET, lookup, "new-workload") == [
            "arrayB"
        ]


class TestPresetIsOnlyNeededWhereItIsRead:
    """preset is required to create or expand, and ignored everywhere else

    It was qualified with the fleet name before any state was consulted, so a
    delete - which has no reason to name a preset - died in string concatenation
    with a raw TypeError rather than doing the one thing it was asked to do.
    """

    def _array(self, workload=None):
        """A fleet member that either holds a workload of that name, or does not"""
        array = _mock_array()
        array.get_rest_version.return_value = "2.40"
        fleet = Mock()
        fleet.name = "test-fleet"
        array.get_fleets.return_value = Mock(status_code=200, items=[fleet])
        array.get_arrays.return_value = _mock_get_arrays()
        array.get_workloads.return_value = (
            _mock_not_found_response(404)
            if workload is None
            else Mock(status_code=200, items=[workload])
        )
        return array

    @patch("plugins.modules.purefa_workload.delete_workload")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_delete_without_a_preset_reaches_delete_workload(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_check_response,
        mock_delete_workload,
    ):
        """A delete names no preset, and does not need one"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0
        mock_module = Mock()
        # preset is left at the _params() default of None, which is the point
        mock_module.params = _params(state="absent")
        mock_ansible_module.return_value = mock_module
        mock_array = self._array(_mock_workload(context="arrayB", destroyed=False))
        mock_get_array.return_value = mock_array

        main()

        mock_delete_workload.assert_called_once()
        mock_module.fail_json.assert_not_called()
        # Nothing was asked about a preset the task never named
        mock_array.get_presets_workload.assert_not_called()

    @patch("plugins.modules.purefa_workload.create_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_create_without_a_preset_names_the_option(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_create_workload,
    ):
        """The failure names preset rather than blaming the array for a null one"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0
        mock_module = Mock()
        mock_module.params = _params(state="present")
        mock_module.fail_json.side_effect = SystemExit
        mock_ansible_module.return_value = mock_module
        mock_array = self._array()
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        assert "preset" in mock_module.fail_json.call_args.kwargs["msg"]
        # The operator is told what they left out, rather than that the array has
        # no preset called None
        mock_array.get_presets_workload.assert_not_called()
        mock_create_workload.assert_not_called()

    @patch("plugins.modules.purefa_workload.expand_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_expand_with_a_null_preset_names_the_option(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_expand_workload,
    ):
        """required_if cannot catch this one, so the guard in main() has to

        check_required_if counts whether the key is present, not whether it holds a
        value, so an explicit preset: null arrives looking supplied.
        """
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0
        mock_module = Mock()
        mock_module.params = _params(
            state="expand", volume_count=1, volume_configuration="vol-config"
        )
        mock_module.fail_json.side_effect = SystemExit
        mock_ansible_module.return_value = mock_module
        mock_array = self._array(_mock_workload(context="arrayB", destroyed=False))
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        assert "preset" in mock_module.fail_json.call_args.kwargs["msg"]
        mock_expand_workload.assert_not_called()

    @patch("plugins.modules.purefa_workload.create_workload")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_the_preset_is_fleet_qualified_where_it_is_read(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_check_response,
        mock_create_workload,
    ):
        """Presets are fleet objects, so the read has to name <fleet>:<preset>"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0
        mock_module = Mock()
        mock_module.params = _params(state="present", preset="test-preset")
        mock_ansible_module.return_value = mock_module
        mock_array = self._array()
        mock_array.get_presets_workload.return_value = Mock(
            status_code=200, items=[Mock()]
        )
        mock_get_array.return_value = mock_array

        main()

        mock_array.get_presets_workload.assert_called_once_with(
            names=["test-fleet:test-preset"]
        )
        # create_workload reads it from params again, so the qualified name has to
        # still be there afterwards
        assert mock_module.params["preset"] == "test-fleet:test-preset"

    @patch("plugins.modules.purefa_workload.rename_workload")
    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_a_rename_never_qualifies_the_preset(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_rename_workload,
    ):
        """A rename works from the workload the array has, and reads no preset"""
        from plugins.modules.purefa_workload import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0
        mock_module = Mock()
        mock_module.params = _params(
            state="present", name="old-workload", rename="new-workload"
        )
        mock_ansible_module.return_value = mock_module
        mock_array = self._array(
            _mock_workload(name="old-workload", context="arrayB", destroyed=False)
        )
        mock_get_array.return_value = mock_array

        main()

        mock_rename_workload.assert_called_once()
        mock_array.get_presets_workload.assert_not_called()
        # Left as it arrived, on a path that has no use for it
        assert mock_module.params["preset"] is None

    def test_expand_requires_a_preset_in_the_argument_spec(self):
        """An omitted preset on an expand is refused before any API call

        AnsibleModule is mocked in these tests, so required_if never runs and the
        declaration itself is the only thing left to assert.
        """
        import plugins.modules.purefa_workload as module_under_test

        source = open(module_under_test.__file__).read()
        assert '"volume_count", "volume_configuration", "preset"' in source


class TestWaitForConnections:
    """Test cases for waiting on the host operation itself"""

    def _wait_kwargs(self, mock_wait_for, mock_array, connected):
        from plugins.modules.purefa_workload import _wait_for_connections

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")

        _wait_for_connections(
            mock_module, mock_array, "test-workload", "pod1", connected
        )

        return mock_wait_for.call_args.kwargs

    @patch("plugins.modules.purefa_workload.wait_for")
    def test_connect_is_done_only_when_every_volume_is_seen(self, mock_wait_for):
        """Partial attachment is never an acceptable end state"""
        kwargs = self._wait_kwargs(mock_wait_for, _mock_array(), True)

        is_done = kwargs["is_done"]
        assert is_done({"volumes": WORKLOAD_VOLUMES, "seen": {"wl-vol1"}}) is False
        assert (
            is_done({"volumes": WORKLOAD_VOLUMES, "seen": set(WORKLOAD_VOLUMES)})
            is True
        )
        assert kwargs["timeout"] == 300
        assert "connected to" in kwargs["description"]

    @patch("plugins.modules.purefa_workload.wait_for")
    def test_disconnect_is_done_when_none_are_seen(self, mock_wait_for):
        """Done is the host seeing none of *these* volumes"""
        kwargs = self._wait_kwargs(mock_wait_for, _mock_array(), False)

        is_done = kwargs["is_done"]
        assert is_done({"volumes": WORKLOAD_VOLUMES, "seen": {"wl-vol1"}}) is False
        assert is_done({"volumes": WORKLOAD_VOLUMES, "seen": set()}) is True
        assert "disconnected from" in kwargs["description"]

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_probe_never_looks_outside_the_workload(
        self, mock_check_response, mock_wait_for
    ):
        """The connection read is scoped to the workload's volumes

        A host still connected to other-vol must not keep a disconnect spinning,
        which it would if the poll read the host's whole connection list.
        """
        mock_array = _mock_array(connected=["other-vol"])
        kwargs = self._wait_kwargs(mock_wait_for, mock_array, False)

        state = kwargs["probe"]()

        mock_array.get_connections.assert_called_once_with(
            host_names=["host1"],
            volume_names=WORKLOAD_VOLUMES,
            context_names=["pod1"],
        )
        # other-vol is not a workload volume, so it cannot appear in seen
        assert state["seen"] == set()
        assert kwargs["is_done"](state) is True

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_probe_rereads_the_volume_set_each_iteration(
        self, mock_check_response, mock_wait_for
    ):
        """A volume that appears late has to be caught, not missed"""
        mock_array = _mock_array()
        kwargs = self._wait_kwargs(mock_wait_for, mock_array, True)

        mock_array.get_volumes.return_value = _mock_volumes_response(["wl-vol1"])
        first = kwargs["probe"]()
        mock_array.get_volumes.return_value = _mock_volumes_response(
            WORKLOAD_VOLUMES + ["wl-vol3"]
        )
        second = kwargs["probe"]()

        assert first["volumes"] == ["wl-vol1"]
        assert second["volumes"] == WORKLOAD_VOLUMES + ["wl-vol3"]

    @patch("plugins.modules.purefa_workload.wait_for")
    def test_timeout_detail_names_the_outstanding_volumes(self, mock_wait_for):
        """A timeout has to say which volumes are on the wrong side"""
        connect = self._wait_kwargs(mock_wait_for, _mock_array(), True)
        assert (
            connect["detail"]({"volumes": WORKLOAD_VOLUMES, "seen": {"wl-vol1"}})
            == "wl-vol2"
        )

        disconnect = self._wait_kwargs(mock_wait_for, _mock_array(), False)
        assert (
            disconnect["detail"]({"volumes": WORKLOAD_VOLUMES, "seen": {"wl-vol1"}})
            == "wl-vol1"
        )


class TestHostConnectionsAreWaitedOn:
    """The host operation is covered by wait, not just the workload"""

    @patch("plugins.modules.purefa_workload._wait_for_connections")
    @patch("plugins.modules.purefa_workload.ConnectionPost")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_connect_waits_for_the_connections(
        self, mock_check_response, mock_connection_post, mock_wait_for_connections
    ):
        """Test _connect_host waits for the connections it just posted"""
        from plugins.modules.purefa_workload import _connect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=[])

        _connect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        mock_wait_for_connections.assert_called_once_with(
            mock_module, mock_array, "test-workload", "pod1", connected=True
        )

    @patch("plugins.modules.purefa_workload._wait_for_connections")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_disconnect_waits_for_the_connections_to_go(
        self, mock_check_response, mock_wait_for_connections
    ):
        """Test _disconnect_host waits for the connections it just deleted"""
        from plugins.modules.purefa_workload import _disconnect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=WORKLOAD_VOLUMES)

        _disconnect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        mock_wait_for_connections.assert_called_once_with(
            mock_module, mock_array, "test-workload", "pod1", connected=False
        )

    @patch("plugins.modules.purefa_workload._wait_for_connections")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_no_wait_when_nothing_changed(
        self, mock_check_response, mock_wait_for_connections
    ):
        """Nothing was posted, so there is nothing to wait for"""
        from plugins.modules.purefa_workload import _connect_host

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=WORKLOAD_VOLUMES)

        _connect_host(
            mock_module, mock_array, "test-workload", "pod1", WORKLOAD_VOLUMES
        )

        mock_wait_for_connections.assert_not_called()


class TestVolumeReadsHappenOnce:
    """The volume list is read at most once per run, not once per consumer"""

    @patch("plugins.modules.purefa_workload._wait_for_connections")
    @patch("plugins.modules.purefa_workload.ConnectionPost")
    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload._wait_for_status")
    def test_connect_path_reads_volumes_once(
        self,
        mock_wait_for_status,
        mock_check_response,
        mock_connection_post,
        mock_wait_for_connections,
    ):
        """The diff and the facts share one read, unlike the old helpers"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array(connected=[])
        mock_wait_for_status.return_value = _mock_workload()

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "connect", _mock_workload()
        )

        mock_array.get_volumes.assert_called_once()

    @patch("plugins.modules.purefa_workload.check_response")
    def test_rename_path_reads_volumes_once(self, mock_check_response):
        """Only the facts need them here"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(
            name="old-workload", rename="new-workload", context="pod1"
        )
        mock_array = _mock_array()
        mock_array.patch_workloads.return_value = _mock_workload_response(
            name="new-workload"
        )

        rename_workload(
            mock_module, mock_array, "pod1", _mock_workload(name="old-workload")
        )

        mock_array.get_volumes.assert_called_once()
        # Read under the new name, since that is what the workload is called now
        assert (
            mock_array.get_volumes.call_args.kwargs["filter"]
            == "workload.name='new-workload'"
        )

    @patch("plugins.modules.purefa_workload.check_response")
    def test_eradicate_reads_no_volumes(self, mock_check_response):
        """There is no workload left to read, so only the target is named"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", wait=False)
        mock_array = _mock_array()
        mock_array.delete_workloads.return_value = Mock(status_code=200)

        eradicate_workload(mock_module, mock_array, "pod1")

        mock_array.get_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=True, workload={"name": "test-workload", "context": "pod1"}
        )


#: Every way this module can change the array. Asserted as a set so a future
#: unguarded write is caught wherever it is added, not just where one is expected.
WRITE_METHODS = (
    "post_volumes",
    "post_workloads",
    "patch_workloads",
    "delete_workloads",
    "post_connections",
    "delete_connections",
)


def _writes(mock_array):
    """Which write endpoints were called, and how often"""
    return {
        method: getattr(mock_array, method).call_count
        for method in WRITE_METHODS
        if getattr(mock_array, method).call_count
    }


class TestCheckModeMakesNoChanges:
    """--check must not touch the array on any path

    The one deliberate exception is the placement recommendation, which is a
    calculation rather than a change and is covered separately.
    """

    def _module(self, **params):
        module = Mock()
        module.check_mode = True
        module.params = _params(**params)
        return module

    @patch("plugins.modules.purefa_workload.VolumePost")
    @patch("plugins.modules.purefa_workload.WorkloadConfigurationReference")
    def test_expand_creates_no_volumes(self, mock_config_ref, mock_volume_post):
        """Test expand posts no volumes under --check

        The regression: _create_volume had no guard, so a --check run of
        volume_count: 3 created three volumes for real.
        """
        mock_module = self._module(
            preset="test-preset",
            context="pod1",
            volume_configuration="vol-config1",
            volume_count=3,
        )
        mock_array = _mock_array()
        vol_config = Mock()
        vol_config.name = "vol-config1"

        expand_workload(
            mock_module,
            mock_array,
            "pod1",
            [vol_config],
            _mock_workload(context="pod1"),
        )

        assert _writes(mock_array) == {}
        # The change is still reported, it is just not made
        assert mock_module.exit_json.call_args.kwargs["changed"] is True

    def test_create_writes_nothing(self):
        """Test create posts no workload under --check"""
        mock_module = self._module(preset="test-preset", context="pod1")
        mock_array = _mock_array()

        create_workload(mock_module, mock_array, "pod1", Mock(parameters=[]))

        assert _writes(mock_array) == {}

    @patch("plugins.modules.purefa_workload.WorkloadPatch")
    def test_delete_writes_nothing(self, mock_workload_patch):
        """Test delete patches nothing under --check"""
        mock_module = self._module(context="pod1")
        mock_array = _mock_array()

        delete_workload(mock_module, mock_array, "pod1", _mock_workload())

        assert _writes(mock_array) == {}

    @patch("plugins.modules.purefa_workload.WorkloadPatch")
    def test_delete_with_eradicate_writes_nothing(self, mock_workload_patch):
        """Test delete + eradicate neither patches nor deletes under --check"""
        mock_module = self._module(context="pod1", eradicate=True)
        mock_array = _mock_array()

        delete_workload(mock_module, mock_array, "pod1", _mock_workload())

        assert _writes(mock_array) == {}

    def test_eradicate_writes_nothing(self):
        """Test eradicate deletes nothing under --check"""
        mock_module = self._module(context="pod1")
        mock_array = _mock_array()

        eradicate_workload(mock_module, mock_array, "pod1")

        assert _writes(mock_array) == {}

    @patch("plugins.modules.purefa_workload.WorkloadPatch")
    def test_recover_writes_nothing(self, mock_workload_patch):
        """Test recover patches nothing under --check"""
        mock_module = self._module(context="pod1")
        mock_array = _mock_array()

        recover_workload(
            mock_module,
            mock_array,
            "pod1",
            _mock_workload(status="destroyed", destroyed=True),
        )

        assert _writes(mock_array) == {}

    @patch("plugins.modules.purefa_workload.WorkloadPatch")
    def test_rename_writes_nothing(self, mock_workload_patch):
        """Test rename patches nothing under --check"""
        mock_module = self._module(context="pod1", rename="new-workload")
        mock_array = _mock_array()

        rename_workload(mock_module, mock_array, "pod1", _mock_workload())

        assert _writes(mock_array) == {}

    @patch("plugins.modules.purefa_workload._wait_for_status")
    def test_connect_writes_nothing(self, mock_wait_for_status):
        """Test connecting a host posts no connections under --check"""
        mock_module = self._module(context="pod1", host="host1")
        mock_array = _mock_array(connected=[])
        mock_wait_for_status.return_value = None

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "connect", _mock_workload()
        )

        assert _writes(mock_array) == {}
        assert mock_module.exit_json.call_args.kwargs["changed"] is True

    def test_disconnect_writes_nothing(self):
        """Test disconnecting a host deletes no connections under --check"""
        mock_module = self._module(context="pod1", host="host1")
        mock_array = _mock_array(connected=WORKLOAD_VOLUMES)

        connect_or_disconnect_volumes(
            mock_module, mock_array, "pod1", "disconnect", _mock_workload()
        )

        assert _writes(mock_array) == {}
        assert mock_module.exit_json.call_args.kwargs["changed"] is True


class TestCreateVolumeCheckMode:
    """Test cases for _create_volume under --check"""

    def test_creates_nothing_and_names_nothing(self):
        """No volume was created, so there is no name to return"""
        from plugins.modules.purefa_workload import _create_volume

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(volume_configuration="vc1", context="pod1")
        mock_array = _mock_array()

        assert _create_volume(mock_module, mock_array, "pod1") is None
        mock_array.post_volumes.assert_not_called()

    @patch("plugins.modules.purefa_workload.VolumePost")
    @patch("plugins.modules.purefa_workload.WorkloadConfigurationReference")
    @patch("plugins.modules.purefa_workload._wait_for_volumes")
    def test_expand_collects_no_placeholder_names(
        self, mock_wait_for_volumes, mock_config_ref, mock_volume_post
    ):
        """The volume wait must not be handed a list of Nones"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            volume_configuration="vol-config1",
            volume_count=2,
        )
        mock_array = _mock_array()
        workload = _mock_workload(context="pod1")
        mock_wait_for_volumes.return_value = workload
        vol_config = Mock()
        vol_config.name = "vol-config1"

        expand_workload(mock_module, mock_array, "pod1", [vol_config], workload)

        # Nothing was created, so there are no names to wait on - not two Nones
        mock_wait_for_volumes.assert_called_once_with(
            mock_module, mock_array, "pod1", [], workload
        )
        # Only the volumes that already exist can be reported
        assert (
            mock_module.exit_json.call_args.kwargs["workload"]["volumes"]
            == WORKLOAD_VOLUMES
        )


class TestWaitForRecommendation:
    """Test cases for the placement recommendation poll

    Replaces an unbounded `while result.status != "completed"` loop that had no
    timeout, no response check, and no handling of the failed state.
    """

    def _wait_kwargs(self, mock_wait_for, mock_array, check_mode=False):
        from plugins.modules.purefa_workload import _wait_for_recommendation

        mock_module = Mock()
        mock_module.check_mode = check_mode
        mock_module.params = _params(preset="test-fleet:test-preset", context="pod1")

        _wait_for_recommendation(mock_module, mock_array, "pod1", "calc-1")

        return mock_wait_for.call_args.kwargs

    @patch("plugins.modules.purefa_workload.wait_for")
    def test_done_only_on_completed(self, mock_wait_for):
        """processing is not done; completed is"""
        kwargs = self._wait_kwargs(mock_wait_for, _mock_array())

        is_done = kwargs["is_done"]
        assert is_done(Mock(status="processing")) is False
        assert is_done(Mock(status="completed")) is True
        assert kwargs["timeout"] == 300
        assert "test-fleet:test-preset" in kwargs["description"]

    @patch("plugins.modules.purefa_workload.wait_for")
    def test_failed_is_terminal(self, mock_wait_for):
        """A placement that cannot be satisfied fails rather than spinning

        This endpoint is the reason wait_for has an is_failed hook - a workload has
        no failure state, but a recommendation does.
        """
        kwargs = self._wait_kwargs(mock_wait_for, _mock_array())

        is_failed = kwargs["is_failed"]
        assert is_failed(Mock(status="processing")) is None
        assert is_failed(Mock(status="completed")) is None
        message = is_failed(Mock(status="failed"))
        assert message and "test-fleet:test-preset" in message

    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.wait_for")
    def test_probe_checks_the_response(self, mock_wait_for, mock_check_response):
        """The old loop read .items straight off an unchecked response"""
        mock_array = _mock_array()
        mock_array.get_workloads_placement_recommendations.return_value = Mock(
            status_code=200, items=[_mock_recommendation()]
        )
        kwargs = self._wait_kwargs(mock_wait_for, mock_array)

        kwargs["probe"]()

        mock_array.get_workloads_placement_recommendations.assert_called_once_with(
            names=["calc-1"], context_names=["pod1"]
        )
        mock_check_response.assert_called_once()

    @patch("plugins.modules.purefa_workload.wait_for")
    def test_runs_under_check_mode(self, mock_wait_for):
        """A calculation changes nothing, so --check may wait on it"""
        kwargs = self._wait_kwargs(mock_wait_for, _mock_array(), check_mode=True)

        assert kwargs["skip_in_check_mode"] is False


class TestCheckModePredictsTheRealRun:
    """--check and a real run must agree on the shape of what they return"""

    @patch("plugins.modules.purefa_workload._build_workload_parameters")
    @patch("plugins.modules.purefa_workload.WorkloadPlacementRecommendation")
    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_check_mode_create_reports_the_recommended_target(
        self,
        mock_check_response,
        mock_wait_for_recommendation,
        mock_recommendation,
        mock_build_workload_parameters,
    ):
        """The headline case, and only reachable because the calculation still runs"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(
            preset="test-preset",
            context="pod1",
            recommendation=True,
            placement="arrayA",
        )
        mock_array = _mock_array()
        calculation = Mock()
        calculation.name = "calc-1"
        mock_array.post_workloads_placement_recommendations.return_value = Mock(
            status_code=200, items=[calculation]
        )
        mock_wait_for_recommendation.return_value = _mock_recommendation("arrayB")

        _create_as_main_does(mock_module, mock_array, Mock())

        # The calculation ran, so --check can name the array Fusion would choose
        mock_array.post_workloads_placement_recommendations.assert_called_once()
        mock_array.post_workloads.assert_not_called()
        assert mock_module.exit_json.call_args.kwargs["workload"]["context"] == "arrayB"

    @patch("plugins.modules.purefa_workload.WorkloadPatch")
    @patch("plugins.modules.purefa_workload._wait_for_status")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_delete_returns_the_same_keys_either_way(
        self, mock_check_response, mock_wait_for_status, mock_workload_patch
    ):
        """A playbook binding to a key must not find it missing in one mode"""
        settled = _mock_workload(status="destroyed", destroyed=True)
        mock_wait_for_status.return_value = settled

        checked = Mock()
        checked.check_mode = True
        checked.params = _params(context="pod1")
        delete_workload(checked, _mock_array(), "pod1", _mock_workload())

        real = Mock()
        real.check_mode = False
        real.params = _params(context="pod1")
        real_array = _mock_array()
        real_array.patch_workloads.return_value = Mock(status_code=200, items=[settled])
        delete_workload(real, real_array, "pod1", _mock_workload())

        predicted = checked.exit_json.call_args.kwargs["workload"]
        actual = real.exit_json.call_args.kwargs["workload"]
        assert set(predicted) == set(actual)
        # And on the fields a prediction can be sure of, they agree outright
        for key in ("name", "context", "status", "completed", "destroyed"):
            assert predicted[key] == actual[key], key

    @patch("plugins.modules.purefa_workload.WorkloadPatch")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_delete_with_eradicate_names_the_target_either_way(
        self, mock_check_response, mock_workload_patch
    ):
        """The divergence this fixes: --check used to return facts, a real run {}

        Both now report the one thing still true of an eradicated workload - which
        name, on which array - so the dry run says what the real run will say.
        """
        checked = Mock()
        checked.check_mode = True
        checked.params = _params(context="pod1", eradicate=True)
        delete_workload(checked, _mock_array(), "pod1", _mock_workload())

        real = Mock()
        real.check_mode = False
        real.params = _params(context="pod1", eradicate=True)
        # The real exit_json terminates, so eradicate_workload's is the only one
        real.exit_json.side_effect = SystemExit(0)
        real_array = _mock_array()
        real_array.patch_workloads.return_value = Mock(
            status_code=200, items=[_mock_workload(destroyed=True)]
        )
        real_array.delete_workloads.return_value = Mock(status_code=200)
        with pytest.raises(SystemExit):
            delete_workload(real, real_array, "pod1", _mock_workload())

        eradicated = {"name": "test-workload", "context": "pod1"}
        assert checked.exit_json.call_args.kwargs["workload"] == eradicated
        assert real.exit_json.call_args.kwargs["workload"] == eradicated

    @pytest.mark.parametrize(
        "wait,expected_status",
        [(True, "ready"), (False, "creating")],
    )
    def test_predicted_completed_agrees_with_predicted_status(
        self, wait, expected_status
    ):
        """completed is derived, so it can never contradict the status reported"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _params(preset="test-preset", context="pod1", wait=wait)

        create_workload(mock_module, _mock_array(), "pod1", Mock(parameters=[]))

        facts = mock_module.exit_json.call_args.kwargs["workload"]
        assert facts["status"] == expected_status
        assert facts["completed"] is (expected_status == "ready")


class TestFactsShapeIsDefinedOnce:
    """A read workload and a predicted one must describe themselves identically"""

    def test_read_and_predicted_return_the_same_keys(self):
        """_facts is the single definition, so the two builders cannot drift"""
        from plugins.modules.purefa_workload import _facts, _workload_facts

        mock_module = Mock()
        mock_module.params = _params(preset="test-preset", context="pod1")
        mock_array = _mock_array()

        read = _workload_facts(mock_module, mock_array, _mock_workload(), "pod1")
        predicted_create = _facts(
            mock_module,
            name=mock_module.params["name"],
            context="pod1",
            status="ready",
        )
        predicted_change = _workload_facts(
            mock_module, mock_array, _mock_workload(), "pod1", destroyed=True
        )

        assert set(read) == set(predicted_create) == set(predicted_change)
        # ...and it is the documented contract, not just self-consistent
        assert set(read) == set(_expected_facts())


class TestPredictedFacts:
    """Test cases for describing a workload that has not been changed yet

    A prediction is expressed by passing changes, so it goes through the same two
    builders a real run does rather than a separate code path.
    """

    def test_create_knows_only_what_it_was_asked_for(self):
        """With no workload to read, params and the clock are all there is"""
        from plugins.modules.purefa_workload import _facts

        mock_module = Mock()
        mock_module.params = _params(
            name="new-workload", preset="test-fleet:test-preset", host="host1"
        )
        mock_array = _mock_array()

        facts = _facts(
            mock_module,
            name=mock_module.params["name"],
            context="arrayB",
            status="creating",
        )

        assert facts["name"] == "new-workload"
        assert facts["context"] == "arrayB"
        assert facts["destroyed"] is False
        # The array generates volume names, so none can be offered up front
        assert facts["volumes"] == []
        # Nothing was read to find any of this out
        mock_array.get_volumes.assert_not_called()

    def test_change_carries_over_what_it_is_not_changing(self):
        """A prediction built on a real workload keeps that workload's values"""
        from plugins.modules.purefa_workload import _workload_facts

        mock_module = Mock()
        mock_module.params = _params()
        mock_array = _mock_array()
        workload = _mock_workload(
            preset="test-fleet:other-preset", status_details=["still working"]
        )

        facts = _workload_facts(
            mock_module, mock_array, workload, "arrayB", name="renamed"
        )

        # Only the named change applies
        assert facts["name"] == "renamed"
        # ...everything else is the workload as it stands
        assert facts["status"] == "ready"
        assert facts["context"] == "arrayB"

    def test_completed_cannot_disagree_with_a_predicted_status(self):
        """completed is derived inside _facts, not passed alongside the status"""
        from plugins.modules.purefa_workload import _facts

        mock_module = Mock()
        mock_module.params = _params()

        for status, completed in (
            ("ready", True),
            ("destroyed", True),
            ("creating", False),
            ("destroying", False),
            ("recovering", False),
        ):
            facts = _facts(
                mock_module,
                name=mock_module.params["name"],
                context="arrayB",
                status=status,
            )
            assert facts["completed"] is completed, status
        # None of those are unrecognised, so nothing was warned about
        mock_module.warn.assert_not_called()


class TestPlacementIsIgnoredWarning:
    """context and placement are the same thing, so disagreement is refused

    They mean one value to the array - a workload is created on its context, and
    there is no separate placement to send - so two different members is not a
    preference to resolve but an instruction that cannot be carried out.
    """

    def _run_main(self, mock_ansible_module, mock_get_array, fails=False, **params):
        from plugins.modules.purefa_workload import main

        mock_module = Mock()
        mock_module.params = _params(
            state="absent", preset="test-preset", volume_count=None, **params
        )
        if fails:
            mock_module.fail_json.side_effect = SystemExit
        mock_ansible_module.return_value = mock_module
        mock_array = _mock_array()
        mock_array.get_rest_version.return_value = "2.40"
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_array.get_fleets.return_value = Mock(status_code=200, items=[mock_fleet])
        mock_array.get_arrays.return_value = _mock_get_arrays()
        mock_array.get_workloads.return_value = _mock_not_found_response(404)
        mock_get_array.return_value = mock_array

        main()

        return mock_module

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_fails_when_they_disagree(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """A warning was too easy to miss, and the cost is a workload on the
        wrong array"""
        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        with pytest.raises(SystemExit):
            self._run_main(
                mock_ansible_module,
                mock_get_array,
                fails=True,
                context="arrayA",
                placement="arrayB",
            )
        mock_module = mock_ansible_module.return_value

        message = mock_module.fail_json.call_args.kwargs["msg"]
        assert "arrayA" in message and "arrayB" in message
        mock_module.warn.assert_not_called()

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_no_warning_when_only_placement_is_given(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """The documented way to use placement, which must stay quiet"""
        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = self._run_main(
            mock_ansible_module, mock_get_array, context=None, placement="arrayB"
        )

        mock_module.warn.assert_not_called()
        # Asserted on the read rather than on module.params, which main() no longer
        # writes: the placement is the member the workload is looked for on
        first_read = mock_get_array.return_value.get_workloads.call_args_list[0]
        assert first_read.kwargs["context_names"] == ["arrayB"]

    @patch("plugins.modules.purefa_workload.LooseVersion")
    @patch("plugins.modules.purefa_workload.get_array")
    @patch("plugins.modules.purefa_workload.AnsibleModule")
    @patch("plugins.modules.purefa_workload.HAS_PURESTORAGE", True)
    def test_no_warning_when_they_agree(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Redundant but not contradictory"""
        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = self._run_main(
            mock_ansible_module, mock_get_array, context="arrayB", placement="arrayB"
        )

        mock_module.warn.assert_not_called()


class TestWaitForCallsMatchTheRealHelper:
    """The module's wait_for calls must match the real helper's signature

    Every other test in this file runs against a mocked api_helpers, so a
    MagicMock accepts any keyword and a renamed or removed wait_for parameter goes
    unnoticed until a playbook hits it. This checks the calls against the real
    signature instead.
    """

    def _real_wait_for_signature(self):
        import importlib.util
        import inspect
        import sys
        import types

        # Import the real module_utils helper, stubbing only what it imports
        package = "ansible_collections.everpure.flasharray.plugins.module_utils"
        saved = {name: sys.modules.get(name) for name in list(sys.modules)}
        version = types.ModuleType(package + ".version")
        version.LooseVersion = str
        sys.modules[package + ".version"] = version
        try:
            spec = importlib.util.spec_from_file_location(
                "_real_api_helpers", "plugins/module_utils/api_helpers.py"
            )
            real = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(real)
            return inspect.signature(real.wait_for)
        finally:
            for name, was in saved.items():
                if was is not None:
                    sys.modules[name] = was

    @patch("plugins.modules.purefa_workload.check_response")
    @patch("plugins.modules.purefa_workload.wait_for")
    def test_every_wait_for_call_binds_against_the_real_signature(
        self, mock_wait_for, mock_check_response
    ):
        """A renamed or removed parameter would raise here, not on a real array"""
        from plugins.modules.purefa_workload import (
            _wait_for_absent,
            _wait_for_connections,
            _wait_for_recommendation,
            _wait_for_status,
            _wait_for_volumes,
        )

        signature = self._real_wait_for_signature()
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(context="pod1", host="host1")
        mock_array = _mock_array()
        mock_array.get_workloads.return_value = _mock_workload_response()
        mock_wait_for.return_value = None

        waiters = [
            lambda: _wait_for_status(mock_module, mock_array, "pod1", "ready"),
            lambda: _wait_for_absent(mock_module, mock_array, "pod1"),
            lambda: _wait_for_connections(
                mock_module, mock_array, "test-workload", "pod1", True
            ),
            lambda: _wait_for_recommendation(mock_module, mock_array, "pod1", "calc-1"),
            lambda: _wait_for_volumes(
                mock_module, mock_array, "pod1", WORKLOAD_VOLUMES, _mock_workload()
            ),
        ]
        for waiter in waiters:
            mock_wait_for.reset_mock()
            waiter()
            args, kwargs = mock_wait_for.call_args
            # Raises TypeError if a keyword no longer exists on the real helper
            signature.bind(*args, **kwargs)

    def test_the_recommendation_opts_out_of_skipping(self):
        """The one waiter that must poll under check mode, spelled the real way"""
        signature = self._real_wait_for_signature()

        assert "skip_in_check_mode" in signature.parameters
        # Skipping is the default, so only the recommendation says otherwise
        assert signature.parameters["skip_in_check_mode"].default is True


class TestNameAndContextAreAlwaysKnown:
    """name and context are not only array observations

    name is a required parameter and main() resolves context before any workload
    work, so both are known even when the array's reply leaves them out. The
    fallback belongs to _workload_facts, which does the reading; _facts itself
    reports whatever it is handed.
    """

    def _array(self):
        array = _mock_array()
        array.get_volumes.return_value = Mock(status_code=200, items=[])
        return array

    def test_facts_reports_what_it_is_handed(self):
        """_facts does not reach for parameters of its own accord"""
        from plugins.modules.purefa_workload import _facts

        mock_module = Mock()
        mock_module.params = _params(name="requested-name")

        facts = _facts(mock_module, context="arrayB", name=None, status="ready")

        assert facts["name"] is None

    def test_a_null_name_falls_back_to_the_requested_one(self):
        """A reply that names nothing still describes the workload we asked for"""
        module = Mock(params=_params(name="requested-name"))

        facts = _workload_facts(
            module, self._array(), _api_workload(name=None), "arrayB", []
        )

        assert facts["name"] == "requested-name"

    def test_a_null_context_falls_back_to_the_resolved_one(self):
        """main() resolves the context before any of this runs"""
        module = Mock(params=_params())

        facts = _workload_facts(
            module, self._array(), _api_workload(context=None), "resolved-array", []
        )

        assert facts["context"] == "resolved-array"

    def test_the_array_name_wins_over_the_requested_one(self):
        """A workload renamed outside Ansible reports its own name"""
        from plugins.modules.purefa_workload import _facts

        mock_module = Mock()
        mock_module.params = _params(name="requested-name")

        facts = _facts(mock_module, context="arrayB", name="array-name", status="ready")

        assert facts["name"] == "array-name"


class TestNullFieldsFromTheArray:
    """The array describes a workload with nulls, and the module must survive it

    Every field on a workload is optional in the API, and reading a null one off an
    API object raises AttributeError instead of returning None. These use
    _ApiObject rather than Mock because only it reproduces that.
    """

    def _array(self):
        array = _mock_array()
        array.get_volumes.return_value = Mock(status_code=200, items=[])
        return array

    def test_a_workload_full_of_nulls_is_described_without_raising(self):
        """The reported crash came from reading fields the array reports as null"""
        facts = _workload_facts(
            Mock(params=_params()), self._array(), _api_workload(), "arrayB", []
        )

        assert facts["status"] == "ready"
        assert facts["time_remaining"] is None

    def test_only_the_agreed_fields_are_returned(self):
        """The dict is the task's outcome, not everything the array knows

        A workload's own properties - the preset, the creation time, the array's
        free-form status text - are purefa_info's job, and were deliberately
        dropped from here. Pinned so they cannot drift back in.
        """
        facts = _workload_facts(
            Mock(params=_params()), self._array(), _api_workload(), "arrayB", []
        )

        assert set(facts) == {
            "name",
            "context",
            "status",
            "completed",
            "destroyed",
            "time_remaining",
            "volumes",
        }

    def test_null_destroyed_is_reported_as_false(self):
        facts = _workload_facts(
            Mock(params=_params()),
            self._array(),
            _api_workload(destroyed=None),
            "arrayB",
            [],
        )

        assert facts["destroyed"] is False

    def test_every_optional_field_null_does_not_crash(self):
        """The guard against the whole class, not just the field that bit us"""
        workload = _ApiObject(
            name=None,
            context=None,
            preset=None,
            status=None,
            status_details=None,
            destroyed=None,
            created=None,
            time_remaining=None,
        )

        facts = _workload_facts(
            Mock(params=_params()), self._array(), workload, "arrayB", []
        )

        # The two the module knows regardless of what the array said
        assert facts["name"] == "test-workload"
        assert facts["context"] == "arrayB"
        # The rest are array state, and null is the honest answer for them
        assert facts["status"] is None
        assert facts["time_remaining"] is None
        assert facts["completed"] is False
        assert facts["destroyed"] is False
        assert facts["volumes"] == []

    @patch("plugins.modules.purefa_workload.wait_for")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_create_with_wait_survives_the_null_the_poll_returns(
        self, mock_check_response, mock_wait_for
    ):
        """End to end for the reported failure.

        The POST reports status_details as [], the GET the wait resolves to reports
        it as null, and the facts are built from the latter.
        """
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _params(preset="test-preset", context="arrayB", wait=True)
        array = self._array()
        array.post_workloads.return_value = Mock(
            status_code=200, items=[_api_workload(status_details=[], status="creating")]
        )
        mock_wait_for.return_value = _api_workload()

        create_workload(mock_module, array, "arrayB", Mock(parameters=[]))

        mock_module.fail_json.assert_not_called()
        facts = mock_module.exit_json.call_args.kwargs["workload"]
        assert facts["status"] == "ready"
        assert facts["name"] == "test-workload"

    def test_completed_handles_a_null_name_and_status(self):
        """_workload_completed reads both, and both are optional"""
        module = Mock()

        assert _workload_completed(module, _ApiObject(name=None, status=None)) is False
        module.warn.assert_called_once()


class TestRecommendationTargetIsGuarded:
    """The walk to the chosen target crosses four optional links and three lists

    Asked of _ask_fusion_for_placement, which owns the whole round trip: build the
    payload, start the calculation, poll it, and read the array Fusion named. A gap
    anywhere along that walk is the missing recommendation it is, and nothing is
    created on the strength of it.
    """

    def _module(self):
        module = Mock()
        module.check_mode = False
        module.params = _params(
            preset="test-preset", context="arrayB", recommendation=True
        )
        module.fail_json.side_effect = SystemExit
        return module

    def _ask(self, module, array):
        from plugins.modules.purefa_workload import _ask_fusion_for_placement

        return _ask_fusion_for_placement(module, array, "arrayB", Mock(parameters=[]))

    def _recommendation(self, results):
        return _ApiObject(name="calc1", status="completed", results=results)

    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_null_results_fails_with_a_message(self, mock_check, mock_wait):
        module = self._module()
        array = _mock_array()
        array.post_workloads_placement_recommendations.return_value = Mock(
            status_code=200, items=[_ApiObject(name="calc1")]
        )
        mock_wait.return_value = self._recommendation(None)

        with pytest.raises(SystemExit):
            self._ask(module, array)

        assert "named no target" in module.fail_json.call_args.kwargs["msg"]
        array.post_workloads.assert_not_called()

    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_empty_results_fails_with_a_message(self, mock_check, mock_wait):
        module = self._module()
        array = _mock_array()
        array.post_workloads_placement_recommendations.return_value = Mock(
            status_code=200, items=[_ApiObject(name="calc1")]
        )
        mock_wait.return_value = self._recommendation([])

        with pytest.raises(SystemExit):
            self._ask(module, array)

        assert "named no target" in module.fail_json.call_args.kwargs["msg"]

    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_null_target_name_fails_with_a_message(self, mock_check, mock_wait):
        module = self._module()
        array = _mock_array()
        array.post_workloads_placement_recommendations.return_value = Mock(
            status_code=200, items=[_ApiObject(name="calc1")]
        )
        mock_wait.return_value = self._recommendation(
            [_ApiObject(placements=[_ApiObject(targets=[_ApiObject(name=None)])])]
        )

        with pytest.raises(SystemExit):
            self._ask(module, array)

        assert "named no target" in module.fail_json.call_args.kwargs["msg"]


class TestReadingAWorkloadThatIsNotThere:
    """Absence is read from the status code, and only from two of them

    A read by name reports a missing workload as an error rather than as an empty
    result, so there is no item count to test. The risk that shapes this is a
    server error being taken for absence: a caller waiting for a workload to go
    away would then report success while the array was never asked.
    """

    def _read(self, status_code):
        from plugins.modules.purefa_workload import _read_workload

        module = Mock(params=_params())
        module.fail_json.side_effect = SystemExit
        array = _mock_array()
        array.get_workloads.return_value = Mock(
            status_code=status_code,
            items=[_mock_workload()] if status_code == 200 else [],
            errors=[Mock(message="Workload does not exist.")],
        )
        return module, _read_workload(module, array, "arrayB")

    def test_a_workload_that_exists_is_returned(self):
        module, workload = self._read(200)

        assert workload is not None
        module.fail_json.assert_not_called()

    @pytest.mark.parametrize("status_code", [400, 404])
    def test_absence_is_reported_as_none(self, status_code):
        """400 is what this array returns; 404 is covered so the test does not
        re-encode a guess about which one it picks"""
        module, workload = self._read(status_code)

        assert workload is None
        module.fail_json.assert_not_called()

    @pytest.mark.parametrize("status_code", [401, 403, 500, 502, 503])
    def test_anything_else_is_surfaced_rather_than_read_as_absence(self, status_code):
        """The regression guard: a server error must never read as absence.

        check_response is what turns a response into a module failure, so the
        assertion is that the read hands it over rather than swallowing it - the
        helper itself is stubbed here, as it is for the rest of this file.
        """
        from plugins.modules.purefa_workload import _read_workload

        module = Mock(params=_params())
        array = _mock_array()
        response = Mock(status_code=status_code, items=[], errors=[])
        array.get_workloads.return_value = response

        with patch("plugins.modules.purefa_workload.check_response") as surfaced:
            _read_workload(module, array, "arrayB")

        # The absence path returns without calling check_response, so this having
        # been called is exactly what distinguishes "surfaced" from "read as absent"
        surfaced.assert_called_once()
        assert surfaced.call_args.args[0] is response

    @patch("plugins.modules.purefa_workload.wait_for")
    def test_waiting_for_absence_finishes_when_the_read_stops_finding_it(
        self, mock_wait_for
    ):
        """The eradicate path: the poll ends when the workload is gone, and a
        gone workload is exactly the error case above"""
        from plugins.modules.purefa_workload import _wait_for_absent

        module = Mock(params=_params())
        module.check_mode = False
        array = _mock_array()
        _wait_for_absent(module, array, "arrayB")
        is_done = mock_wait_for.call_args.kwargs["is_done"]

        assert is_done(None) is True
        assert is_done(_mock_workload()) is False

    def test_the_read_asks_the_array_with_allow_errors(self):
        """Without it the array rejects the read outright on a remote context"""
        from plugins.modules.purefa_workload import _read_workload

        module = Mock(params=_params())
        array = _mock_array()
        array.get_workloads.return_value = Mock(
            status_code=200, items=[_mock_workload()], errors=[]
        )

        _read_workload(module, array, "MUCFA22")

        array.get_workloads.assert_called_once_with(
            names=["test-workload"], context_names=["MUCFA22"], allow_errors=True
        )


class TestResolvingWhichMemberToSearch:
    """Step 2 of the pipeline: where to look, and nothing about what to do

    Naming neither context nor placement means the fleet rather than being refused:
    everything except a create acts on a workload that already exists, so the member
    holding it can be looked up. state is deliberately not read here, so no refusal
    in this step has to guess what the task will go on to do.
    """

    FLEET = "test-fleet"

    def _resolve(self, **params):
        from plugins.modules.purefa_workload import _resolve_member_to_search

        module = Mock(params=_params(**params))
        module.fail_json.side_effect = SystemExit
        array = _mock_array()
        member = _resolve_member_to_search(module, array, self.FLEET)
        return member, module, array

    def _refuse(self, **params):
        """The message a refused input produced, having checked that it refused"""
        from plugins.modules.purefa_workload import _resolve_member_to_search

        module = Mock(params=_params(**params))
        module.fail_json.side_effect = SystemExit
        with pytest.raises(SystemExit):
            _resolve_member_to_search(module, _mock_array(), self.FLEET)
        return module.fail_json.call_args.kwargs["msg"]

    def test_a_named_member_is_the_member_searched(self):
        member, module, _unused = self._resolve(context="arrayB")

        assert member == "arrayB"
        module.fail_json.assert_not_called()

    def test_placement_alone_names_the_member_too(self):
        """The two options are the same thing to the array"""
        member, _unused, _unused = self._resolve(context=None, placement="arrayA")

        assert member == "arrayA"

    def test_both_naming_the_same_member_is_accepted(self):
        member, module, _unused = self._resolve(context="arrayB", placement="arrayB")

        assert member == "arrayB"
        module.fail_json.assert_not_called()

    def test_disagreeing_context_and_placement_are_refused(self):
        message = self._refuse(context="arrayA", placement="arrayB")

        assert "arrayA" in message and "arrayB" in message

    def test_naming_nothing_means_the_whole_fleet(self):
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        member, module, _unused = self._resolve(context=None, placement=None)

        assert member is SEARCH_WHOLE_FLEET
        module.fail_json.assert_not_called()

    def test_naming_nothing_reads_nothing(self):
        """The one path with no name to check, so the fleet need not be listed"""
        _unused, _unused, array = self._resolve(context=None, placement=None)

        array.get_fleets_members.assert_not_called()
        array.get_workloads.assert_not_called()

    def test_an_explicitly_empty_context_is_refused(self):
        """An omitted context means the fleet, so a computed one that came out
        empty must not quietly mean the same thing - that is how a fleet-wide
        destroy happens by accident. Only reachable because the argument spec no
        longer defaults context to ''."""
        message = self._refuse(context="")

        assert "empty string" in message
        # Says what to write instead, both ways
        assert "Omit it" in message and "member" in message

    def test_an_empty_context_is_refused_even_alongside_a_placement(self):
        with pytest.raises(SystemExit):
            self._resolve(context="", placement="arrayA")

    def test_a_non_member_is_refused_and_the_members_are_listed(self):
        message = self._refuse(context="not-in-the-fleet")

        assert "not-in-the-fleet" in message
        # The point of the listing: the user can see what they could have written
        for member in FLEET_MEMBERS:
            assert member in message
        # ...including the fleet itself
        assert self.FLEET in message

    def test_a_non_member_placement_is_refused_by_its_own_name(self):
        message = self._refuse(context=None, placement="not-in-the-fleet")

        assert message.startswith("placement")

    def test_the_fleet_itself_means_the_whole_fleet(self):
        """The bare fleet name is never returned as a member: the array rejects it
        as a query context with a 400 that reads exactly like absence"""
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        member, module, _unused = self._resolve(context=self.FLEET)

        assert member is SEARCH_WHOLE_FLEET
        module.fail_json.assert_not_called()

    def test_a_recommendation_widens_the_search_past_the_named_member(self):
        """Fusion may have placed the workload anywhere, so a re-run has to look
        everywhere. Looking only where the operator pointed would find nothing, ask
        for a second placement, and create a second workload."""
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        member, module, _unused = self._resolve(context="arrayA", recommendation=True)

        assert member is SEARCH_WHOLE_FLEET
        # Still checked against the fleet, since a name was given
        module.fail_json.assert_not_called()

    def test_a_recommendation_with_a_non_member_is_still_refused(self):
        """Widening the search does not excuse a name that means nothing"""
        with pytest.raises(SystemExit):
            self._resolve(context="not-in-the-fleet", recommendation=True)

    def test_a_recommendation_on_a_rename_keeps_the_named_member(self):
        """There is nothing for Fusion to choose: a rename works on the workload
        that is already there"""
        member, _unused, _unused = self._resolve(
            context="arrayA", recommendation=True, rename="new-workload"
        )

        assert member == "arrayA"

    @pytest.mark.parametrize("state", ["absent", "expand"])
    def test_a_recommendation_on_another_state_keeps_the_named_member(self, state):
        member, _unused, _unused = self._resolve(
            context="arrayA", recommendation=True, state=state
        )

        assert member == "arrayA"

    @pytest.mark.parametrize("state", ["present", "absent", "expand"])
    def test_the_state_does_not_change_where_the_search_goes(self, state):
        """The property the whole restructure rests on: this step never reads
        state, so it cannot refuse a task on a guess about what it will do"""
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        assert self._resolve(context="arrayB", state=state)[0] == "arrayB"
        assert self._resolve(context=self.FLEET, state=state)[0] is SEARCH_WHOLE_FLEET
        assert (
            self._resolve(context=None, placement=None, state=state)[0]
            is SEARCH_WHOLE_FLEET
        )

    @pytest.mark.parametrize(
        "params,expected",
        [
            ({"context": "arrayB", "placement": None}, "arrayB"),
            ({"context": None, "placement": "arrayA"}, "arrayA"),
            ({"context": "arrayB", "placement": "arrayB"}, "arrayB"),
            ({"context": None, "placement": None}, ""),
            ({"context": "", "placement": None}, ""),
        ],
    )
    def test_the_requested_member_reads_either_option(self, params, expected):
        from plugins.modules.purefa_workload import _requested_member

        assert _requested_member(_params(**params)) == expected

    @pytest.mark.parametrize(
        "params,expected",
        [
            ({"recommendation": True}, True),
            ({"recommendation": False}, False),
            # recommendation only ever decides where a new workload goes
            ({"recommendation": True, "rename": "new-workload"}, False),
            ({"recommendation": True, "state": "absent"}, False),
            ({"recommendation": True, "state": "expand"}, False),
        ],
    )
    def test_whether_fusion_is_choosing_the_placement(self, params, expected):
        from plugins.modules.purefa_workload import _fusion_will_choose_placement

        assert _fusion_will_choose_placement(_params(**params)) is expected


class TestFindingAWorkloadAcrossTheFleet:
    """One call spans the fleet, with a per-member sweep behind it

    "<fleet>.arrays" is a context covering every member. It is not in the SDK's
    documentation, so the sweep stays as a fallback - and not only for older
    releases: a rejection of the fleet-wide query looks exactly like the workload
    being absent, and reading that as "not there" would let a create duplicate.
    """

    FLEET = "test-fleet"

    def _array(self, homes, fleet_wide=True, errors=(), unattributed=0):
        """homes lists the members reporting the workload.

        fleet_wide=False makes the <fleet>.arrays context fail, so the fallback
        runs - which is how an array that does not support it would behave.

        errors and unattributed make the fleet-wide call answer 200 with a partial
        result: errors is what allow_errors puts there for a member it could not
        reach, and unattributed adds that many items whose context came back null,
        which the SDK permits for every field.
        """
        array = _mock_array()

        def get_workloads(names=None, context_names=None, **kwargs):
            asked = (context_names or [None])[0]
            if asked == f"{self.FLEET}.arrays":
                if not fleet_wide or not (homes or errors or unattributed):
                    return _mock_not_found_response()
                return Mock(
                    status_code=200,
                    items=[_mock_workload(context=member) for member in homes]
                    + [_mock_workload(context=None) for _unused in range(unattributed)],
                    errors=[Mock(message=message) for message in errors],
                )
            if asked in homes:
                return _mock_workload_response(context=asked)
            return _mock_not_found_response()

        array.get_workloads.side_effect = get_workloads
        return array

    def _find(self, array):
        from plugins.modules.purefa_workload import _find_across_fleet

        return _find_across_fleet(Mock(params=_params()), array, self.FLEET)

    def test_finds_it_on_the_one_member_that_has_it(self):
        assert list(self._find(self._array(["arrayB"]))) == ["arrayB"]

    def test_finds_both_when_the_name_is_used_twice(self):
        """Names are unique per member, not across the fleet, so one query can
        legitimately answer with two workloads"""
        found = self._find(self._array(["arrayA", "arrayB"]))

        assert sorted(found) == ["arrayA", "arrayB"]

    def test_one_call_answers_it(self):
        array = self._array(["arrayA", "arrayB"])
        self._find(array)

        array.get_workloads.assert_called_once_with(
            names=["test-workload"],
            context_names=[f"{self.FLEET}.arrays"],
            allow_errors=True,
        )

    def test_finds_nothing_when_no_member_has_it(self):
        assert self._find(self._array([])) == {}

    def test_falls_back_to_asking_each_member(self):
        """An array that rejects the fleet-wide context must still be searched,
        rather than the rejection passing for an empty fleet"""
        array = self._array(["arrayB"], fleet_wide=False)

        found = self._find(array)

        assert list(found) == ["arrayB"]
        asked = {
            call.kwargs["context_names"][0]
            for call in array.get_workloads.call_args_list
        }
        assert set(FLEET_MEMBERS) <= asked

    def test_the_sweep_asks_only_about_this_fleet(self):
        """Which arrays are searched decides which are candidates for a delete or
        an eradication, so it is not left to whatever the array happens to list"""
        array = self._array(["arrayB"], fleet_wide=False)

        self._find(array)

        array.get_fleets_members.assert_called_once_with(fleet_names=[self.FLEET])

    def test_a_partial_answer_is_swept_rather_than_trusted(self):
        """allow_errors turns a member that could not be reached into a 200 with an
        errors list. Trusting it would report a workload as absent because the
        member holding it errored - and absent drives a create, or a delete
        reporting success having touched nothing."""
        array = self._array(["arrayA"], errors=["Executor not found for arrayB"])

        found = self._find(array)

        # arrayB was never in the fleet-wide answer, and the sweep is what finds it
        asked = {
            call.kwargs["context_names"][0]
            for call in array.get_workloads.call_args_list
        }
        assert set(FLEET_MEMBERS) <= asked
        assert list(found) == ["arrayA"]

    def test_an_item_with_no_context_is_swept_rather_than_dropped(self):
        """Every SDK field is optional, so an item can arrive with nothing to
        attribute it to. It cannot be counted, and it cannot be discarded either -
        something of this name is out there."""
        array = self._array(["arrayA"], unattributed=1)

        self._find(array)

        asked = {
            call.kwargs["context_names"][0]
            for call in array.get_workloads.call_args_list
        }
        assert set(FLEET_MEMBERS) <= asked

    def test_an_answer_carrying_only_an_unattributed_item_still_sweeps(self):
        """The dangerous shape: one item, no context, so the fleet-wide answer
        looks empty once it is dropped"""
        array = self._array([], unattributed=1)

        found = self._find(self._array_that_finds_it_on_a_sweep(array))

        assert list(found) == ["arrayB"]

    def _array_that_finds_it_on_a_sweep(self, array):
        """The same array, but with arrayB answering a member-scoped read

        The fleet-wide call still returns its unusable answer; only the per-member
        reads behind it can see the workload.
        """
        fleet_wide = array.get_workloads.side_effect

        def get_workloads(names=None, context_names=None, **kwargs):
            asked = (context_names or [None])[0]
            if asked == "arrayB":
                return _mock_workload_response(context="arrayB")
            return fleet_wide(names=names, context_names=context_names, **kwargs)

        array.get_workloads.side_effect = get_workloads
        return array

    def test_a_complete_answer_is_trusted_and_costs_one_call(self):
        """The check must not make every fleet-wide read pay for a sweep"""
        array = self._array(["arrayA", "arrayB"], errors=[])

        found = self._find(array)

        assert sorted(found) == ["arrayA", "arrayB"]
        array.get_workloads.assert_called_once()
        array.get_fleets_members.assert_not_called()


class TestLookingUpTheWorkload:
    """Step 3 of the pipeline: what is there, reported and never judged

    Absence is a result, and so are two matches. Neither is refused here - what they
    mean depends on the state, which this step does not read - and which array the
    workload is on comes from the array's own answer rather than from what was asked
    for.
    """

    FLEET = "test-fleet"

    def _array(self, homes, fleet_wide=True):
        array = _mock_array()

        def get_workloads(names=None, context_names=None, **kwargs):
            asked = (context_names or [None])[0]
            if asked == f"{self.FLEET}.arrays":
                if not fleet_wide or not homes:
                    return _mock_not_found_response()
                return Mock(
                    status_code=200,
                    items=[_mock_workload(context=member) for member in homes],
                    errors=[],
                )
            if asked in homes:
                return _mock_workload_response(**{"context": asked, **homes[asked]})
            return _mock_not_found_response()

        array.get_workloads.side_effect = get_workloads
        return array

    def _look_up(self, member, homes=None, **params):
        from plugins.modules.purefa_workload import _look_up_workload

        module = Mock(params=_params(**params))
        module.fail_json.side_effect = SystemExit
        array = self._array({} if homes is None else homes)
        return _look_up_workload(module, array, self.FLEET, member), array

    # --- a member-scoped lookup ------------------------------------------------

    def test_a_workload_on_the_member_asked_is_live(self):
        lookup, _unused = self._look_up("arrayB", {"arrayB": {}})

        assert lookup.presence == "live"
        assert lookup.member == "arrayB"
        assert lookup.workload is not None
        assert lookup.members == ["arrayB"]

    def test_a_destroyed_workload_is_distinguished_from_a_live_one(self):
        lookup, _unused = self._look_up("arrayB", {"arrayB": {"destroyed": True}})

        assert lookup.presence == "destroyed"
        assert lookup.member == "arrayB"

    def test_a_workload_that_is_not_there_is_absent_not_a_failure(self):
        lookup, _unused = self._look_up("arrayB")

        assert lookup.presence == "absent"
        assert lookup.member is None
        assert lookup.workload is None
        assert lookup.matches == {}

    def test_a_member_scoped_lookup_does_not_sweep(self):
        lookup, array = self._look_up("arrayB", {"arrayB": {}})

        assert lookup.swept is False
        array.get_fleets_members.assert_not_called()
        array.get_workloads.assert_called_once_with(
            names=["test-workload"], context_names=["arrayB"], allow_errors=True
        )

    def test_the_array_own_answer_says_which_member_holds_it(self):
        """Not what we asked for. The two disagree when a context resolves to
        something else on the array, and only one of them is the truth."""
        lookup, _unused = self._look_up("arrayB", {"arrayB": {"context": "arrayA"}})

        assert lookup.member == "arrayA"

    def test_the_member_asked_stands_in_when_the_answer_names_none(self):
        """Every SDK field is optional, so a workload can come back with no context
        at all - as _workload_facts already allows for"""
        lookup, _unused = self._look_up("arrayB", {"arrayB": {"context": None}})

        assert lookup.member == "arrayB"

    # --- a fleet-wide lookup ---------------------------------------------------

    def test_the_fleet_is_searched_when_no_member_was_settled(self):
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        lookup, array = self._look_up(SEARCH_WHOLE_FLEET, {"arrayB": {}})

        assert lookup.member == "arrayB"
        assert lookup.presence == "live"
        assert lookup.swept is True
        asked = [
            call.kwargs["context_names"][0]
            for call in array.get_workloads.call_args_list
        ]
        assert asked == [f"{self.FLEET}.arrays"]

    def test_the_bare_fleet_name_is_never_used_as_a_query_context(self):
        """The array rejects it with a 400 that reads exactly like absence"""
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        _unused, array = self._look_up(SEARCH_WHOLE_FLEET, {"arrayB": {}})

        asked = [
            call.kwargs.get("context_names", [None])[0]
            for call in array.get_workloads.call_args_list
        ]
        assert self.FLEET not in asked

    def test_nothing_anywhere_in_the_fleet_is_absent(self):
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        lookup, _unused = self._look_up(SEARCH_WHOLE_FLEET)

        assert lookup.presence == "absent"
        assert lookup.swept is True

    def test_two_members_holding_the_name_is_an_answer_not_a_refusal(self):
        """The lookup reports both and leaves the refusal to _decide_action, which
        is the only place that knows what the task was trying to do"""
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        lookup, _unused = self._look_up(
            SEARCH_WHOLE_FLEET, {"arrayA": {}, "arrayB": {}}
        )

        assert lookup.presence == "ambiguous"
        assert lookup.members == ["arrayA", "arrayB"]

    def test_several_matches_can_never_be_read_as_none(self):
        """The reason presence has a fourth value rather than the table being
        fronted by a length check: read as absent under state: present, two
        matches would be a create"""
        from plugins.modules.purefa_workload import WorkloadLookup

        lookup = WorkloadLookup(
            matches={"arrayA": _mock_workload(), "arrayB": _mock_workload()},
            swept=True,
        )

        assert lookup.presence != "absent"
        # And nothing derived from it offers a single answer either
        assert lookup.member is None
        assert lookup.workload is None

    def test_a_destroyed_copy_still_counts_as_a_match(self):
        """Decided knowingly: a leftover destroyed copy blocks an otherwise obvious
        delete until it is eradicated or a context is named"""
        from plugins.modules.purefa_workload import SEARCH_WHOLE_FLEET

        lookup, _unused = self._look_up(
            SEARCH_WHOLE_FLEET, {"arrayA": {}, "arrayB": {"destroyed": True}}
        )

        assert lookup.presence == "ambiguous"

    def test_a_workload_that_does_not_say_whether_it_is_destroyed_reads_as_live(self):
        """destroyed is optional on the SDK model and raises rather than returning
        None, so it is read with a default"""
        from plugins.modules.purefa_workload import WorkloadLookup

        lookup = WorkloadLookup(
            matches={"arrayB": _api_workload(destroyed=None)}, swept=False
        )

        assert lookup.presence == "live"

    def test_the_record_cannot_be_edited_after_the_fact(self):
        """Frozen because its useful values are derived from matches: a field
        written afterwards could disagree with what was read"""
        from plugins.modules.purefa_workload import WorkloadLookup

        lookup = WorkloadLookup(matches={}, swept=False)

        with pytest.raises(Exception):
            lookup.swept = True


class TestDecidingWhatToDo:
    """Step 4: the whole decision, in one pure function

    Every row of the three state tables appears here once. _decide_action takes a
    plain params dict, a member name, a lookup and a fleet name - no module, no
    array, no I/O - so the table is tested by calling it, with nothing mocked. That
    is the point of the signature: today's decision is spread over ten elif arms
    reading a mutated module.params, and cannot be tested without an array.

    It is also the only step that reads state. Nothing here has to guess what the
    task will do, because by the time it runs, it is known.
    """

    FLEET = "test-fleet"

    def _lookup(self, presence, member="arrayB"):
        """A lookup in the given presence, built from workloads as the array sends
        them - nulls and all, and no Mock in sight"""
        from plugins.modules.purefa_workload import WorkloadLookup

        if presence == "absent":
            return WorkloadLookup(matches={}, swept=False)
        if presence == "ambiguous":
            return WorkloadLookup(
                matches={
                    "arrayA": _api_workload(context=_ApiObject(name="arrayA")),
                    "arrayB": _api_workload(context=_ApiObject(name="arrayB")),
                },
                swept=True,
            )
        return WorkloadLookup(
            matches={
                member: _api_workload(
                    context=_ApiObject(name=member), destroyed=presence == "destroyed"
                )
            },
            swept=False,
        )

    def _decide(self, presence, member="arrayB", holder="arrayB", **params):
        from plugins.modules.purefa_workload import _decide_action

        return _decide_action(
            _params(**params), member, self._lookup(presence, holder), self.FLEET
        )

    # --- state: present --------------------------------------------------------

    @pytest.mark.parametrize(
        "presence,member,params,expected",
        [
            # A name on two members is two workloads, whatever the task asked for
            ("ambiguous", SEARCH_WHOLE_FLEET, {}, "fail"),
            ("ambiguous", "arrayB", {"rename": "new-workload"}, "fail"),
            ("ambiguous", SEARCH_WHOLE_FLEET, {"recommendation": True}, "fail"),
            ("ambiguous", SEARCH_WHOLE_FLEET, {"host": "host1"}, "fail"),
            # Nothing there
            ("absent", "arrayB", {"rename": "new-workload"}, "fail"),
            ("absent", "arrayB", {}, "create"),
            ("absent", "arrayB", {"host": "host1"}, "create"),
            ("absent", SEARCH_WHOLE_FLEET, {}, "fail"),
            ("absent", SEARCH_WHOLE_FLEET, {"recommendation": True}, "create"),
            # Fusion is placing, so the member was widened away deliberately
            (
                "absent",
                SEARCH_WHOLE_FLEET,
                {"recommendation": True, "host": "h"},
                "create",
            ),
            # There and usable
            ("live", "arrayB", {"rename": "new-workload"}, "rename"),
            ("live", "arrayB", {"host": "host1"}, "connect"),
            ("live", "arrayB", {}, "nothing"),
            ("live", "arrayB", {"recommendation": True}, "nothing"),
            # There and destroyed
            ("destroyed", "arrayB", {"rename": "new-workload"}, "fail"),
            ("destroyed", "arrayB", {"host": "host1"}, "recover"),
            ("destroyed", "arrayB", {}, "recover"),
        ],
    )
    def test_state_present(self, presence, member, params, expected):
        assert self._decide(presence, member, state="present", **params).action == (
            expected
        )

    def test_a_destroyed_workload_is_recovered_whether_or_not_a_host_is_named(self):
        """host is the mode selector everywhere else in this module, and here it is
        not: recovery happens either way, and the host is connected afterwards.
        Refusing when it is set would let the option decide whether recovery is
        allowed, which is not what it means anywhere."""
        assert self._decide("destroyed").action == "recover"
        assert self._decide("destroyed", host="host1").action == "recover"

    def test_an_existing_live_workload_is_left_alone(self):
        """The idempotent success path, which the old chain reached only by falling
        off the end of its elif chain into a bare else"""
        decision = self._decide("live")

        assert decision == ("nothing", None)

    # --- state: absent ---------------------------------------------------------

    @pytest.mark.parametrize(
        "presence,params,expected",
        [
            ("ambiguous", {}, "fail"),
            ("ambiguous", {"eradicate": True}, "fail"),
            ("ambiguous", {"host": "host1"}, "fail"),
            # Not there: already the requested end state
            ("absent", {}, "nothing"),
            ("absent", {"eradicate": True}, "nothing"),
            ("absent", {"host": "host1"}, "nothing"),
            # There and live
            ("live", {"host": "host1"}, "disconnect"),
            ("live", {"host": "host1", "eradicate": True}, "disconnect"),
            ("live", {}, "delete"),
            ("live", {"eradicate": True}, "delete"),
            # There and already destroyed
            ("destroyed", {"host": "host1"}, "nothing"),
            ("destroyed", {"host": "host1", "eradicate": True}, "nothing"),
            ("destroyed", {"eradicate": True}, "eradicate"),
            ("destroyed", {}, "nothing"),
        ],
    )
    def test_state_absent(self, presence, params, expected):
        assert self._decide(presence, state="absent", **params).action == expected

    def test_eradicate_is_never_silently_ignored_on_a_live_disconnect(self):
        """Naming a host makes the task a disconnect, so eradicate does not apply.
        Today that is silent."""
        decision = self._decide("live", state="absent", host="host1", eradicate=True)

        assert decision.action == "disconnect"
        assert "eradicate is ignored" in decision.message

    def test_a_destroyed_workload_with_a_host_is_not_eradicated(self):
        """The trap this closes: adding eradicate: true to a disconnect task
        eradicates the workload today, ignoring the host entirely"""
        decision = self._decide(
            "destroyed", state="absent", host="host1", eradicate=True
        )

        assert decision.action == "nothing"
        assert "eradicate is not applied" in decision.message

    def test_a_destroyed_workload_with_a_host_says_why_nothing_happened(self):
        """The volumes went with the workload, so the host is already disconnected.
        Failing would break idempotency - but it must not be silent either."""
        decision = self._decide("destroyed", state="absent", host="host1")

        assert decision.action == "nothing"
        assert "already disconnected" in decision.message
        # Only mentioned when it was actually set
        assert "eradicate" not in decision.message

    def test_a_destroyed_workload_pending_eradication_is_reported_not_refused(self):
        """It is absent in the sense state: absent asks for, and the facts carry
        time_remaining"""
        assert self._decide("destroyed", state="absent") == ("nothing", None)

    # --- state: expand ---------------------------------------------------------

    @pytest.mark.parametrize(
        "presence,expected",
        [
            ("ambiguous", "fail"),
            ("absent", "fail"),
            ("live", "expand"),
            # Reports changed: false, ok today, having added nothing
            ("destroyed", "fail"),
        ],
    )
    def test_state_expand(self, presence, expected):
        assert self._decide(presence, state="expand").action == expected

    def test_expanding_a_destroyed_workload_is_refused_rather_than_reported_ok(self):
        """A silent success where the operator's storage did not grow"""
        decision = self._decide("destroyed", state="expand")

        assert decision.action == "fail"
        assert "destroyed" in decision.message
        assert "nothing to add volumes to" in decision.message

    # --- the messages ----------------------------------------------------------

    @pytest.mark.parametrize("state", ["present", "absent", "expand"])
    def test_ambiguity_names_every_member_holding_the_name(self, state):
        decision = self._decide("ambiguous", SEARCH_WHOLE_FLEET, state=state)

        assert decision.action == "fail"
        assert "arrayA" in decision.message and "arrayB" in decision.message
        # And says what to do about it
        assert "context" in decision.message

    def test_a_create_with_no_member_quotes_the_one_refusal_left(self):
        from plugins.modules.purefa_workload import _CREATE_NEEDS_A_MEMBER

        decision = self._decide("absent", SEARCH_WHOLE_FLEET)

        assert decision.action == "fail"
        assert decision.message == _CREATE_NEEDS_A_MEMBER.format(
            name="test-workload", fleet=self.FLEET
        )
        # What cannot be done, then every way to say where
        assert "context or placement" in decision.message
        assert "recommendation" in decision.message

    def test_the_create_refusal_cannot_fire_when_there_is_something_to_act_on(self):
        """It means exactly "you asked me to invent a placement", so it is reachable
        only from absent - which is what makes defaulting to the fleet safe for
        everything else"""
        for presence in ("live", "destroyed"):
            decision = self._decide(presence, SEARCH_WHOLE_FLEET)

            assert decision.action != "fail"

    # --- naming nothing, which used to be refused up front ---------------------

    @pytest.mark.parametrize(
        "state,presence,params",
        [
            ("absent", "live", {}),
            ("absent", "live", {"host": "host1"}),
            ("absent", "destroyed", {"eradicate": True}),
            ("present", "destroyed", {}),
            ("present", "live", {"host": "host1"}),
            ("present", "live", {"rename": "new-workload"}),
            ("expand", "live", {}),
        ],
    )
    def test_naming_nothing_is_refused_only_where_there_is_nothing_to_find(
        self, state, presence, params
    ):
        """The reported bug, inverted. This was refused before any lookup, which is
        why 6 of the module's own 11 EXAMPLES failed as written: every one of these
        acts on a workload that already exists, so the member holding it is an answer
        to look up rather than a thing to be told."""
        decision = self._decide(presence, SEARCH_WHOLE_FLEET, state=state, **params)

        assert decision.action != "fail"

    def test_a_recommendation_does_not_turn_a_removal_into_a_create(self):
        """recommendation only ever decides where a new workload goes. It used to be
        refused outright on a removal for standing in for a context; now the fleet
        default covers the removal and recommendation simply does not apply."""
        decision = self._decide(
            "absent", SEARCH_WHOLE_FLEET, state="absent", recommendation=True
        )

        assert decision.action == "nothing"

    def test_a_recommendation_cannot_stand_in_for_the_member_a_rename_needs(self):
        """A rename works on the workload that is already there, so there is nothing
        for Fusion to choose. The refusal is now the honest one - the workload is not
        in the fleet - rather than "does not exist on ", which is what today's
        disagreement between the two placement checks produces."""
        from plugins.modules.purefa_workload import _CREATE_NEEDS_A_MEMBER

        decision = self._decide(
            "absent",
            SEARCH_WHOLE_FLEET,
            state="present",
            recommendation=True,
            rename="new-workload",
        )

        assert decision.action == "fail"
        assert "nothing to rename to new-workload" in decision.message
        assert f"anywhere in fleet {self.FLEET}" in decision.message
        assert decision.message != _CREATE_NEEDS_A_MEMBER.format(
            name="test-workload", fleet=self.FLEET
        )

    @pytest.mark.parametrize(
        "state,params",
        [
            ("present", {"rename": "new-workload"}),
            ("expand", {}),
        ],
    )
    def test_a_message_about_a_fleet_wide_search_names_the_fleet_not_a_member(
        self, state, params
    ):
        """It must not report a context the operator never wrote, nor an empty one -
        which is what "does not exist on , so there is nothing to rename" does
        today"""
        decision = self._decide("absent", SEARCH_WHOLE_FLEET, state=state, **params)

        assert f"anywhere in fleet {self.FLEET}" in decision.message

    @pytest.mark.parametrize(
        "state,params",
        [
            ("present", {"rename": "new-workload"}),
            ("expand", {}),
        ],
    )
    def test_a_message_about_a_member_scoped_search_names_the_member(
        self, state, params
    ):
        decision = self._decide("absent", "pod1", state=state, **params)

        assert "on pod1" in decision.message

    def test_a_message_names_the_member_the_workload_was_actually_found_on(self):
        """Not the one asked for. A fleet-wide search names no member, and the
        answer is where the message has to come from."""
        decision = self._decide(
            "destroyed",
            SEARCH_WHOLE_FLEET,
            holder="MUCFA22",
            state="expand",
        )

        assert "on MUCFA22" in decision.message

    # --- the contract main() dispatches on -------------------------------------

    def test_every_decision_is_one_of_the_declared_actions(self):
        """main() has one arm per action and fails loudly on anything else, so an
        action invented here without a handler must be impossible"""
        from plugins.modules.purefa_workload import ACTIONS

        for state in ("present", "absent", "expand"):
            for presence in ("absent", "live", "destroyed", "ambiguous"):
                for member in (SEARCH_WHOLE_FLEET, "arrayB"):
                    for extra in (
                        {},
                        {"host": "host1"},
                        {"rename": "new-workload"},
                        {"eradicate": True},
                        {"recommendation": True},
                    ):
                        decision = self._decide(presence, member, state=state, **extra)

                        assert decision.action in ACTIONS

    def test_a_refusal_always_explains_itself(self):
        """fail is raised by main() as the task's message, so an empty one would be
        a task failing with nothing to read"""
        for state in ("present", "absent", "expand"):
            for presence in ("absent", "live", "destroyed", "ambiguous"):
                for extra in ({}, {"rename": "new-workload"}, {"eradicate": True}):
                    decision = self._decide(
                        presence, SEARCH_WHOLE_FLEET, state=state, **extra
                    )

                    if decision.action == "fail":
                        assert decision.message

    def test_deciding_reads_nothing_and_writes_nothing(self):
        """The params dict is an input, not a working register: today's chain reads
        a module.params["context"] that four other places have written"""
        from plugins.modules.purefa_workload import _decide_action

        params = _params(state="absent", eradicate=True)
        before = dict(params)

        _decide_action(params, "arrayB", self._lookup("destroyed"), self.FLEET)

        assert params == before


class TestCopiesElsewhereAreCounted:
    """The same name on two members is two workloads, which is worth knowing

    _copies_elsewhere answers the question and the callers decide how to say it -
    the removal warning in one wording, a create in its own.
    """

    FLEET = "test-fleet"

    def _array(self, homes):
        array = _mock_array()

        def get_workloads(names=None, context_names=None, **kwargs):
            asked = (context_names or [None])[0]
            if asked == f"{self.FLEET}.arrays":
                if not homes:
                    return _mock_not_found_response()
                return Mock(
                    status_code=200,
                    items=[_mock_workload(context=member) for member in homes],
                    errors=[],
                )
            if asked in homes:
                return _mock_workload_response(context=asked)
            return _mock_not_found_response()

        array.get_workloads.side_effect = get_workloads
        return array

    def _copies(self, homes, lookup, **params):
        from plugins.modules.purefa_workload import _copies_elsewhere

        module = Mock(params=_params(**params))
        array = self._array(homes)
        return _copies_elsewhere(module, array, self.FLEET, lookup), array

    def _lookup(self, matches, swept):
        from plugins.modules.purefa_workload import WorkloadLookup

        return WorkloadLookup(
            matches={member: _mock_workload(context=member) for member in matches},
            swept=swept,
        )

    def test_the_other_members_holding_the_name_are_listed(self):
        copies, _unused = self._copies(
            ["arrayA", "arrayB", "pod1"], self._lookup(["arrayB"], swept=False)
        )

        assert copies == ["arrayA", "pod1"]

    def test_the_member_being_acted_on_is_not_one_of_them(self):
        copies, _unused = self._copies(
            ["arrayB"], self._lookup(["arrayB"], swept=False)
        )

        assert copies == []

    def test_the_member_asked_stands_in_when_nothing_was_found_there(self):
        """A delete against arrayB where the workload only exists on arrayA: the
        one being acted on is still arrayB, so arrayA is the copy elsewhere"""
        copies, _unused = self._copies(
            ["arrayA"], self._lookup([], swept=False), context="arrayB"
        )

        assert copies == ["arrayA"]

    def test_a_sweep_already_done_is_not_repeated(self):
        """A fleet-wide lookup has already read every member, so the answer is the
        lookup itself - the module sweeps once per run rather than up to three
        times. The array is stubbed to claim two members here precisely to show
        that it is not asked again."""
        copies, array = self._copies(
            ["arrayA", "arrayB"], self._lookup(["arrayB"], swept=True)
        )

        array.get_workloads.assert_not_called()
        array.get_fleets_members.assert_not_called()
        assert copies == []

    def test_a_fleet_wide_lookup_with_one_match_reports_no_copies(self):
        """It cannot report any: a sweep that found the name on two members is
        ambiguous and already refused, so a lookup that got this far found exactly
        one. That path is told which array was chosen instead."""
        copies, _unused = self._copies(
            ["arrayB"], self._lookup(["arrayB"], swept=True), context=None
        )

        assert copies == []


class TestRecommendationIsIdempotent:
    """Fusion picks the placement, so a repeat run must not ask for another

    A named context does not narrow where the module looks when Fusion is placing -
    Fusion may have put the workload on any member - so the lookup spans the fleet
    and a second run finds what the first one made. Looking only where the operator
    pointed would find nothing, request a new placement, and make a second workload
    through no action of theirs.

    End to end through main(), because a repeat run no longer reaches create_workload
    at all: what was an early exit inside it is now the decision table routing to
    nothing, connect or recover - and two of those it never used to reach.
    """

    def _run(self, homes, fails=False, **params):
        # A context is named and points at the wrong member on purpose: with a
        # recommendation it routes the question and never narrows the search
        module = Mock()
        module.check_mode = False
        module.params = _params(
            preset="test-preset", context="arrayA", recommendation=True, **params
        )
        array = _mock_fleet(homes)
        return module, array, _run_main(module, array, refused=fails)

    def test_an_existing_workload_is_returned_unchanged(self):
        module, array, actions = self._run({"arrayB": {}})

        array.post_workloads_placement_recommendations.assert_not_called()
        actions["create_workload"].assert_not_called()
        assert module.exit_json.call_args.kwargs["changed"] is False
        assert module.exit_json.call_args.kwargs["workload"]["context"] == "arrayB"

    def test_the_same_name_on_two_members_is_refused(self):
        """Nothing in the task says which one is meant, and choosing would be
        arbitrary"""
        module, array, actions = self._run({"arrayA": {}, "arrayB": {}}, fails=True)

        message = module.fail_json.call_args.kwargs["msg"]
        assert "arrayA" in message and "arrayB" in message
        assert "Set context" in message
        array.post_workloads_placement_recommendations.assert_not_called()
        for action in actions.values():
            action.assert_not_called()

    def test_nothing_found_still_asks_fusion(self):
        with patch(
            "plugins.modules.purefa_workload._ask_fusion_for_placement",
            return_value="arrayC",
        ) as fusion:
            module, _unused, actions = self._run({})

        module.fail_json.assert_not_called()
        fusion.assert_called_once()
        actions["create_workload"].assert_called_once()
        arguments = _bound_arguments(
            "create_workload", actions["create_workload"].call_args
        )
        assert arguments["context"] == "arrayC"

    def test_a_repeat_run_with_a_host_connects_it(self):
        """The early exit returned before connect_or_disconnect_volumes could be
        reached, so a repeat run that asked for a host reported ok having silently
        skipped it"""
        _unused, array, actions = self._run({"arrayB": {}}, host="host1")

        array.post_workloads_placement_recommendations.assert_not_called()
        actions["create_workload"].assert_not_called()
        actions["connect_or_disconnect_volumes"].assert_called_once()
        arguments = _bound_arguments(
            "connect_or_disconnect_volumes",
            actions["connect_or_disconnect_volumes"].call_args,
        )
        assert arguments["mode"] == "connect"
        assert arguments["context"] == "arrayB"

    def test_a_workload_destroyed_since_the_last_run_is_recovered(self):
        """The early exit reported ok on a workload pending eradication, which is
        neither present nor going to become present on its own. recover_workload
        needed no change - nothing could route to it."""
        _unused, array, actions = self._run({"arrayB": {"destroyed": True}})

        array.post_workloads_placement_recommendations.assert_not_called()
        actions["create_workload"].assert_not_called()
        actions["recover_workload"].assert_called_once()
        arguments = _bound_arguments(
            "recover_workload", actions["recover_workload"].call_args
        )
        assert arguments["context"] == "arrayB"


class TestRecommendationWithoutAContext:
    """Asking Fusion to choose still needs a route to ask through

    Naming neither context nor placement is the documented way to let Fusion pick
    the member, and both spellings of that - "" and the None main() used to leave
    behind - went into context_names as an empty context, which the array answers
    with an internal error.

    The array addressed is only the route the question travels. It is never a
    default placement - _decide_action refuses a create that has neither a member
    nor a recommendation - and these tests pin the difference.

    Asked of _choose_placement and create_workload together, since main() reaches the
    create arm with the placement already settled.
    """

    def _module(self, context=""):
        module = Mock()
        module.check_mode = False
        module.params = _params(
            preset="test-preset", context=context, recommendation=True, wait=False
        )
        module.fail_json.side_effect = SystemExit
        return module

    def _array(self):
        array = _mock_array()
        # Nothing of this name anywhere, which is why the create arm was reached at
        # all - _decide_action looked before anything got this far
        array.get_workloads.return_value = _mock_not_found_response()
        calculation = Mock()
        calculation.name = "calc-1"
        array.post_workloads_placement_recommendations.return_value = Mock(
            status_code=200, items=[calculation]
        )
        array.post_workloads.return_value = _mock_workload_response(context="arrayB")
        return array

    @pytest.mark.parametrize("context", ["", None])
    @patch(
        "plugins.modules.purefa_workload.get_local_array_name",
        return_value="MUCFA21",
    )
    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_the_array_addressed_is_the_route_when_none_was_named(
        self, mock_check_response, mock_wait, mock_local_array_name, context
    ):
        module = self._module(context)
        array = self._array()
        mock_wait.return_value = _mock_recommendation("arrayB")

        _create_as_main_does(module, array, Mock(parameters=[]))

        asked = array.post_workloads_placement_recommendations.call_args.kwargs
        assert asked["context_names"] == ["MUCFA21"]

    @patch(
        "plugins.modules.purefa_workload.get_local_array_name",
        return_value="MUCFA21",
    )
    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_the_poll_follows_the_same_route(
        self, mock_check_response, mock_wait, mock_local_array_name
    ):
        """The calculation lives in the context it was started in, so reading it
        back through a different one finds nothing"""
        module = self._module()
        array = self._array()
        mock_wait.return_value = _mock_recommendation("arrayB")

        _create_as_main_does(module, array, Mock(parameters=[]))

        assert mock_wait.call_args.args[2] == "MUCFA21"

    @patch(
        "plugins.modules.purefa_workload.get_local_array_name",
        return_value="MUCFA21",
    )
    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_a_named_context_is_asked_through_as_given(
        self, mock_check_response, mock_wait, mock_local_array_name
    ):
        """No default: a context the task named is the one the question travels"""
        module = self._module(context="pod1")
        array = self._array()
        mock_wait.return_value = _mock_recommendation("arrayB")

        _create_as_main_does(module, array, Mock(parameters=[]))

        asked = array.post_workloads_placement_recommendations.call_args.kwargs
        assert asked["context_names"] == ["pod1"]
        mock_local_array_name.assert_not_called()

    @patch(
        "plugins.modules.purefa_workload.get_local_array_name",
        return_value="MUCFA21",
    )
    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_the_route_is_not_a_placement(
        self, mock_check_response, mock_wait, mock_local_array_name
    ):
        """The workload lands where Fusion said, never on the array asked"""
        module = self._module()
        array = self._array()
        mock_wait.return_value = _mock_recommendation("arrayB")

        _create_as_main_does(module, array, Mock(parameters=[]))

        assert array.post_workloads.call_args.kwargs["context_names"] == ["arrayB"]
        assert module.exit_json.call_args.kwargs["workload"]["context"] == "arrayB"

    @patch(
        "plugins.modules.purefa_workload.get_local_array_name",
        return_value="MUCFA21",
    )
    @patch("plugins.modules.purefa_workload.check_response")
    def test_nothing_is_asked_when_the_workload_is_already_there(
        self, mock_check_response, mock_local_array_name
    ):
        """A route is only worked out where one is needed. A repeat run never reaches
        the create arm, so nothing is routed anywhere and nothing is asked."""
        module = self._module(context=None)
        array = _mock_fleet({"arrayB": {}})

        _run_main(module, array)

        mock_local_array_name.assert_not_called()
        array.post_workloads_placement_recommendations.assert_not_called()

    @patch(
        "plugins.modules.purefa_workload.get_local_array_name",
        return_value="MUCFA21",
    )
    @patch("plugins.modules.purefa_workload._wait_for_recommendation")
    @patch("plugins.modules.purefa_workload.check_response")
    def test_check_mode_asks_fusion_through_the_array_addressed(
        self, mock_check_response, mock_wait, mock_local_array_name
    ):
        """A calculation changes nothing, which is what lets --check report the
        target Fusion would have chosen - including with no context named"""
        module = self._module()
        module.check_mode = True
        array = self._array()
        mock_wait.return_value = _mock_recommendation("arrayB")

        _create_as_main_does(module, array, Mock(parameters=[]))

        asked = array.post_workloads_placement_recommendations.call_args.kwargs
        assert asked["context_names"] == ["MUCFA21"]
        array.post_workloads.assert_not_called()
        assert module.exit_json.call_args.kwargs["workload"]["context"] == "arrayB"


class TestDuplicateNameIsReportedNotHidden:
    """A name is unique per fleet member, so the same one elsewhere is a
    different workload - worth saying, never worth acting on"""

    def _array(self, homes):
        array = _mock_array()

        def get_workloads(names=None, context_names=None, **kwargs):
            member = (context_names or [None])[0]
            if member in homes:
                return _mock_workload_response(context=member)
            return _mock_not_found_response()

        array.get_workloads.side_effect = get_workloads
        return array

    @patch("plugins.modules.purefa_workload.check_response")
    def test_creating_warns_when_the_name_exists_elsewhere(self, mock_check_response):
        """The create says it in its own words, which is why it is handed the list
        rather than warned about by the caller: what it makes is a second workload of
        the same name, not a duplicate"""
        module = Mock()
        module.check_mode = False
        module.params = _params(preset="test-preset", context="pod1", wait=False)
        array = self._array(["arrayB"])
        array.post_workloads.return_value = _mock_workload_response(context="pod1")

        create_workload(module, array, "pod1", Mock(parameters=[]), others=["arrayB"])

        module.warn.assert_called_once()
        warning = module.warn.call_args[0][0]
        assert "arrayB" in warning
        # Warned, not refused - the array permits it and the user named a context
        array.post_workloads.assert_called_once()

    def test_the_create_is_told_which_members_already_hold_the_name(self):
        """Which members those are is main()'s answer, from the sweep that used to
        happen inside the create"""
        module = Mock()
        module.check_mode = False
        module.params = _params(context="pod1", preset="test-preset")
        actions = _run_main(module, _mock_fleet({"arrayB": {}}))

        arguments = _bound_arguments(
            "create_workload", actions["create_workload"].call_args
        )
        assert arguments["others"] == ["arrayB"]
        assert arguments["context"] == "pod1"

    def _lookup(self, member="arrayB"):
        """A member-scoped lookup that found the workload where it was asked for"""
        from plugins.modules.purefa_workload import WorkloadLookup

        return WorkloadLookup(
            matches={member: _mock_workload(context=member)}, swept=False
        )

    def test_removing_warns_that_copies_remain(self):
        from plugins.modules.purefa_workload import _warn_about_copies_elsewhere

        module = Mock(params=_params(context="arrayB"))

        _warn_about_copies_elsewhere(
            module, self._array(["arrayA", "arrayB"]), "test-fleet", self._lookup()
        )

        warning = module.warn.call_args[0][0]
        # The survivor is named, and the one being acted on is described as the
        # only thing affected rather than listed among the survivors
        assert "arrayA" in warning
        assert "Only the one on arrayB" in warning

    def test_removing_says_nothing_when_it_is_the_only_one(self):
        from plugins.modules.purefa_workload import _warn_about_copies_elsewhere

        module = Mock(params=_params(context="arrayB"))

        _warn_about_copies_elsewhere(
            module, self._array(["arrayB"]), "test-fleet", self._lookup()
        )

        module.warn.assert_not_called()


class TestAbsenceIsReadFromTheArraysExplanation:
    """The status alone cannot say a workload is missing

    A workload read answers 400 for several different mistakes, and only one of
    them is absence. Treating the rest as "not there" is how a create duplicates
    or a delete reports success having done nothing.
    """

    def _read(self, status_code, messages):
        from plugins.modules.purefa_workload import _read_workload

        module = Mock(params=_params())
        array = _mock_array()
        response = Mock(
            status_code=status_code,
            items=[],
            errors=[Mock(message=message) for message in messages],
        )
        array.get_workloads.return_value = response
        with patch("plugins.modules.purefa_workload.check_response") as surfaced:
            result = _read_workload(module, array, "arrayB")
        return result, surfaced, response

    @pytest.mark.parametrize(
        "message",
        [
            "Workload does not exist.",
            # The match is loose on purpose, so wording and punctuation can drift
            "workload does not exist",
            "The workload does not exist on this array",
        ],
    )
    def test_absence_is_recognised(self, message):
        result, surfaced, _unused = self._read(400, [message])

        assert result is None
        surfaced.assert_not_called()

    def test_absence_is_recognised_on_a_404_too(self):
        result, surfaced, _unused = self._read(404, ["Workload does not exist."])

        assert result is None
        surfaced.assert_not_called()

    @pytest.mark.parametrize(
        "message",
        [
            "Cannot specify context that is a fleet",
            "Cannot specify search parameter names without allow_errors.",
            "Executor not found for [MUCLAB].arrays",
        ],
    )
    def test_the_other_400s_are_surfaced(self, message):
        """Each of these is this module's own mistake, not a missing workload"""
        result, surfaced, response = self._read(400, [message])

        surfaced.assert_called_once()
        assert surfaced.call_args.args[0] is response
        assert result is None  # only because check_response is stubbed here

    def test_a_400_explaining_nothing_is_surfaced(self):
        _unused, surfaced, _unused = self._read(400, [])

        surfaced.assert_called_once()

    def test_a_server_error_is_surfaced(self):
        _unused, surfaced, _unused = self._read(500, ["Workload does not exist."])

        surfaced.assert_called_once()


class TestNamingNothingMeansTheFleet:
    """Naming nothing, and naming the fleet, are the same request

    Both mean "wherever in the fleet this workload is", and every operation except a
    create can answer it: they act on a workload that already exists, so the member
    holding it is looked up rather than stated. Six of the module's own 11 EXAMPLES
    name neither option and were refused outright before this.

    End to end through main(), because what is pinned here is the whole pipeline -
    where to look, what was found, what to do, and which array the action was handed.
    """

    FLEET = FLEET_NAME
    #: The two spellings of "the whole fleet", which must behave identically
    WHOLE_FLEET = (None, FLEET_NAME)

    def _run(self, homes, fails=False, **params):
        module = Mock()
        module.check_mode = False
        # context defaults to omitted here, which is the whole point of the class
        module.params = _params(**{"context": None, **params})
        array = _mock_fleet(homes)
        return module, array, _run_main(module, array, refused=fails)

    def _contexts_read(self, array):
        return [
            call.kwargs.get("context_names", [None])[0]
            for call in array.get_workloads.call_args_list
        ]

    # --- the member holding it is the member acted on ---------------------------

    @pytest.mark.parametrize("context", WHOLE_FLEET)
    @pytest.mark.parametrize(
        "params,homes,action",
        [
            ({"state": "absent"}, {"arrayB": {}}, "delete_workload"),
            (
                {"state": "absent", "host": "host1"},
                {"arrayB": {}},
                "connect_or_disconnect_volumes",
            ),
            (
                {"state": "absent", "eradicate": True},
                {"arrayB": {"destroyed": True}},
                "eradicate_workload",
            ),
            ({"state": "present"}, {"arrayB": {"destroyed": True}}, "recover_workload"),
            (
                {"state": "present", "host": "host1"},
                {"arrayB": {}},
                "connect_or_disconnect_volumes",
            ),
            (
                {"state": "present", "rename": "new-workload"},
                {"arrayB": {}},
                "rename_workload",
            ),
            (
                {
                    "state": "expand",
                    "preset": "test-preset",
                    "volume_count": 1,
                    "volume_configuration": "vol-config",
                },
                {"arrayB": {}},
                "expand_workload",
            ),
        ],
    )
    def test_the_member_holding_it_is_the_member_acted_on(
        self, context, params, homes, action
    ):
        """One of these per EXAMPLE that used to be refused. Each resolves to the
        member the sweep found it on, and that member is what the action is handed -
        never the array the request happened to reach."""
        module, _unused, actions = self._run(homes, context=context, **params)

        actions[action].assert_called_once()
        arguments = _bound_arguments(action, actions[action].call_args)
        assert arguments["context"] == "arrayB"
        module.fail_json.assert_not_called()

    @pytest.mark.parametrize(
        "state,mode", [("present", "connect"), ("absent", "disconnect")]
    )
    def test_the_host_direction_is_the_one_the_decision_named(self, state, mode):
        """One function does both, so the mode is the whole difference between
        giving a host access to the workload's volumes and taking it away"""
        _unused, _unused, actions = self._run({"arrayB": {}}, state=state, host="host1")

        arguments = _bound_arguments(
            "connect_or_disconnect_volumes",
            actions["connect_or_disconnect_volumes"].call_args,
        )
        assert arguments["mode"] == mode

    def test_the_no_change_exit_describes_the_member_it_found(self):
        """Nothing was asked for, so the workload's own answer is the only source -
        including for the volume read the facts are built from"""
        module, array, _unused = self._run({"arrayB": {}}, state="present")

        module.exit_json.assert_called_once_with(
            changed=False, workload=_expected_facts()
        )
        assert array.get_volumes.call_args.kwargs["context_names"] == ["arrayB"]

    @pytest.mark.parametrize("context", WHOLE_FLEET)
    def test_the_bare_fleet_name_is_never_used_as_a_query_context(self, context):
        """The invariant the whole scheme rests on, and it must hold for the
        context-less default too: the array rejects a fleet as a query context with a
        400 that reads exactly like the workload being absent - which under
        state: present would be a create."""
        _unused, array, _unused = self._run(
            {"arrayB": {}}, context=context, state="absent"
        )

        assert self.FLEET not in self._contexts_read(array)

    @pytest.mark.parametrize("context", WHOLE_FLEET)
    def test_the_bare_fleet_name_is_never_used_as_a_route_to_fusion(self, context):
        """The same invariant on the one path that does not read first: Fusion's
        question travels through an array, and a fleet is not one"""
        with patch(
            "plugins.modules.purefa_workload._ask_fusion_for_placement",
            return_value="arrayC",
        ) as fusion:
            _unused, _unused, actions = self._run(
                {}, context=context, preset="test-preset", recommendation=True
            )

        # Empty rather than the fleet, so the question is routed through the array
        # addressed - which is a member
        assert fusion.call_args.args[2] == ""
        actions["create_workload"].assert_called_once()
        arguments = _bound_arguments(
            "create_workload", actions["create_workload"].call_args
        )
        # And what the create is handed is Fusion's answer, never the route
        assert arguments["context"] == "arrayC"

    # --- what is refused, and what is not --------------------------------------

    @pytest.mark.parametrize("context", WHOLE_FLEET)
    @pytest.mark.parametrize("state", ["present", "absent", "expand"])
    def test_the_same_name_on_two_members_is_refused(self, context, state):
        """A name belongs to a member, not to a fleet, so two of them are two
        workloads and nothing in the task says which is meant. There is no state for
        which "which of these did you mean" has an answer."""
        module, _unused, actions = self._run(
            {"arrayA": {}, "arrayB": {}},
            fails=True,
            context=context,
            state=state,
            preset="test-preset",
            volume_count=1,
            volume_configuration="vol-config",
        )

        message = module.fail_json.call_args.kwargs["msg"]
        assert "arrayA" in message and "arrayB" in message
        for action in actions.values():
            action.assert_not_called()

    @pytest.mark.parametrize("context", WHOLE_FLEET)
    def test_nothing_found_on_a_create_is_refused(self, context):
        """The fleet says where to look, not where to create - and naming the fleet
        is not naming a member"""
        from plugins.modules.purefa_workload import _CREATE_NEEDS_A_MEMBER

        module, _unused, actions = self._run(
            {}, fails=True, context=context, state="present", preset="test-preset"
        )

        assert module.fail_json.call_args.kwargs[
            "msg"
        ] == _CREATE_NEEDS_A_MEMBER.format(name="test-workload", fleet=self.FLEET)
        actions["create_workload"].assert_not_called()

    @pytest.mark.parametrize("context", WHOLE_FLEET)
    def test_nothing_found_with_recommendation_lets_fusion_choose(self, context):
        """The one create that needs no member named, because Fusion names one"""
        with patch(
            "plugins.modules.purefa_workload._ask_fusion_for_placement",
            return_value="arrayC",
        ):
            module, _unused, actions = self._run(
                {}, context=context, preset="test-preset", recommendation=True
            )

        module.fail_json.assert_not_called()
        actions["create_workload"].assert_called_once()

    @pytest.mark.parametrize("context", WHOLE_FLEET)
    def test_nothing_found_on_a_removal_is_already_done(self, context):
        """Not a failure - absent is the requested end state, and it is already the
        case"""
        module, _unused, _unused = self._run({}, context=context, state="absent")

        module.fail_json.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False, workload={})

    @pytest.mark.parametrize("context", WHOLE_FLEET)
    def test_nothing_found_on_an_expand_is_refused(self, context):
        """Unlike absent, expand needs something to add volumes to"""
        module, array, actions = self._run(
            {},
            fails=True,
            context=context,
            state="expand",
            preset="test-preset",
            volume_count=1,
            volume_configuration="vol-config",
        )

        message = module.fail_json.call_args.kwargs["msg"]
        assert "nothing to add volumes to" in message
        # Names where it looked, rather than an empty context
        assert f"anywhere in fleet {self.FLEET}" in message
        actions["expand_workload"].assert_not_called()
        # And the preset is not read for a workload that is not there
        array.get_presets_workload.assert_not_called()

    # --- the destructive default names the array it picked ---------------------

    def test_a_removal_with_no_context_says_which_array_it_chose(self):
        """The fact the operator lacks. The copies-elsewhere warning cannot fire on
        this path - two matches were already refused - and its wording names a context
        they never wrote, which reads as confirmation of something they typed."""
        module, _unused, _unused = self._run({"arrayB": {}}, state="absent")

        warning = module.warn.call_args[0][0]
        assert "No context was named" in warning
        assert "arrayB" in warning
        assert "destroyed" in warning

    def test_naming_the_fleet_is_not_reported_as_naming_nothing(self):
        module, _unused, _unused = self._run(
            {"arrayB": {}}, context=self.FLEET, state="absent"
        )

        warning = module.warn.call_args[0][0]
        assert f"context {self.FLEET} names fleet {self.FLEET}" in warning
        assert "arrayB" in warning

    @pytest.mark.parametrize(
        "params,homes",
        [
            ({"state": "absent", "eradicate": True}, {"arrayB": {"destroyed": True}}),
            ({"state": "absent", "eradicate": True}, {"arrayB": {}}),
        ],
    )
    def test_an_eradicate_with_no_context_says_so_in_those_words(self, params, homes):
        """A delete asked to eradicate does both, so the word that matters is the
        one for the half that cannot be undone"""
        module, _unused, _unused = self._run(homes, **params)

        assert "will be eradicated" in module.warn.call_args[0][0]

    @pytest.mark.parametrize(
        "params,homes,action",
        [
            ({"state": "present"}, {"arrayB": {"destroyed": True}}, "recover_workload"),
            (
                {"state": "present", "host": "host1"},
                {"arrayB": {}},
                "connect_or_disconnect_volumes",
            ),
            (
                {"state": "absent", "host": "host1"},
                {"arrayB": {}},
                "connect_or_disconnect_volumes",
            ),
        ],
    )
    def test_only_the_destructive_actions_say_which_array_was_chosen(
        self, params, homes, action
    ):
        """Nothing is lost on these, so there is nothing to confirm before it is"""
        module, _unused, actions = self._run(homes, **params)

        actions[action].assert_called_once()
        module.warn.assert_not_called()

    def test_a_named_member_is_told_about_copies_instead(self):
        """Complementary, never both: named a context, "it also exists over there";
        named nothing, "I picked this one" """
        module, _unused, actions = self._run(
            {"arrayA": {}, "arrayB": {}}, context="arrayB", state="absent"
        )

        actions["delete_workload"].assert_called_once()
        warning = module.warn.call_args[0][0]
        assert "also exists on arrayA" in warning
        assert "Only the one on arrayB" in warning
        assert "No context was named" not in warning


class TestTheCasesTheChainLost:
    """The four combinations that fell off the end of the elif chain, end to end

    They reached a bare else that reported changed: false and described whatever the
    read had returned. Two of them meant that anyway; two did not, and are the bugs
    this step makes live. Decided as a table in _decide_action, they are asserted here
    through main() because that is where the old behaviour was visible.
    """

    def _run(self, homes, fails=False, **params):
        module = Mock()
        module.check_mode = False
        module.params = _params(**params)
        array = _mock_fleet(homes)
        return module, array, _run_main(module, array, refused=fails)

    def test_expanding_a_destroyed_workload_is_refused(self):
        """It reported ok having added nothing - a silent success where the
        operator's storage did not grow"""
        module, array, actions = self._run(
            {"arrayB": {"destroyed": True}},
            fails=True,
            state="expand",
            preset="test-preset",
            volume_count=1,
            volume_configuration="vol-config",
        )

        message = module.fail_json.call_args.kwargs["msg"]
        assert "destroyed" in message and "nothing to add volumes to" in message
        actions["expand_workload"].assert_not_called()
        module.exit_json.assert_not_called()
        # And no preset is read for volumes that are not going to be built
        array.get_presets_workload.assert_not_called()

    def test_a_destroyed_workload_is_not_eradicated_by_a_disconnect_task(self):
        """The trap: adding eradicate: true to a host disconnect eradicated the
        workload, ignoring the host that made it a disconnect in the first place"""
        module, _unused, actions = self._run(
            {"arrayB": {"destroyed": True}},
            state="absent",
            host="host1",
            eradicate=True,
        )

        actions["eradicate_workload"].assert_not_called()
        actions["connect_or_disconnect_volumes"].assert_not_called()
        assert module.exit_json.call_args.kwargs["changed"] is False
        # Not silently, either
        warning = module.warn.call_args[0][0]
        assert "already disconnected" in warning
        assert "eradicate is not applied" in warning

    def test_a_destroyed_workload_with_a_host_is_a_no_op_with_a_reason(self):
        """The volumes went with the workload, so the host is already disconnected.
        Failing would break idempotency; silence is what hid the case above."""
        module, _unused, actions = self._run(
            {"arrayB": {"destroyed": True}}, state="absent", host="host1"
        )

        actions["connect_or_disconnect_volumes"].assert_not_called()
        assert module.exit_json.call_args.kwargs["changed"] is False
        assert "already disconnected" in module.warn.call_args[0][0]
        # Only mentioned when it was actually set
        assert "eradicate" not in module.warn.call_args[0][0]

    def test_a_workload_that_is_already_as_asked_reports_itself(self):
        """state: present and it is present - the idempotent success path, which was
        only ever reached by falling off the end"""
        module, _unused, actions = self._run({"arrayB": {}}, state="present")

        for action in actions.values():
            action.assert_not_called()
        module.exit_json.assert_called_once_with(
            changed=False, workload=_expected_facts()
        )

    def test_a_destroyed_workload_pending_eradication_reports_its_countdown(self):
        """It is absent in the sense state: absent asks for, and time_remaining is
        the useful part of saying so"""
        module, _unused, actions = self._run(
            {"arrayB": {"destroyed": True, "time_remaining": 86400000}}, state="absent"
        )

        for action in actions.values():
            action.assert_not_called()
        module.exit_json.assert_called_once_with(
            changed=False,
            workload=_expected_facts(
                destroyed=True, status="ready", time_remaining=86400000
            ),
        )

    def test_a_server_error_on_the_read_is_not_taken_for_absence(self):
        """main() read the workload itself, so any non-200 - including a genuine 500 -
        read as "not there", and a create then made a duplicate. The read now goes
        through _read_workload, which surfaces anything the array did not explain as
        absence."""
        module = Mock()
        module.params = _params(state="present", preset="test-preset")
        error = Mock(
            status_code=500, items=[], errors=[Mock(message="Internal server error")]
        )
        array = _mock_fleet({})
        array.get_workloads.side_effect = None
        array.get_workloads.return_value = error

        def surface(response, *arguments):
            """The real check_response ends the module on a response like this"""
            if response is error:
                raise SystemExit

        with patch(
            "plugins.modules.purefa_workload.check_response", side_effect=surface
        ) as surfaced:
            with pytest.raises(SystemExit):
                _run_main(module, array)

        assert error in [call.args[0] for call in surfaced.call_args_list]
        module.exit_json.assert_not_called()


class TestTheFleetIsSweptOnce:
    """One question, one sweep

    Three call sites swept the fleet before - resolving a fleet context, the create's
    idempotency check, and the copies-elsewhere warning - so one task could pay up to
    three times for the same answer. There is no behavioural symptom, so nothing but
    a call count catches a regression here.
    """

    def _sweeps(self, context, homes, **params):
        """How many times main() asked the whole fleet, running it for real"""
        import plugins.modules.purefa_workload as module_under_test

        array = _mock_fleet(homes)
        module = Mock()
        module.check_mode = False
        module.params = _params(context=context, **params)
        with patch.object(
            module_under_test,
            "_find_across_fleet",
            wraps=module_under_test._find_across_fleet,
        ) as sweep:
            _run_main(module, array)
        return sweep.call_count

    def test_a_fleet_scoped_removal_sweeps_once(self):
        """It has to sweep to find the member at all, and the copies question is
        then answered from the same result rather than asked again"""
        assert self._sweeps(None, {"arrayB": {}}, state="absent") == 1

    def test_a_fleet_scoped_recovery_sweeps_once(self):
        assert self._sweeps(None, {"arrayB": {"destroyed": True}}, state="present") == 1

    def test_a_member_scoped_removal_sweeps_once(self):
        """It reads one member, then pays one sweep to answer whether the name lives
        anywhere else - deliberately, and once"""
        assert self._sweeps("arrayB", {"arrayB": {}}, state="absent") == 1

    def test_a_member_scoped_create_sweeps_once(self):
        """The create's own sweep is gone. The one it pays for now is the shared
        copies-elsewhere question, asked in main() like every other action's."""
        assert (
            self._sweeps("pod1", {"arrayB": {}}, state="present", preset="test-preset")
            == 1
        )

    def test_a_recommendation_create_sweeps_once(self):
        """Two of the three old sweeps were on this path: the fleet lookup and the
        create's idempotency check asked the same question one after the other"""
        with patch(
            "plugins.modules.purefa_workload._ask_fusion_for_placement",
            return_value="arrayC",
        ):
            sweeps = self._sweeps(
                None, {}, state="present", preset="test-preset", recommendation=True
            )

        assert sweeps == 1

    def test_a_rename_pays_one_sweep_per_name(self):
        """A sweep answers only for the name it was made about, and a rename involves
        two: renaming foo to bar where bar already exists elsewhere makes two bars"""
        assert (
            self._sweeps(None, {"arrayB": {}}, rename="new-workload", state="present")
            == 2
        )


class TestEveryActionHasAHandler:
    """main() has one arm per action, and the set is checked rather than trusted

    The chain this replaces lost whole cases by falling off the end into a bare else -
    which is how expanding a destroyed workload came to report ok having added
    nothing. This catches an action that _decide_action can return and main() does not
    handle. It cannot catch a row transcribed into the wrong arm; that is what
    TestDecidingWhatToDo is for.
    """

    def _dispatched_actions(self):
        """Every action literal main() tests decision.action for being

        Read off the parsed source rather than by running main(), so that an arm with
        no test of its own is still counted. Only == and in are read: a != guard is
        not a handler, and counting one would let a deleted arm pass unnoticed.
        """
        import ast
        import inspect
        import plugins.modules.purefa_workload as module_under_test

        dispatched = set()
        for node in ast.walk(ast.parse(inspect.getsource(module_under_test.main))):
            if not isinstance(node, ast.Compare):
                continue
            if not (
                isinstance(node.left, ast.Attribute) and node.left.attr == "action"
            ):
                continue
            for operator, comparator in zip(node.ops, node.comparators):
                if not isinstance(operator, (ast.Eq, ast.In)):
                    continue
                for element in getattr(comparator, "elts", [comparator]):
                    if isinstance(element, ast.Constant):
                        dispatched.add(element.value)
        return dispatched

    def test_the_arms_and_the_declared_actions_are_the_same_set(self):
        from plugins.modules.purefa_workload import ACTIONS

        assert self._dispatched_actions() == set(ACTIONS)

    def test_an_action_with_no_arm_fails_loudly_rather_than_reporting_no_change(self):
        """The else is not reachable through _decide_action, which is the point of
        asserting on it directly: reporting changed: false is what an unhandled
        action used to do"""
        from plugins.modules.purefa_workload import Decision

        module = Mock()
        module.params = _params(state="absent")
        array = _mock_fleet({"arrayB": {}})

        with patch(
            "plugins.modules.purefa_workload._decide_action",
            return_value=Decision("teleport"),
        ):
            _run_main(module, array, refused=True)

        assert "teleport" in module.fail_json.call_args.kwargs["msg"]
        module.exit_json.assert_not_called()
