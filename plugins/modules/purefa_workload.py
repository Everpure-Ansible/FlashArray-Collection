#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2025, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_workload
version_added: '1.33.0'
short_description: Manage Fusion Fleet Workloads
description:
- Apply/Rename/Delete Fusion fleet workloads
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  context:
    description:
    - Name of the fleet member on which to perform the workload operation, or
      the name of the fleet itself.
    - Defaults to the whole fleet. Selecting the fleet means - "the workload
      with this name, wherever it is in the fleet".
    - A create is the one exception, because there is nothing to look up. Either
      specify this or I(placement), or set I(recommendation), in which case
      Fusion chooses the target array.
    - A workload is identified by its name B(and) its member. The same name on
      two fleet members is two separate workloads, so naming a different member
      creates a second one rather than moving the first. If two or more members
      hold the name in the same context (e.g. Fleet), the task is ambiguous and
      fails naming them, rather than picking one.
    type: str
    version_added: '1.36.0'
  host:
    type: str
    description:
    - Host to connect to every volume in the workload after provisioning.
    - With I(state=absent) the host is disconnected from the workload's volumes
      instead of the workload being deleted.
    - Only the workload's own volumes are affected. Volumes the host is connected
      to outside this workload are never changed.
    - Refused together with I(rename), which does not disturb connections and
      connects nothing. Run the two as separate tasks.
    default: ""
  name:
    description:
    - Name of the workload.
    type: str
    required: true
  state:
    description:
    - Define whether to create or delete a fleet workload.
    - Using the expand option will add volume(s) to the workload.
    - If absent is specified together with a host, rather than deleting the workload, the host will be disconnected from the workload
    default: present
    choices: [ absent, present, expand]
    type: str
  preset:
    description:
    - Name of an existing workload preset to build the workload from.
    - Required to create a workload, and to expand one
    - Presets are fleet objects, named C(<fleet>:<preset>) by the API. Give the
      bare name; the fleet is prefixed automatically.
    type: str
  rename:
    description:
    - new name for a workload
    type: str
  eradicate:
    description:
    - whether to eradicate a workload
    - Applies only to I(state=absent). Any other state is refused.
    type: bool
    default: false
  placement:
    description:
    - Name of the fleet member on which the workload will be deployed.
    - Same as I(context), so naming both with different members fails.
    - Naming neither this nor I(context) means the whole fleet - see I(context)
      for what that resolves to, and for the one operation that cannot default.
    - Ignored when I(recommendation) is true, as the recommended target
      replaces it.
    type: str
  recommendation:
    description:
    - whether to use the Fusion placement recommendation based
      on the workload preset definitions during creates.
    - This will use the first recommended placement if more than
      one is available
    - Only useful during a create. Every other operation works from the member
      already holding the workload, which is looked up rather than chosen, so
      setting this there changes nothing.
    default: false
    type: bool
  parameters:
    description:
    - Parameter values to apply when creating a workload from the preset.
    - Parameters are only applied on the create path and are not applied
      when recovering an existing destroyed workload.
    - Any task that does not create is told they were not applied, rather than
      dropping them silently.
    type: list
    elements: dict
    suboptions:
      name:
        description:
        - Name of the preset parameter to set.
        type: str
        required: true
      value:
        description:
        - Value for the preset parameter.
        - Exactly one of C(string), C(integer), C(boolean), or
          C(resource_reference) must be provided.
        type: dict
        required: true
        suboptions:
          string:
            description:
            - String parameter value.
            type: str
          integer:
            description:
            - Integer parameter value.
            type: int
          boolean:
            description:
            - Boolean parameter value.
            type: bool
          resource_reference:
            description:
            - Reference to another resource.
            type: dict
            suboptions:
              id:
                description:
                - ID of the referenced resource.
                type: str
              name:
                description:
                - Name of the referenced resource.
                type: str
              resource_type:
                description:
                - Optional resource type for the reference.
                type: str
  volume_count:
    description:
    - Number of additional volumes to add to an existing workload
    - Only used with I(state=expand), where it is required.
    - Must be a positive integer. Zero is rejected.
    type: int
  volume_configuration:
    description:
    - Name of the volume configuration to use for adding volumes
      to a workload
    type: str
  wait:
    description:
    - Whether to wait for the array to finish provisioning before returning.
    - Cannot be disabled when I(host) is set. A host can only be connected to
      every volume in a workload once the volume set has settled.
    type: bool
    default: true
    version_added: '1.45.0'
  wait_timeout:
    description:
    - Maximum number of seconds to wait for a single array operation when
      I(wait) is true. The task fails if that operation has not finished within
      this time.
    - This bounds each operation individually rather than the task as a whole, so
      a task that waits for more than one can take a multiple of it.
    type: int
    default: 300
    version_added: '1.45.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create a workload using an existing preset on a specific placement target and connect to host myhost
  everpure.flasharray.purefa_workload:
    name: foo
    preset: bar
    host: myhost
    placement: arrayB
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create a workload using an existing preset using the recommended target and connect to host myhost
  everpure.flasharray.purefa_workload:
    name: foo
    preset: bar
    host: myhost
    recommendation: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create a workload on the recommended target, waiting for it to be ready
  everpure.flasharray.purefa_workload:
    name: foo
    preset: bar
    recommendation: true
    wait: true
    wait_timeout: 600
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: new_workload

- name: Report the fleet member Fusion placed the workload on
  ansible.builtin.debug:
    msg: "{{ new_workload.workload.name }} placed on {{ new_workload.workload.context }}"

- name: Report the volumes the array provisioned
  ansible.builtin.debug:
    msg: "{{ new_workload.workload.volumes }}"

- name: Create a workload using preset parameters
  everpure.flasharray.purefa_workload:
    name: foo
    preset: bar
    context: arr1
    parameters:
      - name: replication_target
        value:
          resource_reference:
            name: arr2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Add volumes to workload foo based on volume configuration fin and connect to host myhost
  everpure.flasharray.purefa_workload:
    name: foo
    preset: bar
    volume_configuration: fin
    volume_count: 3
    host: myhost
    state: expand
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Add a volume to workload foo, wherever in the fleet it lives
  everpure.flasharray.purefa_workload:
    # Naming neither context nor placement searches the fleet and acts on the
    # member holding foo, so the task does not need to know which one that is.
    name: foo
    preset: bar
    volume_configuration: fin
    volume_count: 1
    state: expand
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename an existing workload
  everpure.flasharray.purefa_workload:
    name: foo
    rename: bar
    context: arr1
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Disconnect an existing workload from host
  everpure.flasharray.purefa_workload:
    name: foo
    host: myhost
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete an existing workload on a named fleet member
  everpure.flasharray.purefa_workload:
    # Omitting context here would delete foo wherever in the fleet it is found.
    # That works, but name the member when the target matters.
    name: foo
    context: arr1
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Eradicate an existing workload on a named fleet member
  everpure.flasharray.purefa_workload:
    # Eradication cannot be undone, so say which array it applies to. Run it
    # with --check first; the reported context is the array that would lose the
    # workload.
    name: foo
    context: arr1
    state: absent
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Recover a deleted workload
  everpure.flasharray.purefa_workload:
    name: foo
    state: present
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Reconnect an existing workload to a host
  everpure.flasharray.purefa_workload:
    name: foo
    host: myhost
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
workload:
    description: Describes what a task did to the workload.
        Returned on every action. An eradication leaves nothing to read off, so it
        reports I(name) and I(context) alone - which workload, and the array it was
        removed from - and none of the other keys below. The dict is empty only when
        there was no workload at all, as for I(state=absent) against a name that
        exists nowhere in the fleet. More detail is available from the array by
        M(everpure.flasharray.purefa_info) rather than repeated here.
    type: dict
    returned: success
    contains:
        name:
            description: Name of the workload. This is the new name after a
                rename.
            type: str
            sample: 'foo'
        context:
            description: Name of the fleet member the workload is placed on.
                When I(recommendation) is used this is the target chosen by
                Fusion. Together with I(name) it identifies the workload -
                the same name on another fleet member is a different workload.
            type: str
            sample: 'arrayB'
        status:
            description: Status of the workload, as reported by the array.
                Normally one of C(creating), C(ready), C(destroying),
                C(destroyed), C(eradicating) or C(recovering). Passed through
                unmodified, so a future Purity release may report a value not in
                this list, and null when the array reports no status at all. Use
                I(completed) to test for completion rather than comparing this
                field - a null or unrecognised status counts as still in flight
                and raises a warning.
            type: str
            sample: 'ready'
        completed:
            description: Whether the array has finished the operation in flight
                for this workload. A destroyed workload is complete but still pending
                eradication - see I(time_remaining).
            type: bool
            sample: false
        destroyed:
            description: Whether deletion of the workload has been requested.
                This says nothing about whether the deletion has finished - see
                I(completed).
            type: bool
            sample: false
        time_remaining:
            description: Milliseconds until a destroyed workload is eradicated.
                Null unless I(destroyed) is true. A check-mode run that predicts a
                destroy also reports null, because the countdown only starts once
                the destroy is applied; a check-mode run that merely reports a
                workload already destroyed passes the array's own value through.
            type: int
            sample: 86400000
        volumes:
            description: Names of the volumes belonging to this workload, as they
                stand after the action. In check mode a create reports an empty
                list and an expand reports only the volumes that already exist.
            type: list
            elements: str
            sample: ['foo-vol1', 'foo-vol2']
"""

from typing import NamedTuple

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        WorkloadConfigurationReference,
        WorkloadParameter,
        WorkloadParameterValue,
        WorkloadParameterValueResourceReference,
        WorkloadPatch,
        WorkloadPost,
        WorkloadPlacementRecommendation,
        VolumePost,
        ConnectionPost,
    )
except ImportError:
    HAS_PURESTORAGE = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_response,
    get_local_array_name,
    wait_for,
)

VERSION = 1.5
USER_AGENT_BASE = "Ansible"
MIN_REQUIRED_API_VERSION = "2.40"
SUPPORTED_PARAMETER_VALUE_TYPES = (
    "string",
    "integer",
    "boolean",
    "resource_reference",
)

# The API reports exactly these six statuses. Only two are terminal. There is NO
# failure state, so a broken provision is indistinguishable from a slow one and
# is caught by wait_timeout rather than reported as a failure.
TERMINAL_STATUSES = frozenset({"ready", "destroyed"})
TRANSIENT_STATUSES = frozenset({"creating", "destroying", "eradicating", "recovering"})

# A read by name reports a missing object as an error rather than as an empty
# result, so absence has to be recognised from the error itself. These two statuses
# are the only candidates - every other status, 5xx above all, is surfaced rather
# than quietly reported as absence.
NOT_FOUND_STATUSES = frozenset({400, 404})

# ...but the status alone will not do. The array answers with 400 for several
# different mistakes, only one of which means the workload is not there.
# so additionally we match on a lowercase substring so wording and punctuation
# can drift without breaking.
NOT_FOUND_TEXT = "does not exist"


def _parameter_fail(module, parameter_name, message):
    module.fail_json(msg=f"Invalid workload parameter '{parameter_name}': {message}")


def _coerce_parameter_list(parameter_items):
    if parameter_items is None:
        return []
    try:
        return list(parameter_items)
    except TypeError:
        return []


def _supplied_option_keys(value_definition, allowed_keys):
    return [
        key
        for key in allowed_keys
        if key in value_definition and value_definition[key] is not None
    ]


def _build_resource_reference(module, parameter_name, resource_reference):
    if not isinstance(resource_reference, dict):
        _parameter_fail(
            module,
            parameter_name,
            "resource_reference must be a dictionary",
        )
    unknown_keys = set(resource_reference) - {"id", "name", "resource_type"}
    if unknown_keys:
        _parameter_fail(
            module,
            parameter_name,
            "resource_reference contains unsupported keys: {0}".format(
                ", ".join(sorted(unknown_keys))
            ),
        )
    identifier_keys = _supplied_option_keys(resource_reference, ("id", "name"))
    if len(identifier_keys) != 1:
        _parameter_fail(
            module,
            parameter_name,
            "resource_reference must include exactly one of id or name",
        )
    return WorkloadParameterValueResourceReference(
        **{
            key: resource_reference[key]
            for key in resource_reference
            if resource_reference[key] is not None
        }
    )


def _build_parameter_value(module, parameter_name, value_definition):
    if not isinstance(value_definition, dict):
        _parameter_fail(module, parameter_name, "value must be a dictionary")
    unknown_keys = set(value_definition) - set(SUPPORTED_PARAMETER_VALUE_TYPES)
    if unknown_keys:
        _parameter_fail(
            module,
            parameter_name,
            "value contains unsupported keys: {0}".format(
                ", ".join(sorted(unknown_keys))
            ),
        )
    supplied_value_types = _supplied_option_keys(
        value_definition, SUPPORTED_PARAMETER_VALUE_TYPES
    )
    if len(supplied_value_types) != 1:
        _parameter_fail(
            module,
            parameter_name,
            "value must include exactly one of {0}".format(
                ", ".join(SUPPORTED_PARAMETER_VALUE_TYPES)
            ),
        )

    value_type = supplied_value_types[0]
    normalized_value = value_definition[value_type]
    if value_type == "string":
        if not isinstance(normalized_value, str):
            _parameter_fail(module, parameter_name, "string value must be a string")
    elif value_type == "integer":
        if isinstance(normalized_value, bool) or not isinstance(normalized_value, int):
            _parameter_fail(module, parameter_name, "integer value must be an integer")
    elif value_type == "boolean":
        if not isinstance(normalized_value, bool):
            _parameter_fail(
                module, parameter_name, "boolean value must be true or false"
            )
    elif value_type == "resource_reference":
        normalized_value = _build_resource_reference(
            module, parameter_name, normalized_value
        )

    return value_type, WorkloadParameterValue(**{value_type: normalized_value})


def _build_workload_parameters(module, preset_config):
    raw_parameters = module.params.get("parameters") or []
    if not raw_parameters:
        return None

    preset_parameters = {}
    for preset_parameter in _coerce_parameter_list(
        getattr(preset_config, "parameters", [])
    ):
        if getattr(preset_parameter, "name", None):
            preset_parameters[preset_parameter.name] = preset_parameter

    normalized_parameters = []
    seen_parameters = set()
    for raw_parameter in raw_parameters:
        if not isinstance(raw_parameter, dict):
            module.fail_json(msg="Each workload parameter must be a dictionary")
        parameter_name = raw_parameter.get("name")
        if not parameter_name:
            module.fail_json(msg="Each workload parameter requires a name")
        if parameter_name in seen_parameters:
            _parameter_fail(module, parameter_name, "parameter names must be unique")
        if parameter_name not in preset_parameters:
            _parameter_fail(
                module,
                parameter_name,
                "parameter is not defined by preset {0}".format(
                    module.params["preset"]
                ),
            )
        if "value" not in raw_parameter:
            _parameter_fail(module, parameter_name, "parameter requires a value")

        value_type, parameter_value = _build_parameter_value(
            module, parameter_name, raw_parameter["value"]
        )
        preset_type = getattr(preset_parameters[parameter_name], "type", None)
        if preset_type and preset_type != value_type:
            _parameter_fail(
                module,
                parameter_name,
                "expected type {0}, got {1}".format(preset_type, value_type),
            )

        normalized_parameters.append(
            WorkloadParameter(name=parameter_name, value=parameter_value)
        )
        seen_parameters.add(parameter_name)
    return normalized_parameters


def _status_completed(module, name, status):
    """True when the array has no operation in flight for a workload

    Anything unrecognised counts as in-flight, so a status added by a future
    Purity release can never be mistaken for success.
    """
    if status in TERMINAL_STATUSES:
        return True
    if status not in TRANSIENT_STATUSES:
        module.warn(
            f"Workload {name} reported unrecognised status {status!r}. "
            f"Treating as in progress. This collection may need updating."
        )
    return False


def _workload_completed(module, workload):
    """_status_completed() for an already-read Workload"""
    return _status_completed(
        module,
        getattr(workload, "name", None),
        getattr(workload, "status", None),
    )


# Check mode has two rules in this module. An action function decides what to
# report, since only it knows what its own action would have produced. Every other
# function guards its own writes, so that a write cannot escape by being called
# from somewhere new. Waiting is handled once, in wait_for().


def _workload_volume_names(module, array, name, context):
    """Sorted names of the volumes belonging to a workload"""
    res = array.get_volumes(
        filter="workload.name='{0}'".format(name),
        context_names=[context],
    )
    check_response(res, module, f"Failed to get volumes for workload {name}")
    return sorted(volume.name for volume in list(res.items))


def _connected_volume_names(module, array, context, volume_names, host):
    """Which of the given volumes the host can currently see

    Scoped to volume_names, so connections the host has outside this workload are
    never even read, let alone changed. get_connections rejects multiple names on
    two objects at once, so the host is the single name and the volumes the many.
    """
    if not volume_names:
        return set()
    res = array.get_connections(
        host_names=[host],
        volume_names=volume_names,
        context_names=[context],
    )
    check_response(res, module, f"Failed to get connections for host {host}")
    # The volume, and the name on it, are both optional, so a connection naming no
    # volume is dropped rather than raising
    names = {
        getattr(getattr(connection, "volume", None), "name", None)
        for connection in list(res.items)
    }
    names.discard(None)
    return names


def _facts(
    module,
    context,
    name=None,
    status=None,
    volumes=None,
    destroyed=False,
    time_remaining=None,
):
    """The workload contract

    What the task did, rather than everything the array knows about the workload.
    A workload's own properties - the preset it came from, when it was created, the
    array's free-form status text - are what purefa_info reports, and repeating
    them here would only invite the two to disagree.

    The defaults are what a workload that does not exist yet can report.
    """
    return {
        "name": name,
        "context": context,
        "status": status,
        # Derived here, so it can never disagree with the status beside it
        "completed": _status_completed(module, name, status),
        "destroyed": destroyed,
        "time_remaining": time_remaining,
        "volumes": volumes or [],
    }


def _workload_facts(module, array, workload, context, volume_names=None, **changes):
    """Describe a workload the array reported

    volume_names is passed in by callers that have already read them, so a path
    doing host work does not read the same list twice.

    changes replaces fields the caller knows differ from what the array said,
    which is how check mode reports a state it has not applied. They land on the
    values _facts() is given rather than the dict it returns, so that everything
    _facts() derives is derived from the changed values.
    """
    if not workload:
        return {}
    # In the SDK every field on a workload is optional, if we try to read one that
    # is not defined it will raise, so we use getattr()
    workload_context = getattr(workload, "context", None)

    name = getattr(workload, "name", None) or module.params["name"]
    if volume_names is None:
        # Read under the name the workload still answers to, which for a rename is
        # the old one
        volume_names = _workload_volume_names(module, array, name, context)
    values = {
        "name": name,
        "context": getattr(workload_context, "name", None) or context,
        "status": getattr(workload, "status", None),
        "destroyed": getattr(workload, "destroyed", False),
        "time_remaining": getattr(workload, "time_remaining", None),
    }
    return _facts(module, volumes=volume_names, **{**values, **changes})


def _is_absent(response):
    """A response the array explained as the workload not being there

    Matching on message text is unpleasant, and was avoided for as long as the
    status code alone could carry it. It cannot: the array answers 400 for several
    different mistakes, and only one of them means absence. The match is
    deliberately loose - lowercase substring, across every error rather than the
    first - and if it ever stops matching, a missing workload surfaces as a task
    failure quoting the array. That is the safe direction to be wrong in: loud
    rather than silent.

    A response carrying no errors at all is not absence either, and falls through
    to be surfaced rather than assumed benign.
    """
    if getattr(response, "status_code", None) not in NOT_FOUND_STATUSES:
        return False
    return any(
        NOT_FOUND_TEXT in (getattr(error, "message", "") or "").lower()
        for error in getattr(response, "errors", None) or []
    )


def _read_workload(module, array, context, name=None):
    """Read the workload in the given context, or None if it does not exist

    A workload that is not there is reported as an error rather than as an empty
    result - with or without allow_errors - so absence is recognised by
    _is_absent(), which reads the array's own explanation. A server error can
    therefore never be mistaken for a missing workload and reported as success by
    a caller waiting for one to go away.

    allow_errors is required whenever the context is a fleet member other than the
    local array being addressed.

    name defaults to the workload the task is about. It is given explicitly when the
    question is about another name - a rename asking whether its target already
    exists somewhere.
    """
    name = name or module.params["name"]
    res = array.get_workloads(
        names=[name],
        context_names=[context],
        allow_errors=True,
    )
    if res.status_code == 200:
        return list(res.items)[0]
    if _is_absent(res):
        return None
    check_response(res, module, f"Failed to read workload {name}")


def _find_across_fleet(module, array, fleet, name=None):
    """Every fleet member reporting a workload of this name, as {member: workload}

    Names are not unique across a fleet: the same name on two members is two
    separate workloads, and both are returned.

    name defaults to the workload the task is about, and is given explicitly when
    the question is about another name - a rename asking where its target already
    exists.

    "<fleet>.arrays" is a context that spans every member, and answers this in one
    call. The bare fleet name does not - the array rejects it with "Cannot specify
    context that is a fleet" - and the form used here is not in the SDK's
    documentation, so a member-by-member sweep backs it up. That fallback is not
    only for old releases: a rejection of the fleet-wide query is indistinguishable
    from the workload being absent, and reading "unsupported" as "not there" would
    let a create make a duplicate.

    A 200 is only trusted when it is a complete answer, for the same reason - see
    below.
    """
    name = name or module.params["name"]
    res = array.get_workloads(
        names=[name],
        context_names=[f"{fleet}.arrays"],
        allow_errors=True,
    )
    if res.status_code == 200:
        items = list(res.items)
        reported = {
            member: workload
            for workload in items
            for member in [getattr(getattr(workload, "context", None), "name", None)]
            if member
        }
        # A 200 is not the same as a complete answer. allow_errors is what turns a
        # member that could not be reached into a partial result carrying an errors
        # list rather than a failed call, and every field the SDK returns is
        # optional, so an item can arrive with no context to attribute it to. Both
        # mean "I did not see it", which must never be recorded as "it is not
        # there": a create would then duplicate, and a delete would report success
        # having touched nothing. Ask each member individually instead.
        if len(reported) == len(items) and not (hasattr(res, "errors") and res.errors):
            return reported

    found = {}
    # Every member, and deliberately not stopping at the first hit: the same name on
    # two members is two workloads, and only a complete list can say so. Returning
    # early would defeat the ambiguity check and turn a duplicate name into a
    # silently wrong target.
    for member in _fleet_members(module, array, fleet):
        workload = _read_workload(module, array, member, name)
        if workload is not None:
            found[member] = workload
    return found


def _warn_about_copies_elsewhere(module, array, fleet, lookup, name=None):
    """Say when a name being acted on here also exists on other fleet members

    Reporting only. The module acts on exactly the (name, context) it was given, and
    this must never widen that: eradication cannot be undone, so a fleet-wide search
    informs the operator rather than choosing a target for them.

    name defaults to the workload the task is about. A rename asks twice - once for
    the name it is leaving, once for the name it is taking, since renaming foo to bar
    where bar already exists on another member produces two bars.
    """
    name = name or module.params["name"]
    others = _copies_elsewhere(module, array, fleet, lookup, name)
    if others:
        module.warn(
            f"A workload named {name} also exists on "
            f"{', '.join(others)}. Only the one on "
            f"{_member_being_acted_on(module.params, lookup)} is affected here - a "
            "name is unique per fleet member, not across the fleet."
        )


def _status_detail(workload):
    """Render the array's own diagnostics for a timeout message"""
    if not workload:
        return ""
    return ", ".join(getattr(workload, "status_details", None) or [])


def _wait_for_status(module, array, context, status):
    """Wait until the workload has settled into the given status

    The context is passed in rather than read from module.params, so that a
    recommendation-resolved placement stays fixed for the life of the poll.
    """
    return wait_for(
        module,
        probe=lambda: _read_workload(module, array, context),
        is_done=lambda workload: (
            workload is not None
            and _workload_completed(module, workload)
            and workload.status == status
        ),
        timeout=module.params["wait_timeout"],
        description=f"workload {module.params['name']} to become {status}",
        detail=_status_detail,
    )


def _wait_for_absent(module, array, context):
    """Wait until the workload has been fully eradicated

    Done here is the absence of a status rather than a value of one, so this is
    the one path that cannot use _workload_completed().
    """
    return wait_for(
        module,
        probe=lambda: _read_workload(module, array, context),
        is_done=lambda workload: workload is None,
        timeout=module.params["wait_timeout"],
        description=f"workload {module.params['name']} to be eradicated",
        detail=_status_detail,
    )


def _wait_for_connections(module, array, name, context, connected):
    """Wait until the host sees all of the workload's volumes, or none of them

    connected=True after a connect, False after a disconnect. Both the volume
    list and the connections are re-read each iteration, so a volume that
    appears late is caught rather than missed, and the poll never looks at
    connections outside this workload.
    """
    host = module.params["host"]

    def probe():
        volume_names = _workload_volume_names(module, array, name, context)
        return {
            "volumes": volume_names,
            "seen": _connected_volume_names(module, array, context, volume_names, host),
        }

    def is_done(state):
        if connected:
            return set(state["volumes"]) == state["seen"]
        # Done is the host seeing none of *these* volumes, not the host having
        # no connections at all
        return not state["seen"]

    def detail(state):
        if connected:
            outstanding = sorted(set(state["volumes"]) - state["seen"])
        else:
            outstanding = sorted(state["seen"])
        return ", ".join(outstanding)

    return wait_for(
        module,
        probe=probe,
        is_done=is_done,
        timeout=module.params["wait_timeout"],
        description=(
            f"host {host} to be {'connected to' if connected else 'disconnected from'} "
            f"the volumes of workload {name}"
        ),
        detail=detail,
    )


def _wait_for_recommendation(module, array, context, calculation):
    """Wait for Fusion to finish calculating a placement recommendation

    Unlike a workload, this endpoint reports a real failure state, so this is the
    one waiter with something for wait_for's is_failed hook. Runs under check
    mode: it reads a calculation and changes nothing on the array.
    """

    def probe():
        res = array.get_workloads_placement_recommendations(
            names=[calculation], context_names=[context]
        )
        check_response(res, module, "Failed to read placement recommendation")
        return list(res.items)[0]

    return wait_for(
        module,
        probe=probe,
        # status is optional, and a calculation reporting none is still in flight as
        # far as this is concerned, so both tests read it with a default
        is_done=lambda result: getattr(result, "status", None) == "completed",
        is_failed=lambda result: (
            f"Fusion could not find a placement for preset "
            f"{module.params['preset']}"
            if getattr(result, "status", None) == "failed"
            else None
        ),
        timeout=module.params["wait_timeout"],
        description=(
            f"a placement recommendation for preset {module.params['preset']}"
        ),
        # Polled in check mode too: a calculation changes nothing on the array,
        # and it is what lets a check run report the target Fusion would choose
        skip_in_check_mode=False,
    )


def _wait_for_volumes(module, array, context, volume_names, workload):
    """Wait until new volumes exist and the workload has settled back to ready

    Volumes carry no lifecycle status of their own, so the volume half of this
    can only test existence, and the POST that created them has already
    returned. The workload half is what covers the configuration the preset
    derives from those volumes.

    Falls back to the workload it was given when there was nothing to wait for,
    so callers never have to handle an absent result.
    """

    def probe():
        res = array.get_volumes(names=volume_names, context_names=[context])
        # A name that does not resolve yet is an error rather than an empty
        # result, and here means "not created yet" rather than a real failure
        found = (
            {volume.name for volume in list(res.items)}
            if res.status_code == 200
            else set()
        )
        return {"workload": _read_workload(module, array, context), "volumes": found}

    def is_done(state):
        workload = state["workload"]
        return (
            not set(volume_names) - state["volumes"]
            and workload is not None
            and _workload_completed(module, workload)
            and workload.status == "ready"
        )

    state = wait_for(
        module,
        probe=probe,
        is_done=is_done,
        timeout=module.params["wait_timeout"],
        description=(
            f"volumes added to workload {module.params['name']} to become ready"
        ),
        detail=lambda state: _status_detail(state["workload"]),
    )
    return state["workload"] if state else workload


# Eight functions below act on a workload on a particular array - _create_volume and
# the seven actions main() dispatches to - and each is told that array as its third
# argument, ahead of anything it is asked to do there. Required, with no fallback to
# module.params["context"]: the array was settled by the pipeline before any of these
# was called.


def _create_volume(module, array, context):
    """Create an actual volume in a workload

    Returns the array-generated volume name, so that a later wait can target
    exactly the volumes this task created, or None in check mode where no volume
    was created and so none can be named.

    The check-mode guard below is the second of two: expand_workload does not call
    this at all in check mode. It is kept rather than removed as unreachable so
    that no future caller can create a volume by forgetting to guard.
    """
    if module.check_mode:
        return None
    res = array.post_volumes(
        volume=VolumePost(
            workload=WorkloadConfigurationReference(
                name=module.params["name"],
                configuration=module.params["volume_configuration"],
            ),
        ),
        context_names=[context],
    )
    check_response(res, module, "Workload volume creation failed")
    return list(res.items)[0].name


def _connect_host(module, array, name, context, volume_names):
    """Connect the host to any of the workload's volumes it cannot already see

    Additive only, and only within this workload: the host keeps every connection
    it has elsewhere. post_connections has no allow_errors, so reposting an
    existing connection is an error rather than a no-op, which is why only the
    difference is sent.

    Returns whether a connection was missing.
    """
    host = module.params["host"]
    missing = sorted(
        set(volume_names)
        - _connected_volume_names(module, array, context, volume_names, host)
    )
    if missing and not module.check_mode:
        res = array.post_connections(
            host_names=[host],
            volume_names=missing,
            context_names=[context],
            connection=ConnectionPost(),
        )
        check_response(res, module, f"Failed to connect volumes to host {host}")
        if module.params["wait"]:
            _wait_for_connections(module, array, name, context, connected=True)
    return bool(missing)


def _disconnect_host(module, array, name, context, volume_names):
    """Disconnect the host from the workload's volumes, and only those

    Subtractive only, and only within this workload. volume_names is always
    passed, so connections the host has elsewhere are left alone.

    Returns whether there was a connection to remove.
    """
    host = module.params["host"]
    attached = sorted(
        _connected_volume_names(module, array, context, volume_names, host)
        & set(volume_names)
    )
    if attached and not module.check_mode:
        res = array.delete_connections(
            host_names=[host],
            volume_names=attached,
            context_names=[context],
        )
        check_response(res, module, f"Failed to disconnect volumes from host {host}")
        if module.params["wait"]:
            _wait_for_connections(module, array, name, context, connected=False)
    return bool(attached)


def _ask_fusion_for_placement(module, array, route, preset_config):
    """Ask Fusion which array to create on, and return the one it names

    route is the array the question travels through, never the answer. This is the
    one call in the module with no member for its context to describe - nothing has
    been placed yet - which is why falling back to the array addressed is safe here
    and is not a default placement: Fusion's answer replaces it before anything is
    created. Without the fallback a task that named neither context nor placement
    sends an empty context, which the array rejects with an internal error.
    """
    route = route or get_local_array_name(array, module)
    # Start the workload calculation for the preset being used
    res = array.post_workloads_placement_recommendations(
        inputs=WorkloadPlacementRecommendation(
            parameters=_build_workload_parameters(module, preset_config)
        ),
        preset_names=[module.params["preset"]],
        context_names=[route],
    )
    check_response(res, module, "Recommendation calculation failure")
    workload_calc = getattr(list(res.items)[0], "name", None)
    # A calculation, not a change, so this runs in check mode too - it is what lets a
    # check-mode run report the target Fusion would have chosen
    result = _wait_for_recommendation(module, array, route, workload_calc)
    # Every link on the way to the target is optional and every list can come back
    # empty, so the walk is guarded as a whole and a gap is reported as the missing
    # recommendation it is, rather than as an error further downstream.
    try:
        target = result.results[0].placements[0].targets[0].name
    except (AttributeError, IndexError):
        target = None
    if not target:
        module.fail_json(
            msg="Fusion reported a completed placement recommendation for preset "
            f"{module.params['preset']} but named no target to deploy on."
        )
    return target


def _choose_placement(module, array, fleet, member, preset_config):
    """Which array a NEW workload is created on - the only place this is decided

    Two possible sources: the operator named a member, or Fusion chose one. There
    is no fallback to the array the request happened to reach.
    """
    if module.params["recommendation"]:
        # What was named routes the question and does not answer it, so the fleet
        # itself is blanked here rather than sent: the array rejects a fleet as a
        # context, and naming the fleet is the same request as naming nothing.
        route = _requested_member(module.params)
        return _ask_fusion_for_placement(
            module, array, "" if route == fleet else route, preset_config
        )
    # _decide_action guarantees a real member here: a create that named none and did
    # not ask Fusion is the one thing left that cannot be resolved, and it is refused
    # before anything gets this far.
    return member


def create_workload(module, array, context, preset_config, others=None):
    """Create a workload on one array from an existing preset

    context is the array to create on. It is decided before this is called - see
    _choose_placement - so there is no placement reasoning here and no lookup: by now
    it is known that nothing of this name is there to find.

    others are the fleet members that already hold this name. That does not stop the
    create, and the array permits it: a name is unique per member, not across the
    fleet, so what this makes is a second workload rather than a duplicate. Said
    rather than refused, and in the create's own words - which is why the list is
    handed in instead of warned about by the caller.
    """
    changed = True
    workload_parameters = _build_workload_parameters(module, preset_config)
    if others:
        module.warn(
            f"A workload named {module.params['name']} already exists on "
            f"{', '.join(others)}. Creating on {context} makes a "
            "separate workload: a name is unique per fleet member, not across "
            "the fleet."
        )
    if module.check_mode:
        # Nothing exists to read, so everything reported is predicted. The context
        # is the resolved one, which for a recommendation is Fusion's choice. Only
        # what a create can know is named here; volumes are left to _facts() to
        # default, because the array generates their names.
        workload_facts = _facts(
            module,
            name=module.params["name"],
            context=context,
            status="ready" if module.params["wait"] else "creating",
        )
    else:
        res = array.post_workloads(
            names=[module.params["name"]],
            preset_names=[module.params["preset"]],
            workload=WorkloadPost(parameters=workload_parameters),
            context_names=[context],
        )
        check_response(
            res, module, f"Failed to create workload {module.params['name']}"
        )
        workload = list(res.items)[0]
        if module.params["wait"]:
            workload = _wait_for_status(module, array, context, "ready")
        # Read once, after the wait, so the host sees the settled volume set and
        # the facts report the same list the connect worked from
        volume_names = _workload_volume_names(module, array, workload.name, context)
        if module.params["host"] != "":
            _connect_host(module, array, workload.name, context, volume_names)
        workload_facts = _workload_facts(module, array, workload, context, volume_names)

    module.exit_json(changed=changed, workload=workload_facts)


def expand_workload(module, array, context, volume_configs, workload):
    """Add new volumes to workload"""
    changed = False
    matched = False
    volume_names = []
    for vol_config in volume_configs:
        if vol_config.name == module.params["volume_configuration"]:
            matched = True
            for _volume in range(module.params["volume_count"]):
                changed = True
                # Creating storage is the costliest thing this module does, so it
                # is guarded here as well as inside _create_volume
                if module.check_mode:
                    continue
                volume_names.append(_create_volume(module, array, context))
    if not matched:
        module.fail_json(
            msg="Volume Configuration {0} does not exist for preset {1}.".format(
                module.params["volume_configuration"], module.params["preset"]
            )
        )
    if module.params["wait"]:
        # Re-read rather than reuse main()'s workload, which predates the volumes
        workload = _wait_for_volumes(module, array, context, volume_names, workload)
    # The full set, not just the volumes this task added - the host must end up
    # able to see all of them, and the facts report the grown set
    all_volume_names = _workload_volume_names(module, array, workload.name, context)
    if module.params["host"] != "":
        _connect_host(module, array, workload.name, context, all_volume_names)

    if module.check_mode:
        # The volumes that would be added cannot be named in advance, so only the
        # existing ones are listed
        workload_facts = _workload_facts(
            module,
            array,
            workload,
            context,
            all_volume_names,
            status=(
                "ready" if module.params["wait"] else getattr(workload, "status", None)
            ),
        )
    else:
        # Without a wait this is still main()'s pre-expand read, which is accurate
        # because only the workload's volumes changed here
        workload_facts = _workload_facts(
            module, array, workload, context, all_volume_names
        )
    module.exit_json(changed=changed, workload=workload_facts)


def delete_workload(module, array, context, workload=None):
    """Delete the workload"""
    changed = True
    if module.check_mode:
        # Nothing is sent, so report the state this run would have produced
        if module.params["eradicate"]:
            # An eradicate leaves nothing behind to describe, so this reports what
            # eradicate_workload reports - the workload and the array it is on, and
            # nothing else - which is what the real run this predicts would say
            workload_facts = {
                "name": module.params["name"],
                "context": context,
            }
        else:
            workload_facts = _workload_facts(
                module,
                array,
                workload,
                context,
                destroyed=True,
                status="destroyed" if module.params["wait"] else "destroying",
            )
    else:
        res = array.patch_workloads(
            names=[module.params["name"]],
            workload=WorkloadPatch(destroyed=True),
            context_names=[context],
        )
        check_response(res, module, "Workload deletion failed")
        # The PATCH response reports destroyed=True and the time_remaining
        # countdown until eradication, so use it rather than the pre-delete read
        deleted = list(res.items)[0]
        if module.params["wait"]:
            deleted = _wait_for_status(module, array, context, "destroyed")
        workload_facts = _workload_facts(module, array, deleted, context)
        if module.params["eradicate"]:
            eradicate_workload(module, array, context)
    module.exit_json(changed=changed, workload=workload_facts)


def eradicate_workload(module, array, context):
    """Eradicate the workload"""
    changed = True
    if not module.check_mode:
        res = array.delete_workloads(
            names=[module.params["name"]],
            context_names=[context],
        )
        check_response(res, module, "Workload eradication failed")
        if module.params["wait"]:
            _wait_for_absent(module, array, context)
    # The workload no longer exists, so there are no facts left to read off it - but
    # which one, and on which array, is exactly what an operator dry-running an
    # eradicate is asking, and the more so when the context was resolved for them
    # rather than written in the task. So name that much and nothing more, and name
    # it identically in check mode and on a real run: check mode has to predict the
    # run it stands in for.
    module.exit_json(
        changed=changed,
        workload={"name": module.params["name"], "context": context},
    )


def recover_workload(module, array, context, workload=None):
    """Recover the workload and optionally reconnect to host"""
    changed = True
    if module.check_mode:
        # Nothing is sent, so report the state this run would have produced
        workload_facts = _workload_facts(
            module,
            array,
            workload,
            context,
            destroyed=False,
            status="ready" if module.params["wait"] else "recovering",
        )
    else:
        res = array.patch_workloads(
            names=[module.params["name"]],
            workload=WorkloadPatch(destroyed=False),
            context_names=[context],
        )
        check_response(res, module, "Workload recovery failed")
        recovered = list(res.items)[0]
        if module.params["wait"]:
            recovered = _wait_for_status(module, array, context, "ready")
        # Recovered volumes may have kept their connections, so the diff inside
        # _connect_host is what makes reconnecting work rather than error
        volume_names = _workload_volume_names(module, array, recovered.name, context)
        if module.params["host"] != "":
            _connect_host(module, array, recovered.name, context, volume_names)
        workload_facts = _workload_facts(
            module, array, recovered, context, volume_names
        )

    module.exit_json(changed=changed, workload=workload_facts)


def rename_workload(module, array, context, workload=None):
    """Rename the workload

    Nothing about a rename is asynchronous, so wait does not apply, and a rename
    does not disturb connections, so there is no host work either. The volumes
    and host are still reported, read under whichever name is current.
    """
    changed = True
    if module.check_mode:
        # Nothing is sent, so report the name this run would have given it
        workload_facts = _workload_facts(
            module, array, workload, context, name=module.params["rename"]
        )
    else:
        res = array.patch_workloads(
            names=[module.params["name"]],
            workload=WorkloadPatch(name=module.params["rename"]),
            context_names=[context],
        )
        check_response(res, module, "Workload rename failed")
        # Reports the new name, as returned by the PATCH response
        workload_facts = _workload_facts(module, array, list(res.items)[0], context)
    module.exit_json(changed=changed, workload=workload_facts)


def connect_or_disconnect_volumes(module, array, context, mode, workload):
    """Connect the host to the workload's volumes, or disconnect it from them

    Both directions are scoped to this workload's volumes. The host keeps every
    connection it has outside the workload either way.
    """
    if mode == "connect" and module.params["wait"]:
        # "All connected" only means something once the volume set has settled
        workload = _wait_for_status(module, array, context, "ready") or workload
    volume_names = _workload_volume_names(module, array, workload.name, context)

    if mode == "connect":
        changed = _connect_host(module, array, workload.name, context, volume_names)
    else:
        changed = _disconnect_host(module, array, workload.name, context, volume_names)

    # Only host connections change here, not the workload itself
    module.exit_json(
        changed=changed,
        workload=_workload_facts(module, array, workload, context, volume_names),
    )


def _fleet_members(module, array, fleet):
    """Names of every member of the given fleet

    Filtered by name rather than taking whatever the array lists: an array may
    belong to more than one fleet, and the rest of the module works from a single
    fleet name. Without the filter the two halves of _find_across_fleet would search
    different sets - and what that set is decides which arrays are candidates for an
    eradication.
    """
    res = array.get_fleets_members(fleet_names=[fleet])
    check_response(res, module, "Failed to list fleet members")
    members = []
    for member in list(res.items):
        name = getattr(getattr(member, "member", None), "name", None)
        if name:
            members.append(name)
    return members


def _check_option_combinations(module):
    """Refuse option combinations that cannot be honoured, before any API call

    Every check here is answerable from the task alone. Nothing that depends on what
    the array holds belongs in it - that is _decide_action's job, once there is
    something to decide about.
    """
    # A host has to be connected to every volume in the workload, which cannot be
    # established while the volume set is still growing, so there is no correct way
    # to honour host without waiting.
    if module.params["host"] and not module.params["wait"]:
        module.fail_json(
            msg="host cannot be used with wait: false. Connecting or "
            "disconnecting a host requires the workload's volume set to have "
            "settled first, which only happens when waiting."
        )

    volume_count = module.params["volume_count"]
    if volume_count is not None and volume_count <= 0:
        module.fail_json(msg="volume_count must be a positive integer.")

    # Renaming is a state: present operation. On any other state the option is
    # silently ignored today, so a task asking to both rename and delete reads as
    # having renamed.
    if module.params["rename"] and module.params["state"] != "present":
        module.fail_json(
            msg=f"rename cannot be used with state: {module.params['state']}. "
            "Renaming a workload is a state: present operation - run it as a "
            "separate task."
        )

    # A rename does not read host, so the two together promise a rename that also
    # connects. The remedy is the one directly above: two tasks.
    if module.params["host"] and module.params["rename"]:
        module.fail_json(
            msg="host cannot be used with rename. A rename does not disturb "
            "connections and connects nothing - run the host task separately."
        )

    # eradicate only ever qualifies a removal, so anything else asks to make sure
    # the workload exists and destroy it for good in the same breath. The other
    # options this module ignores elsewhere are reported rather than refused - see
    # IGNORED_OPTIONS - but there is no reading of this one to report.
    if module.params["eradicate"] and module.params["state"] != "absent":
        module.fail_json(
            msg=f"eradicate cannot be used with state: {module.params['state']}. "
            "It applies only to state: absent, where it removes a destroyed "
            "workload for good."
        )


def _read_fleet_name(module, array):
    """The name of the fleet this array belongs to

    Every workload operation is scoped to a fleet: presets are named after one, and
    a workload lives on one of its members. An array outside a fleet has no
    workloads to manage, so this is a hard requirement rather than a fallback.
    """
    res = array.get_fleets()
    fleets = list(res.items) if res.status_code == 200 else []
    if not fleets:
        module.fail_json(
            msg="purefa_workload requires a Fusion fleet environment, but this "
            "array is not a member of a fleet."
        )
    return fleets[0].name


#: _resolve_member_to_search returns this instead of a member name when the task did
#: not name one, named the fleet, or asked for a recommendation - all three mean
#: "look everywhere and let the answer say which array".
SEARCH_WHOLE_FLEET = None


def _requested_member(params):
    """The fleet member the task named, or "" if it named none

    context and placement are the same thing to the array - a workload is created on
    its context, and there is no separate placement to send - so once they have been
    checked to agree, either stands for both.
    """
    return params["context"] or params["placement"] or ""


def _fusion_will_choose_placement(params):
    """Whether Fusion, rather than the playbook, picks the array for this task

    False for everything but a create: recommendation only ever decides where a
    *new* workload goes. Deleting, expanding or renaming an existing one works from
    the array holding it, and there is nothing there for Fusion to choose.
    """
    return bool(
        params["state"] == "present"
        and params["recommendation"]
        and not params["rename"]
    )


def _resolve_member_to_search(module, array, fleet):
    """Which array to address, or SEARCH_WHOLE_FLEET to look across all of them

    Answers where to look and never what to do about it - state is not read here, so
    no refusal has to guess what the task will go on to do.

    Naming neither context nor placement means the fleet. Every operation except a
    create acts on a workload that already exists, so the member holding it can be
    looked up rather than stated, and a fleet-wide lookup gives the same answer
    whichever member was addressed - which is the property that makes defaulting
    safe where falling back to "the array the request reached" was not.

    The bare fleet name is never returned: the array rejects it as a query context
    with a 400 that reads exactly like the workload being absent, so "the fleet" is
    SEARCH_WHOLE_FLEET and _look_up_workload picks the query shape from that.
    """
    context = module.params["context"]
    placement = module.params["placement"]

    if context and placement and context != placement:
        module.fail_json(
            msg=f"context '{context}' and placement '{placement}' name different "
            "fleet members. They are the same thing to the array, so set one of "
            "them, or set both to the same member."
        )

    # An omitted context is None and means the fleet. An empty string is something a
    # playbook computed, and a computed empty context is how a fleet-wide destroy
    # happens by accident rather than by intent - so the two are no longer spelled
    # the same. This does not catch "| default(omit)", which removes the key
    # entirely; nothing can.
    if context == "":
        module.fail_json(
            msg="context is an empty string, which names no fleet member. Omit it "
            f"to search the whole fleet for {module.params['name']}, or set it to a "
            "member - an empty string is usually an undefined variable, as "
            "'| default('')' produces."
        )

    requested = _requested_member(module.params)
    # The one path that reads nothing: there is no name to check against the fleet
    if not requested:
        return SEARCH_WHOLE_FLEET

    # The fleet itself is allowed and means "wherever in the fleet this workload is"
    allowed = set(_fleet_members(module, array, fleet)) | {fleet}
    for option in ("context", "placement"):
        value = module.params[option]
        if value and value not in allowed:
            module.fail_json(
                msg=f"{option} '{value}' is not a member of fleet {fleet}, nor the "
                f"fleet itself. Valid: {', '.join(sorted(allowed))}."
            )

    if requested == fleet:
        return SEARCH_WHOLE_FLEET

    # A named member does not narrow the search when Fusion is placing: it only
    # routes the question there. Fusion may have put the workload on any member, and
    # looking only where the operator pointed would find nothing, ask for a second
    # placement, and create a second workload on a re-run.
    if _fusion_will_choose_placement(module.params):
        return SEARCH_WHOLE_FLEET
    return requested


class WorkloadLookup(NamedTuple):
    """What the fleet says about this name, and how widely we asked

    Stores only what was read. Everything else is derived from matches, so nothing
    can disagree with it - which is the failure this module already has, with
    module.params["context"] saying one thing and the workload another.
    """

    matches: dict  # {member: workload} - every member reporting this name.
    # More than one is a legitimate answer: a name belongs to a
    # member, not to a fleet, so two of them are two workloads.
    swept: bool  # whether the whole fleet was searched, so a later question
    # about copies elsewhere costs nothing

    @property
    def presence(self):
        """absent, live, destroyed or ambiguous - what _decide_action turns on

        ambiguous is a presence in its own right rather than a length check in front
        of the table, so that "several" can never be read as "none" - which under
        state: present would be a create. destroyed is optional on the SDK model and
        raises rather than returning None, so it is read with a default, as
        everywhere else in this module.
        """
        if len(self.matches) > 1:
            return "ambiguous"
        if not self.matches:
            return "absent"
        return "destroyed" if getattr(self.workload, "destroyed", False) else "live"

    @property
    def members(self):
        """Every array holding this name, sorted - for the ambiguity message"""
        return sorted(self.matches)

    @property
    def member(self):
        """The one array holding it, or None when there is no single answer

        None on both "nothing found" and "found on several", which is safe only
        because presence distinguishes them and _decide_action refuses "ambiguous"
        outright. The array's own answer wins over whatever we asked for, as in
        _workload_facts.
        """
        return next(iter(self.matches)) if len(self.matches) == 1 else None

    @property
    def workload(self):
        return next(iter(self.matches.values())) if len(self.matches) == 1 else None


def _look_up_workload(module, array, fleet, member):
    """What is actually there, as a WorkloadLookup - the only lookup in the module

    Reports and never decides: absence is a result, and so are two matches. Neither
    is refused here, because what they mean depends on the state, and this step does
    not read it.

    Which array the workload is on comes from the array's own answer,
    workload.context.name, rather than from what was asked for - a member-scoped read
    falls back to the member asked only when the answer carries no context at all.
    That single source is what stops "which array are we on" having a different
    answer depending on when it is asked.
    """
    if member is SEARCH_WHOLE_FLEET:
        return WorkloadLookup(
            matches=_find_across_fleet(module, array, fleet), swept=True
        )
    workload = _read_workload(module, array, member)
    if workload is None:
        return WorkloadLookup(matches={}, swept=False)
    home = getattr(getattr(workload, "context", None), "name", None) or member
    return WorkloadLookup(matches={home: workload}, swept=False)


def _member_being_acted_on(params, lookup):
    """The member this task acts on: the one holding the workload, or the one asked

    The array's own answer wins wherever there is one, as everywhere else in this
    module. Falling back to what was asked for covers a task aimed at a member that
    turned out not to hold the name - a delete against arrayB where the workload only
    exists on arrayA - which is still the member the task was aimed at.
    """
    return lookup.member or _requested_member(params)


def _copies_elsewhere(module, array, fleet, lookup, name=None):
    """Every other fleet member holding this workload name, sorted

    The same name on two members is two separate workloads, and an operator acting
    on "the" one needs to know that - so this answers the question, and the caller
    decides how to say it. A sweep already done is reused rather than repeated: on a
    fleet-wide lookup the answer is the lookup itself, and the question is then free.

    Reporting only. Nothing here widens what a task acts on: it destroys exactly the
    (name, context) it was given, and eradication cannot be undone.

    name defaults to the workload the task is about, and is given explicitly for the
    other name a rename involves.
    """
    name = name or module.params["name"]
    here = _member_being_acted_on(module.params, lookup)
    # A sweep already done answers only for the name it was made about, so a rename
    # asking about its target pays for its own
    reuse = lookup.swept and name == module.params["name"]
    found = lookup.matches if reuse else _find_across_fleet(module, array, fleet, name)
    return sorted(member for member in found if member != here)


class Decision(NamedTuple):
    """What to do, and anything the operator needs told while it happens"""

    action: str  # one of ACTIONS
    message: str = None  # the refusal on a "fail", an optional warning otherwise


#: Every action _decide_action can ask for. main() handles exactly these, and
#: handles an unknown one loudly rather than as a silent no-op - which is how the
#: chain this replaces lost expand-on-a-destroyed-workload.
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
    "fail",
)

#: The only refusal left for a task that named no member. It cannot fire when there
#: is anything to act on, so it means exactly "you asked me to invent a placement" -
#: what cannot be done, then what to set. The reasoning belongs in the module
#: documentation, not in an error read by an operator who is already blocked.
_CREATE_NEEDS_A_MEMBER = (
    "Workload {name} was not found in fleet {fleet} and cannot be created without a "
    "target array. Set context or placement to a fleet member, or set "
    "recommendation: true to let Fusion choose one."
)


def _describe_search_area(lookup, member, fleet):
    """Where a message should say it looked: "on arrayB" or "anywhere in fleet F"

    The array's own answer wins where there is one, so no message ever reports a
    context the workload was not actually on.
    """
    where = lookup.member or member
    if where is SEARCH_WHOLE_FLEET:
        return f"anywhere in fleet {fleet}"
    return f"on {where}"


def _decide_action(params, member, lookup, fleet):
    """What to do about what was found - the only place that decides, and pure

    Takes the params rather than the module, and never touches the array: every
    array-dependent refusal is expressed as Decision("fail", ...) for main() to
    raise. That is what makes the whole table testable without mocking anything, and
    it is why this is the only step allowed to read state - nothing here has to guess
    what the task will do, because by now it is known.
    """
    state = params["state"]
    presence = lookup.presence
    area = _describe_search_area(lookup, member, fleet)

    # Before any state branch: there is no action for which "which of these two did
    # you mean" has an answer. Every match counts, destroyed or not - a leftover
    # destroyed copy blocks an otherwise obvious delete until it is eradicated or a
    # context is named, which is a knowing trade for never guessing a target.
    if presence == "ambiguous":
        return Decision(
            "fail",
            f"Workload {params['name']} exists on more than one member of {fleet}: "
            f"{', '.join(lookup.members)}. Set context to the one you mean.",
        )

    if state == "present":
        if presence == "absent":
            if params["rename"]:
                return Decision(
                    "fail",
                    f"Workload {params['name']} does not exist {area}, so there is "
                    f"nothing to rename to {params['rename']}.",
                )
            # Nothing to act on and no member named. A create is the one operation
            # that cannot look its target up, because there is nothing there yet.
            if member is SEARCH_WHOLE_FLEET and not _fusion_will_choose_placement(
                params
            ):
                return Decision(
                    "fail",
                    _CREATE_NEEDS_A_MEMBER.format(name=params["name"], fleet=fleet),
                )
            return Decision("create")
        if presence == "destroyed":
            if params["rename"]:
                return Decision(
                    "fail",
                    f"Workload {params['name']} {area} is destroyed, so there is "
                    f"nothing to rename to {params['rename']}. Recover it first with "
                    "a separate task (state: present, no rename), then rename it.",
                )
            # host does not decide whether recovery is allowed - it is the mode
            # selector everywhere else in this module, and here it is not. Recovery
            # happens either way; a host is connected afterwards.
            return Decision("recover")
        if params["rename"]:
            return Decision("rename")
        if params["host"]:
            return Decision("connect")
        # state: present and it is present. The idempotent success path.
        return Decision("nothing")

    if state == "absent":
        if presence == "absent":
            # Already the requested end state. Whether a copy on another member
            # deserves a word is main()'s question, and it asks it for every action.
            return Decision("nothing")
        if presence == "live":
            if params["host"]:
                if params["eradicate"]:
                    return Decision(
                        "disconnect",
                        f"eradicate is ignored: {params['host']} is named, which "
                        f"makes this a disconnect from the volumes of "
                        f"{params['name']} {area} rather than a removal of the "
                        "workload.",
                    )
                return Decision("disconnect")
            # delete_workload eradicates afterwards when asked to
            return Decision("delete")
        if params["host"]:
            # The volumes went with the workload, so the host is already
            # disconnected. Failing would break idempotency - but silence here is
            # what let eradicate turn a disconnect task into an eradication.
            message = (
                f"Workload {params['name']} {area} is destroyed, so {params['host']} "
                "is already disconnected from its volumes and there is nothing to do."
            )
            if params["eradicate"]:
                message += (
                    " eradicate is not applied: this task names a host, which makes "
                    "it a disconnect rather than a removal."
                )
            return Decision("nothing", message)
        if params["eradicate"]:
            return Decision("eradicate")
        # It is absent, in the sense state: absent asks for - destroyed and pending
        # eradication. The facts carry time_remaining, which is worth reporting.
        return Decision("nothing")

    if state == "expand":
        if presence == "absent":
            # Unlike absent, where not being there is the requested end state, expand
            # asks to add volumes to something that has to exist. Reporting no change
            # would read as "already expanded".
            return Decision(
                "fail",
                f"Workload {params['name']} does not exist {area}, so there is "
                "nothing to add volumes to.",
            )
        if presence == "destroyed":
            return Decision(
                "fail",
                f"Workload {params['name']} {area} is destroyed, so there is nothing "
                "to add volumes to. Recover it first with a separate task "
                "(state: present), then expand it.",
            )
        return Decision("expand")

    # Not reachable: the argument spec allows exactly the three states above. Named
    # rather than left to fall off the end returning None, which is the failure mode
    # this whole table exists to remove.
    return Decision(
        "fail",
        f"purefa_workload does not handle state {state!r}. This is a bug in the "
        "module.",
    )


#: The only two actions that build volumes from a preset, and so the only two that
#: read one. Stated once, rather than restated as the conditions that route to them.
PRESET_ACTIONS = frozenset({"create", "expand"})


def _read_preset(module, array, fleet, action):
    """The preset the action will build from, or None where none is needed

    Every outcome other than a create or an expand works from the workload the array
    already has, so a task that names no preset is not incomplete. required_if cannot
    express that: whether a create is happening is only known once the workload has
    been looked up.

    Asking the action rather than restating the conditions that produced it also
    means a task missing both a preset and the workload reports the workload - the
    real problem - instead of demanding a preset it would then have nothing to use.
    """
    if action not in PRESET_ACTIONS:
        return None
    if not module.params["preset"]:
        module.fail_json(
            msg="preset required to create a new workload or to expand an "
            "existing one."
        )
    # Presets are fleet objects, and the API names them "<fleet>:<preset>", so
    # qualify it here rather than at the top of main(): it is meaningless on every
    # path that does not reach this function.
    module.params["preset"] = fleet + ":" + module.params["preset"]
    res = array.get_presets_workload(names=[module.params["preset"]])
    check_response(
        res,
        module,
        f"Preset {module.params['preset']} does not exist in fleet {fleet}",
    )
    return list(res.items)[0]


#: The actions that remove something. Which array they landed on is worth saying
#: whenever the task did not say it, because nothing else in the output will.
DESTRUCTIVE_ACTIONS = frozenset({"delete", "eradicate"})


def _warn_which_member_was_chosen(module, fleet, member, lookup, action):
    """Name the array a destructive action resolved to, when the task did not

    The copies-elsewhere warning cannot fire on a fleet-wide search - two matches
    were already refused as ambiguous, so exactly one member holds the name - and its
    wording ("only the one on X is affected") names a context the operator never
    wrote, which reads as confirmation of something they typed. What they lack is the
    one fact the search decided for them: which array is about to lose a workload.
    """
    if member is not SEARCH_WHOLE_FLEET or action not in DESTRUCTIVE_ACTIONS:
        return
    requested = _requested_member(module.params)
    scope = (
        f"context {requested} names fleet {fleet} rather than one of its members"
        if requested
        else "No context was named"
    )
    # A delete asked to eradicate does both, so say the one that cannot be undone
    removal = (
        "eradicated"
        if action == "eradicate" or module.params["eradicate"]
        else "destroyed"
    )
    module.warn(
        f"{scope}; workload {module.params['name']} was found on {lookup.member} and "
        f"that is what will be {removal}."
    )


#: Options only some actions read. An option a task sets that the action it
#: resolved to does not read is said rather than quietly dropped - being accepted
#: and silently doing nothing is what this module was reported for, in placement's
#: case. Said rather than refused, because a playbook may legitimately set one of
#: these once in module_defaults for a sibling task, as preset already is.
#:
#: Four options are deliberately absent. eradicate is refused outright where it
#: cannot apply, and _decide_action already has its own word for the one case where
#: it is accepted and ignored. host selects the action rather than being read by
#: one, so "host is ignored" means nothing anywhere except with rename, which is
#: refused. wait defaults to true, so listing it would warn on every rename anyone
#: ever runs.
#:
IGNORED_OPTIONS = (
    # (option, the one action that reads it, why none of the others do)
    ("volume_count", "expand", "only an expand adds volumes"),
    ("volume_configuration", "expand", "only an expand adds volumes"),
    ("parameters", "create", "preset parameters are applied only at creation"),
)


def _warn_about_ignored_options(module, action):
    """Say which of the options the task set this action does not read

    Asked after _decide_action rather than beside the refusals in
    _check_option_combinations, because none of it is answerable from the task
    alone: a create and a no-op are the same task until the workload has been
    looked up. That is also what lets each warning name the action the task turned
    out to be, rather than the state it asked for.
    """
    for option, read_by, why in IGNORED_OPTIONS:
        if not module.params[option] or action == read_by:
            continue
        module.warn(
            f"{option} is not applied: this task resolved to a {action} of "
            f"{module.params['name']}, and {why}."
        )


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(
                type="str",
                default="present",
                choices=["absent", "present", "expand"],
            ),
            preset=dict(type="str"),
            rename=dict(type="str"),
            eradicate=dict(type="bool", default=False),
            placement=dict(type="str"),
            parameters=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    value=dict(
                        type="dict",
                        required=True,
                        options=dict(
                            string=dict(type="str"),
                            integer=dict(type="int"),
                            boolean=dict(type="bool"),
                            resource_reference=dict(
                                type="dict",
                                options=dict(
                                    id=dict(type="str"),
                                    name=dict(type="str"),
                                    resource_type=dict(type="str"),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            volume_count=dict(type="int"),
            volume_configuration=dict(type="str"),
            recommendation=dict(type="bool", default=False),
            # No default, as for placement: omitting it means the fleet, and an
            # empty string is then distinguishable from an omission rather than
            # being the same request written two ways.
            context=dict(type="str", default=None),
            host=dict(type="str", default=""),
            # Deliberately not in purefa_argument_spec(), which would land these
            # on every module in the collection
            wait=dict(type="bool", default=True),
            wait_timeout=dict(type="int", default=300),
        )
    )

    required_if = [
        ["state", "expand", ["volume_count", "volume_configuration", "preset"]]
    ]

    module = AnsibleModule(
        argument_spec, supports_check_mode=True, required_if=required_if
    )

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    # Everything answerable from the task alone, before any API call
    _check_option_combinations(module)

    array = get_array(module)
    api_version = array.get_rest_version()
    if LooseVersion(MIN_REQUIRED_API_VERSION) > LooseVersion(api_version):
        module.fail_json(
            msg="FlashArray REST version not supported. "
            "Minimum version required: {0}".format(MIN_REQUIRED_API_VERSION)
        )
    fleet = _read_fleet_name(module, array)

    # Four questions, in order, each answering one thing and nothing else: are the
    # options coherent, which array do we address, what is there, what to do.
    member = _resolve_member_to_search(module, array, fleet)
    lookup = _look_up_workload(module, array, fleet, member)
    decision = _decide_action(module.params, member, lookup, fleet)

    if decision.action == "fail":
        module.fail_json(msg=decision.message)
    if decision.message:
        module.warn(decision.message)

    preset_config = _read_preset(module, array, fleet, decision.action)

    # One name on two arrays is this module's central hazard, so it is reported
    # wherever it is true - not only where this task is what makes it true. A create
    # says it in its own words, so it is left to say it. A rename asks twice: once
    # for the name it is leaving, once for the name it is taking.
    if decision.action != "create":
        _warn_about_copies_elsewhere(module, array, fleet, lookup)
    if decision.action == "rename":
        _warn_about_copies_elsewhere(
            module, array, fleet, lookup, name=module.params["rename"]
        )
    # The complement, for the one path where that warning cannot fire: which member
    # the search settled on, before anything is removed from it.
    _warn_which_member_was_chosen(module, fleet, member, lookup, decision.action)
    # And the options this action will not read. Only answerable now: which action
    # a state: present task is depends on what the lookup found.
    _warn_about_ignored_options(module, decision.action)

    # Every action except a create works on lookup.member - the array the workload
    # was actually found on. A create has nothing to have found, so it is the one arm
    # that asks the placement logic where to go. There is deliberately no shared
    # "context" variable falling back from one to the other: that fallback is itself a
    # placement decision, and it belongs in _choose_placement where it can be seen.
    if decision.action == "create":
        create_workload(
            module,
            array,
            _choose_placement(module, array, fleet, member, preset_config),
            preset_config,
            others=_copies_elsewhere(module, array, fleet, lookup),
        )
    elif decision.action == "expand":
        expand_workload(
            module,
            array,
            lookup.member,
            preset_config.volume_configurations,
            lookup.workload,
        )
    elif decision.action == "recover":
        recover_workload(module, array, lookup.member, lookup.workload)
    elif decision.action == "rename":
        rename_workload(module, array, lookup.member, lookup.workload)
    elif decision.action in ("connect", "disconnect"):
        connect_or_disconnect_volumes(
            module, array, lookup.member, decision.action, lookup.workload
        )
    elif decision.action == "delete":
        delete_workload(module, array, lookup.member, lookup.workload)
    elif decision.action == "eradicate":
        eradicate_workload(module, array, lookup.member)
    elif decision.action == "nothing":
        module.exit_json(
            changed=False,
            workload=_workload_facts(module, array, lookup.workload, lookup.member),
        )
    else:
        # Not reachable: _decide_action returns nothing else. Named rather than left
        # as a fall-through, so an action added there and not here fails loudly
        # instead of quietly reporting no change - which is exactly how the old chain
        # lost expand-on-a-destroyed-workload.
        module.fail_json(
            msg=f"purefa_workload has no handler for action {decision.action!r}. "
            "This is a bug in the module."
        )


if __name__ == "__main__":
    main()
