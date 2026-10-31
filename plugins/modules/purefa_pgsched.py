#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_pgsched
short_description: Manage protection groups replication schedules on Everpure FlashArrays
version_added: '1.0.0'
description:
- Modify or delete protection groups replication schedules on Everpure FlashArrays.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the protection group.
    type: str
    required: true
  state:
    description:
    - Define whether to set or delete the protection group schedule.
    type: str
    default: present
    choices: [ absent, present ]
  schedule:
    description:
    - Which schedule to change.
    type: str
    choices: ['replication', 'snapshot']
    required: true
  enabled:
    description:
    - Enable the schedule being configured.
    - When not specified the current enabled state is left unchanged.
    type: bool
  replicate_at:
    description:
    - Provide a time in 12-hour AM/PM format, eg. 11AM
    - Sent to the array as seconds since midnight, which is the unit the
      array stores and returns for the C(at) value.
    - Only valid if I(replicate_frequency) is an exact multiple of 86400, ie 1 day.
    - Set to an empty string "" to clear an existing at value (sends -1 to the API).
    - Automatically cleared when I(replicate_frequency) changes to a non-day multiple.
    type: str
  blackout_start:
    description:
    - Specifies the time at which to suspend replication.
    - Provide a time in 12-hour AM/PM format, eg. 11AM
    - Sent to the array as seconds since midnight.
    type: str
  blackout_end:
    description:
    - Specifies the time at which to restart replication.
    - Provide a time in 12-hour AM/PM format, eg. 5PM
    - Sent to the array as seconds since midnight.
    type: str
  replicate_frequency:
    description:
    - Specifies the replication frequency in seconds.
    - Converted to milliseconds for the array, which stores frequencies
      in milliseconds.
    - Range 900 - 34560000 (FA-405, //M10, //X10 and Cloud Block Store).
    - Range 300 - 34560000 (all other arrays).
    type: int
  snap_at:
    description:
    - Provide a time in 12-hour AM/PM format, eg. 11AM
    - Sent to the array as seconds since midnight, which is the unit the
      array stores and returns for the C(at) value.
    - Only valid if I(snap_frequency) is an exact multiple of 86400, ie 1 day.
    - Set to an empty string "" to clear an existing at value (sends -1 to the API).
    - Automatically cleared when I(snap_frequency) changes to a non-day multiple.
    type: str
  snap_frequency:
    description:
    - Specifies the snapshot frequency in seconds.
    - Converted to milliseconds for the array, which stores frequencies
      in milliseconds.
    - Range available 300 - 34560000.
    type: int
  days:
    description:
    - Specifies the number of days to keep the I(per_day) snapshots beyond the
      I(all_for) period before they are eradicated
    - Max retention period is 4000 days
    type: int
  all_for:
    description:
    - Specifies the length of time, in seconds, to keep the snapshots on the
      source array before they are eradicated.
    - Range available 1 - 34560000.
    type: int
  per_day:
    description:
    - Specifies the number of I(per_day) snapshots to keep beyond the I(all_for) period.
    - Maximum number is 1440
    type: int
  target_all_for:
    description:
    - Specifies the length of time, in seconds, to keep the replicated snapshots on the targets.
    - Range is 1 - 34560000 seconds.
    type: int
  target_per_day:
    description:
    - Specifies the number of I(per_day) replicated snapshots to keep beyond the I(target_all_for) period.
    - Maximum number is 1440
    type: int
  target_days:
    description:
    - Specifies the number of days to keep the I(target_per_day) replicated snapshots
      beyond the I(target_all_for) period before they are eradicated.
    - Max retention period is 4000 days
    type: int
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
    version_added: '1.33.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Update protection group snapshot schedule
  everpure.flasharray.purefa_pgsched:
    name: foo
    schedule: snapshot
    enabled: true
    snap_frequency: 86400
    snap_at: 3PM
    per_day: 5
    all_for: 5
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Update protection group replication schedule
  everpure.flasharray.purefa_pgsched:
    name: foo
    schedule: replication
    enabled: true
    replicate_frequency: 86400
    replicate_at: 3PM
    target_per_day: 5
    target_all_for: 5
    blackout_start: 2AM
    blackout_end: 5AM
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete protection group snapshot schedule
  everpure.flasharray.purefa_pgsched:
    name: foo
    schedule: snapshot
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete protection group replication schedule
  everpure.flasharray.purefa_pgsched:
    name: foo
    schedule: replication
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Clear snap_at value while keeping daily frequency
  everpure.flasharray.purefa_pgsched:
    name: foo
    schedule: snapshot
    snap_at: ""
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Clear replicate_at value while keeping daily frequency
  everpure.flasharray.purefa_pgsched:
    name: foo
    schedule: replication
    replicate_at: ""
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    get_with_context,
    check_response,
)

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        ProtectionGroup,
        ReplicationSchedule,
        SnapshotSchedule,
        RetentionPolicy,
        TimeWindow,
    )
except ImportError:
    HAS_PURESTORAGE = False


CONTEXT_API_VERSION = "2.38"


def get_pending_pgroup(module, array):
    """Get Protection Group"""
    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        destroyed=True,
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_pgroup(module, array):
    """Get Protection Group"""
    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def _convert_to_seconds(hour):
    """Convert a 12-hour clock value (e.g. 3PM) to seconds from midnight.

    Despite the SDK model documenting ``at`` in milliseconds, the array
    stores and returns ``snapshot_schedule.at``, ``replication_schedule.at``
    and the blackout window in seconds since midnight: ``at: 54000`` (3PM)
    is accepted and read back, ``at: 54000000`` is silently dropped. Only
    ``frequency`` is in milliseconds.
    """
    period = hour[-2:].upper()
    hour_value = int(hour[:-2])

    if period == "AM" and hour_value == 12:
        return 0
    if period == "AM":
        return hour_value * 3600
    if period == "PM" and hour_value == 12:
        return 43200
    return (hour_value + 12) * 3600


def update_schedule(module, array, snap_time, repl_time):
    """
    Update Protection Group Schedule for snapshots and replication.
    Immediately fail if any patch call returns an error.
    """
    changed = False

    # Fetch protection group
    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
    )
    groups = list(res.items) if res.status_code == 200 else []

    if not groups:
        module.fail_json(msg=f"Protection group {module.params['name']} not found")

    schedule = groups[0]

    # Ensure blackout exists
    if not hasattr(schedule.replication_schedule.blackout, "start"):
        schedule.replication_schedule.blackout = TimeWindow(start=0, end=0)

    # Current snapshot schedule
    current_snap = {
        "days": schedule.source_retention.days,
        "snap_frequency": schedule.snapshot_schedule.frequency,
        "snap_enabled": schedule.snapshot_schedule.enabled,
        "snap_at": getattr(schedule.snapshot_schedule, "at", None),
        "per_day": schedule.source_retention.per_day,
        "all_for": schedule.source_retention.all_for_sec,
    }

    # Current replication schedule
    current_repl = {
        "replicate_frequency": schedule.replication_schedule.frequency,
        "replicate_enabled": schedule.replication_schedule.enabled,
        "replicate_at": getattr(schedule.replication_schedule, "at", None),
        "target_days": schedule.target_retention.days,
        "target_per_day": schedule.target_retention.per_day,
        "target_all_for": schedule.target_retention.all_for_sec,
        "blackout_start": schedule.replication_schedule.blackout.start,
        "blackout_end": schedule.replication_schedule.blackout.end,
    }

    # Snapshot schedule
    if module.params["schedule"] == "snapshot":
        snap_enabled = (
            current_snap["snap_enabled"]
            if module.params.get("enabled") is None
            else module.params["enabled"]
        )
        snap_frequency = (
            module.params["snap_frequency"] * 1000
            if module.params.get("snap_frequency") is not None
            else current_snap["snap_frequency"]
        )
        # Determine snap_at value:
        # - Empty string "" means explicitly clear the at value
        # - Non-day frequency means at value must be cleared
        # - Valid time string means set to that time
        # - None (not provided) means keep current value
        freq_is_days = snap_frequency % 86400000 == 0
        if module.params.get("snap_at") == "":
            # Explicit clear request
            snap_at = None
        elif not freq_is_days:
            # Non-day frequency - at value must be cleared
            snap_at = None
        elif module.params.get("snap_at"):
            # New value provided
            snap_at = _convert_to_seconds(module.params["snap_at"].upper())
        else:
            # No change - keep current
            snap_at = current_snap["snap_at"]
        days = (
            current_snap["days"]
            if module.params.get("days") is None
            else module.params["days"]
        )
        per_day = (
            current_snap["per_day"]
            if module.params.get("per_day") is None
            else module.params["per_day"]
        )
        all_for = (
            current_snap["all_for"]
            if module.params.get("all_for") is None
            else module.params["all_for"]
        )

        snap_schedule_changed = (
            snap_frequency != current_snap["snap_frequency"]
            or snap_at != current_snap["snap_at"]
        )

        # Patch frequency and at together, never with enabled: a body that
        # carries enabled applies only enabled and silently ignores the
        # frequency and at sent with it (verified on Purity 6.10.6)
        if snap_schedule_changed:
            changed = True
            if freq_is_days and snap_at is not None:
                # Day frequency with at value set
                schedule = SnapshotSchedule(frequency=snap_frequency, at=snap_at)
            else:
                # Non-day frequency, or clearing at value (snap_at is None)
                # Send at=-1 to clear the value on the array
                schedule = SnapshotSchedule(frequency=snap_frequency, at=-1)
            res = get_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(snapshot_schedule=schedule),
            )
            check_response(
                res,
                module,
                f"Failed to update snap_frequency/at for pgroup {module.params['name']}",
            )

        # Patch enabled on its own, for the same reason
        if snap_enabled != current_snap["snap_enabled"]:
            changed = True
            res = get_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    snapshot_schedule=SnapshotSchedule(enabled=snap_enabled)
                ),
            )
            check_response(
                res,
                module,
                f"Failed to update snap_enabled for pgroup {module.params['name']}",
            )

        # Patch retention separately
        if (
            days != current_snap["days"]
            or per_day != current_snap["per_day"]
            or all_for != current_snap["all_for"]
        ):
            changed = True
            res = get_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    source_retention=RetentionPolicy(
                        days=days, per_day=per_day, all_for_sec=all_for
                    )
                ),
            )
            check_response(
                res,
                module,
                f"Failed to update snapshot retention for pgroup {module.params['name']}",
            )

    # Replication schedule
    else:
        replicate_enabled = (
            current_repl["replicate_enabled"]
            if module.params.get("enabled") is None
            else module.params["enabled"]
        )
        replicate_frequency = (
            module.params["replicate_frequency"] * 1000
            if module.params.get("replicate_frequency") is not None
            else current_repl["replicate_frequency"]
        )
        # Determine replicate_at value:
        # - Empty string "" means explicitly clear the at value
        # - Non-day frequency means at value must be cleared
        # - Valid time string means set to that time
        # - None (not provided) means keep current value
        freq_is_days = replicate_frequency % 86400000 == 0
        if module.params.get("replicate_at") == "":
            # Explicit clear request
            replicate_at = None
        elif not freq_is_days:
            # Non-day frequency - at value must be cleared
            replicate_at = None
        elif module.params.get("replicate_at"):
            # New value provided
            replicate_at = _convert_to_seconds(module.params["replicate_at"].upper())
        else:
            # No change - keep current
            replicate_at = current_repl["replicate_at"]
        target_days = (
            current_repl["target_days"]
            if module.params.get("target_days") is None
            else module.params["target_days"]
        )
        target_per_day = (
            current_repl["target_per_day"]
            if module.params.get("target_per_day") is None
            else module.params["target_per_day"]
        )
        target_all_for = (
            current_repl["target_all_for"]
            if module.params.get("target_all_for") is None
            else module.params["target_all_for"]
        )
        blackout_start = (
            current_repl["blackout_start"]
            if module.params.get("blackout_start") is None
            else _convert_to_seconds(module.params["blackout_start"].upper())
        )
        blackout_end = (
            current_repl["blackout_end"]
            if module.params.get("blackout_end") is None
            else _convert_to_seconds(module.params["blackout_end"].upper())
        )

        repl_schedule_changed = (
            replicate_frequency != current_repl["replicate_frequency"]
            or replicate_at != current_repl["replicate_at"]
        )

        # Patch frequency and at together, never with enabled: a body that
        # carries enabled applies only enabled and silently ignores the
        # frequency and at sent with it (verified on Purity 6.10.6)
        if repl_schedule_changed:
            changed = True
            if freq_is_days and replicate_at is not None:
                # Day frequency with at value set
                schedule = ReplicationSchedule(
                    frequency=replicate_frequency, at=replicate_at
                )
            else:
                # Non-day frequency, or clearing at value (replicate_at is None)
                # Send at=-1 to clear the value on the array
                schedule = ReplicationSchedule(frequency=replicate_frequency, at=-1)
            res = get_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(replication_schedule=schedule),
            )
            check_response(
                res,
                module,
                f"Failed to update replicate_frequency/at for pgroup {module.params['name']}",
            )

        # Patch enabled on its own, for the same reason
        if replicate_enabled != current_repl["replicate_enabled"]:
            changed = True
            res = get_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    replication_schedule=ReplicationSchedule(enabled=replicate_enabled)
                ),
            )
            check_response(
                res,
                module,
                f"Failed to update replicate_enabled for pgroup {module.params['name']}",
            )

        # Patch blackout separately
        if (
            blackout_start != current_repl["blackout_start"]
            or blackout_end != current_repl["blackout_end"]
        ):
            changed = True
            res = get_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    replication_schedule=ReplicationSchedule(
                        blackout=TimeWindow(start=blackout_start, end=blackout_end)
                    )
                ),
            )
            check_response(
                res,
                module,
                f"Failed to update blackout window for pgroup {module.params['name']}",
            )

        # Patch target retention separately
        if (
            target_days != current_repl["target_days"]
            or target_per_day != current_repl["target_per_day"]
            or target_all_for != current_repl["target_all_for"]
        ):
            changed = True
            res = get_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    target_retention=RetentionPolicy(
                        days=target_days,
                        per_day=target_per_day,
                        all_for_sec=target_all_for,
                    )
                ),
            )
            check_response(
                res,
                module,
                f"Failed to update replication retention for pgroup {module.params['name']}",
            )

    module.exit_json(changed=changed)


def _patch_schedule(module, array, schedule, failure):
    """PATCH one schedule body and fail the module if the array refuses it"""
    res = get_with_context(
        array,
        "patch_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        protection_group=ProtectionGroup(**schedule),
    )
    check_response(res, module, failure)


def delete_schedule(module, array):
    """Delete, ie. disable, Protection Group Schedules

    The reset is sent as separate PATCH bodies: a body carrying ``enabled``
    applies only ``enabled`` and silently ignores everything sent with it.
    """
    changed = False

    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
    )
    schedule = list(res.items)[0]
    reset_failed = (
        f"Resetting pgroup {module.params['name']} {module.params['schedule']} schedule"
    )

    if module.params["schedule"] == "replication":
        if schedule.replication_schedule.enabled:
            changed = True
            if not module.check_mode:
                # Reset blackout window, then frequency (clearing at), then
                # disable, each on its own
                _patch_schedule(
                    module,
                    array,
                    dict(
                        replication_schedule=ReplicationSchedule(
                            blackout=TimeWindow(start=0, end=0)
                        )
                    ),
                    reset_failed,
                )
                _patch_schedule(
                    module,
                    array,
                    dict(
                        replication_schedule=ReplicationSchedule(
                            frequency=14400000, at=-1
                        )
                    ),
                    reset_failed,
                )
                _patch_schedule(
                    module,
                    array,
                    dict(replication_schedule=ReplicationSchedule(enabled=False)),
                    reset_failed,
                )
                # Reset target retention
                res = get_with_context(
                    array,
                    "patch_protection_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    protection_group=ProtectionGroup(
                        target_retention=RetentionPolicy(
                            all_for_sec=1,
                            per_day=0,
                            days=0,
                        ),
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Deleting pgroup {module.params['name']} {module.params['schedule']} schedule",
                )
    else:
        if schedule.snapshot_schedule.enabled:
            changed = True
            if not module.check_mode:
                # Reset frequency (clearing at), then disable, each on its own
                _patch_schedule(
                    module,
                    array,
                    dict(snapshot_schedule=SnapshotSchedule(frequency=300000, at=-1)),
                    reset_failed,
                )
                _patch_schedule(
                    module,
                    array,
                    dict(snapshot_schedule=SnapshotSchedule(enabled=False)),
                    reset_failed,
                )
                # Reset source retention
                res = get_with_context(
                    array,
                    "patch_protection_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    protection_group=ProtectionGroup(
                        source_retention=RetentionPolicy(
                            all_for_sec=1,
                            per_day=0,
                            days=0,
                        ),
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Deleting pgroup {module.params['name']} {module.params['schedule']} schedule",
                )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            schedule=dict(
                type="str", required=True, choices=["replication", "snapshot"]
            ),
            blackout_start=dict(type="str"),
            blackout_end=dict(type="str"),
            snap_at=dict(type="str"),
            replicate_at=dict(type="str"),
            replicate_frequency=dict(type="int"),
            snap_frequency=dict(type="int"),
            all_for=dict(type="int"),
            days=dict(type="int"),
            per_day=dict(type="int"),
            target_all_for=dict(type="int"),
            target_per_day=dict(type="int"),
            target_days=dict(type="int"),
            enabled=dict(type="bool"),
            context=dict(type="str", default=""),
        )
    )

    required_together = [["blackout_start", "blackout_end"]]

    module = AnsibleModule(
        argument_spec, required_together=required_together, supports_check_mode=True
    )

    state = module.params["state"]
    array = get_array(module)

    pgroup = get_pgroup(module, array)
    repl_time = False
    if module.params["replicate_at"] and module.params["replicate_frequency"]:
        if not module.params["replicate_frequency"] % 86400 == 0:
            module.fail_json(
                msg="replicate_at not valid unless replicate frequency is measured in days, ie. a multiple of 86400"
            )
        repl_time = True
    snap_time = False
    if module.params["snap_at"] and module.params["snap_frequency"]:
        if not module.params["snap_frequency"] % 86400 == 0:
            module.fail_json(
                msg="snap_at not valid unless snapshot frequency is measured in days, ie. a multiple of 86400"
            )
        snap_time = True
    if pgroup and state == "present":
        update_schedule(module, array, snap_time, repl_time)
    elif pgroup and state == "absent":
        delete_schedule(module, array)
    elif pgroup is None:
        module.fail_json(
            msg="Specified protection group {0} does not exist.".format(
                module.params["name"]
            )
        )


if __name__ == "__main__":
    main()
