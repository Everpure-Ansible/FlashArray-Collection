#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_pgsnap
version_added: '1.0.0'
short_description: Manage protection group snapshots on Everpure FlashArrays
description:
- Create or delete protection group snapshots on Everpure FlashArray.
- Recovery of replicated snapshots on the replica target array is enabled.
- Support for ActiveCluster and Volume Group protection groups is supported.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the source protection group.
    type: str
    required: true
  suffix:
    description:
    - Suffix of snapshot name.
    - Special case. If I(latest) the module will select the latest snapshot created in the group
    type: str
  state:
    description:
    - Define whether the protection group snapshot should exist or not.
      Copy (added in 2.7) will create a full read/write clone of the
      snapshot.
    type: str
    choices: [ absent, present, copy, rename ]
    default: present
  eradicate:
    description:
    - Define whether to eradicate the snapshot on delete or leave in trash.
    type: bool
    default: false
  restore:
    description:
    - Restore a specific volume from a protection group snapshot, or use C(all)
      to restore all member volumes at once.
    - The protection group name is not required. Only provide the name of the
      volume to be restored, or C(all) to restore all volumes.
    - When using C(all), if restoring to an existing protection group the
      I(overwrite) parameter must be set to C(true).
    - When using C(all), the I(target) parameter can specify a new or existing
      protection group name. If not specified, it defaults to the source
      protection group name.
    type: str
  overwrite:
    description:
    - Define whether to overwrite the target volume if it already exists.
    - Required when I(restore=all) and restoring to an existing protection group.
    type: bool
    default: false
  target:
    description:
    - Volume to restore a specified volume to.
    - If not supplied this will default to the volume defined in I(restore)
    - Name of new snapshot suffix if renaming a snapshot
    - When I(restore=all), this specifies the target protection group name.
      If not supplied, defaults to the source protection group name.
    type: str
  offload:
    description:
    - Name of offload target on which the snapshot exists.
    - This is only applicable for deletion and erasure of snapshots
    type: str
  now:
    description:
    - Whether to initiate a snapshot of the protection group immediately
    type: bool
    default: false
  apply_retention:
    description:
    - Apply retention schedule settings to the snapshot
    type: bool
    default: false
  remote:
    description:
    - Force immediate snapshot to remote targets
    type: bool
    default: false
  throttle:
    description:
    - If set to true, allows snapshot to fail if array health is not optimal.
    type: bool
    default: false
    version_added: '1.21.0'
  with_default_protection:
    description:
    - Whether to add the default container protection groups to
      those specified in I(add_to_pgs) as the initial protection
      of a volume created from a snapshot.
    type: bool
    default: true
    version_added: '1.27.0'
  add_to_pgs:
    description:
    - A volume created from a snapshot will be added to the specified
      protection groups
    type: list
    elements: str
    version_added: '1.27.0'
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
- name: Create protection group snapshot foo.ansible
  everpure.flasharray.purefa_pgsnap:
    name: foo
    suffix: ansible
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Delete and eradicate protection group snapshot named foo.snap
  everpure.flasharray.purefa_pgsnap:
    name: foo
    suffix: snap
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Restore volume data from local protection group snapshot named foo.snap to volume data2
  everpure.flasharray.purefa_pgsnap:
    name: foo
    suffix: snap
    restore: data
    target: data2
    overwrite: true
    with_default_protection: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: copy

- name: Restore remote protection group snapshot arrayA:pgname.snap.data to local copy
  everpure.flasharray.purefa_pgsnap:
    name: arrayA:pgname
    suffix: snap
    restore: data
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: copy

- name: Restore AC pod  protection group snapshot pod1::pgname.snap.data to pod1::data2
  everpure.flasharray.purefa_pgsnap:
    name: pod1::pgname
    suffix: snap
    restore: data
    target: pod1::data2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: copy

- name: Create snapshot of existing pgroup foo with suffix and force immediate copy to remote targets
  everpure.flasharray.purefa_pgsnap:
    name: pgname
    suffix: force
    now: true
    apply_retention: true
    remote: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete and eradicate snapshot named foo.snap on offload target bar from arrayA
  everpure.flasharray.purefa_pgsnap:
    name: "arrayA:foo"
    suffix: snap
    offload: bar
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Rename protection group snapshot foo.fred to foo.dave
  everpure.flasharray.purefa_pgsnap:
    name: foo
    suffix: fred
    target: dave
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: rename

- name: Restore all volumes from protection group snapshot foo.snap (overwrite existing)
  everpure.flasharray.purefa_pgsnap:
    name: foo
    suffix: snap
    restore: all
    overwrite: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: copy

- name: Clone all volumes from protection group snapshot foo.snap to new protection group foo_clone
  everpure.flasharray.purefa_pgsnap:
    name: foo
    suffix: snap
    restore: all
    target: foo_clone
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: copy
"""

RETURN = r"""
suffix:
    description: Suffix of the protection group snapshot that was created.
    type: str
    returned: when I(state=present), including check mode
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        ProtectionGroupSnapshot,
        ProtectionGroupSnapshotPatch,
        VolumePost,
        Reference,
        DestroyedPatchPost,
    )
except ImportError:
    HAS_PURESTORAGE = False

import re
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
    get_with_context,
    post_with_context,
    patch_with_context,
    delete_with_context,
)

from datetime import datetime

THROTTLE_API = "2.25"
DEFAULT_API = "2.16"
CONTEXT_API_VERSION = "2.38"


def _check_offload(module, array):
    res = get_with_context(
        array,
        "get_offloads",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["offload"]],
    )
    if res.status_code == 200:
        return bool(list(res.items)[0].status == "connected")
    return False


def get_pgroup(module, array):
    """Return Protection Group"""
    return bool(
        get_with_context(
            array,
            "get_protection_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        ).status_code
        == 200
    )


def get_pgroupvolume(module, array):
    """Return Protection Group Volume or None"""
    try:
        volumes = []
        pgroup = list(
            get_with_context(
                array,
                "get_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
            ).items
        )[0]
        if pgroup.host_count > 0:  # We have a host PG
            host_dict = list(
                get_with_context(
                    array,
                    "get_protection_groups_hosts",
                    CONTEXT_API_VERSION,
                    module,
                    group_names=[module.params["name"]],
                ).items
            )
            for host in host_dict:
                hostvols = list(
                    get_with_context(
                        array,
                        "get_connections",
                        CONTEXT_API_VERSION,
                        module,
                        host_names=[host.member.name],
                    ).items
                )
                for hvol in hostvols:
                    volumes.append(hvol.volume.name)
        elif pgroup.host_group_count > 0:  # We have a hostgroup PG
            hgroup_dict = list(
                get_with_context(
                    array,
                    "get_protection_groups_host_groups",
                    CONTEXT_API_VERSION,
                    module,
                    group_names=[module.params["name"]],
                ).items
            )
            # First check if there are any volumes in the host groups
            for hgentry in hgroup_dict:
                hgvols = list(
                    get_with_context(
                        array,
                        "get_connections",
                        CONTEXT_API_VERSION,
                        module,
                        host_group_names=[hgentry.member.name],
                    ).items
                )
                for hgvol in hgvols:
                    volumes.append(hgvol.volume.name)
            # Second check for host specific volumes
            for hgroup in hgroup_dict:
                hg_hosts = list(
                    get_with_context(
                        array,
                        "get_host_groups_hosts",
                        CONTEXT_API_VERSION,
                        module,
                        group_names=[hgroup.member.name],
                    ).items
                )
                for hg_host in hg_hosts:
                    host_vols = list(
                        get_with_context(
                            array,
                            "get_connections",
                            CONTEXT_API_VERSION,
                            module,
                            host_names=[hg_host.member.name],
                        ).items
                    )
                    for host_vol in host_vols:
                        volumes.append(host_vol.volume.name)
        else:  # We have a volume PG
            vol_dict = list(
                get_with_context(
                    array,
                    "get_protection_groups_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    group_names=[module.params["name"]],
                ).items
            )
            for entry in vol_dict:
                volumes.append(entry.member.name)
        volumes = list(set(volumes))
        if "::" in module.params["name"]:
            restore_volume = (
                "::".join(module.params["name"].split("::")[:-1])
                + "::"
                + module.params["restore"]
            )
        else:
            restore_volume = module.params["restore"]
        for volume in volumes:
            if volume == restore_volume:
                return volume
    except Exception:
        return None


def get_rpgsnapshot(module, array):
    """Return Replicated Snapshot or None"""
    snapname = (
        module.params["name"]
        + "."
        + module.params["suffix"]
        + "."
        + module.params["restore"]
    )
    res = get_with_context(
        array,
        "get_volume_snapshots",
        CONTEXT_API_VERSION,
        module,
        names=[snapname],
    )
    if res.status_code == 200:
        return snapname
    return None


def get_pgsnapshot(module, array):
    """Return Snapshot (active or deleted) or None"""
    snapname = module.params["name"] + "." + module.params["suffix"]
    res = get_with_context(
        array,
        "get_protection_group_snapshots",
        CONTEXT_API_VERSION,
        module,
        names=[snapname],
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def create_pgsnapshot(module, array):
    """Create Protection Group Snapshot"""
    api_version = array.get_rest_version()
    snap_data = None
    changed = True
    if not module.check_mode:
        suffix = ProtectionGroupSnapshot(suffix=module.params["suffix"])
        if LooseVersion(THROTTLE_API) >= LooseVersion(api_version):
            if (
                list(array.get_protection_groups(names=[module.params["name"]]).items)[
                    0
                ].target_count
                > 0
            ):
                if module.params["now"]:
                    res = array.post_protection_group_snapshots(
                        source_names=[module.params["name"]],
                        apply_retention=module.params["apply_retention"],
                        replicate_now=True,
                        protection_group_snapshot=suffix,
                    )
                else:
                    res = array.post_protection_group_snapshots(
                        source_names=[module.params["name"]],
                        apply_retention=module.params["apply_retention"],
                        protection_group_snapshot=suffix,
                        replicate=module.params["remote"],
                    )
            else:
                res = array.post_protection_group_snapshots(
                    source_names=[module.params["name"]],
                    apply_retention=module.params["apply_retention"],
                    protection_group_snapshot=suffix,
                )
        else:
            remote_target = (
                list(
                    get_with_context(
                        array,
                        "get_protection_groups",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["name"]],
                    ).items
                )[0].target_count
                > 0
            )
            if remote_target:
                if module.params["now"]:
                    res = post_with_context(
                        array,
                        "post_protection_group_snapshots",
                        CONTEXT_API_VERSION,
                        module,
                        source_names=[module.params["name"]],
                        apply_retention=module.params["apply_retention"],
                        replicate_now=True,
                        allow_throttle=module.params["throttle"],
                        protection_group_snapshot=suffix,
                    )
                else:
                    res = post_with_context(
                        array,
                        "post_protection_group_snapshots",
                        CONTEXT_API_VERSION,
                        module,
                        source_names=[module.params["name"]],
                        apply_retention=module.params["apply_retention"],
                        allow_throttle=module.params["throttle"],
                        protection_group_snapshot=suffix,
                        replicate=module.params["remote"],
                    )
            else:
                res = post_with_context(
                    array,
                    "post_protection_group_snapshots",
                    CONTEXT_API_VERSION,
                    module,
                    source_names=[module.params["name"]],
                    apply_retention=module.params["apply_retention"],
                    allow_throttle=module.params["throttle"],
                    protection_group_snapshot=suffix,
                )

        check_response(res, module, f"Snapshot of pgroup {module.params['name']}")
        snap_data = list(res.items)[0]
    module.exit_json(
        changed=changed,
        # In check mode nothing was created, so report the requested suffix
        suffix=snap_data.suffix if snap_data is not None else module.params["suffix"],
    )


def restore_pgsnapvolume(module, array):
    """Restore a Protection Group Snapshot Volume"""
    api_version = array.get_rest_version()
    changed = True
    if module.params["suffix"] == "latest":
        latest_snapshot = list(
            get_with_context(
                array,
                "get_protection_group_snapshots",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
            ).items
        )[-1].suffix
        module.params["suffix"] = latest_snapshot
    if ":" in module.params["name"] and "::" not in module.params["name"]:
        if get_rpgsnapshot(module, array) is None:
            module.fail_json(
                msg="Selected restore snapshot {0} does not exist in the Protection Group".format(
                    module.params["restore"]
                )
            )
    else:
        if get_pgroupvolume(module, array) is None:
            module.fail_json(
                msg="Selected restore volume {0} does not exist in the Protection Group".format(
                    module.params["restore"]
                )
            )
    source_volume = (
        module.params["name"]
        + "."
        + module.params["suffix"]
        + "."
        + module.params["restore"]
    )
    if "::" in module.params["target"]:
        target_pod_name = module.params["target"].split(":")[0]
        if "::" in module.params["name"]:
            source_pod_name = module.params["name"].split(":")[0]
        else:
            source_pod_name = ""
        if source_pod_name != target_pod_name:
            if (
                list(
                    get_with_context(
                        array,
                        "get_pods",
                        CONTEXT_API_VERSION,
                        module,
                        names=[target_pod_name],
                    ).items
                )[0].array_count
                > 1
            ):
                module.fail_json(msg="Volume cannot be restored to a stretched pod")
    if not module.check_mode:
        if LooseVersion(DEFAULT_API) <= LooseVersion(array.get_rest_version()):
            if module.params["add_to_pgs"]:
                # Reference objects without an id crash inside the SDK
                # (_process_references reads ref.id, which raises
                # AttributeError), so pass the protection group names
                # straight to the add_to_protection_group_names parameter
                res = post_with_context(
                    array,
                    "post_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["target"]],
                    volume=VolumePost(source=Reference(name=source_volume)),
                    with_default_protection=module.params["with_default_protection"],
                    add_to_protection_group_names=module.params["add_to_pgs"],
                )
            else:
                if module.params["overwrite"]:
                    # Overwrite path is identical across versions apart from
                    # context; the helper adds context_names only when set.
                    res = post_with_context(
                        array,
                        "post_volumes",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["target"]],
                        volume=VolumePost(source=Reference(name=source_volume)),
                        overwrite=module.params["overwrite"],
                    )
                elif LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version):
                    res = post_with_context(
                        array,
                        "post_volumes",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["target"]],
                        volume=VolumePost(source=Reference(name=source_volume)),
                        overwrite=module.params["overwrite"],
                        with_default_protection=module.params[
                            "with_default_protection"
                        ],
                    )
                else:
                    res = array.post_volumes(
                        names=[module.params["target"]],
                        volume=VolumePost(source=Reference(name=source_volume)),
                        with_default_protection=module.params[
                            "with_default_protection"
                        ],
                    )
        else:
            res = array.post_volumes(
                names=[module.params["target"]],
                overwrite=module.params["overwrite"],
                volume=VolumePost(source=Reference(name=source_volume)),
            )
        check_response(
            res,
            module,
            f"Failed to restore {module.params['restore']} from pgroup {module.params['name']}",
        )
    module.exit_json(changed=changed)


def restore_pgsnapshot_all(module, array):
    """Restore all volumes from a Protection Group Snapshot"""
    changed = True

    # Handle 'latest' suffix
    if module.params["suffix"] == "latest":
        latest_snapshot = list(
            get_with_context(
                array,
                "get_protection_group_snapshots",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
            ).items
        )[-1].suffix
        module.params["suffix"] = latest_snapshot

    # Source is the pgroup snapshot: pgname.suffix
    source_snapshot = module.params["name"] + "." + module.params["suffix"]

    # Target defaults to original protection group if not specified
    if module.params["target"]:
        target_pgroup = module.params["target"]
    else:
        target_pgroup = module.params["name"]

    # Check if target protection group exists
    target_exists = False
    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[target_pgroup],
    )
    if res.status_code == 200:
        items = list(res.items)
        if items:
            target_exists = True

    # Validate: overwrite required if target exists
    if target_exists and not module.params["overwrite"]:
        module.fail_json(
            msg="overwrite must be True when restoring to existing protection group '{0}'".format(
                target_pgroup
            )
        )

    if not module.check_mode:
        res = post_with_context(
            array,
            "post_protection_groups",
            CONTEXT_API_VERSION,
            module,
            names=[target_pgroup],
            source_names=[source_snapshot],
            overwrite=module.params["overwrite"],
        )
        check_response(
            res,
            module,
            f"Failed to restore all volumes from pgroup snapshot {source_snapshot}",
        )
    module.exit_json(changed=changed)


def delete_offload_snapshot(module, array):
    """Delete Offloaded Protection Group Snapshot"""
    changed = False
    snapname = module.params["name"] + "." + module.params["suffix"]
    if ":" in module.params["name"] and module.params["offload"]:
        if _check_offload(module, array):
            res = get_with_context(
                array,
                "get_remote_protection_group_snapshots",
                CONTEXT_API_VERSION,
                module,
                names=[snapname],
                on=module.params["offload"],
            )
            check_response(
                res,
                module,
                f"Offload snapshot {snapname} does not exist on {module.params['offload']}",
            )

            rpg_destroyed = list(res.items)[0].destroyed
            if not module.check_mode:
                if not rpg_destroyed:
                    changed = True
                    res = patch_with_context(
                        array,
                        "patch_remote_protection_group_snapshots",
                        CONTEXT_API_VERSION,
                        module,
                        names=[snapname],
                        on=module.params["offload"],
                        remote_protection_group_snapshot=DestroyedPatchPost(
                            destroyed=True
                        ),
                    )
                    check_response(
                        res,
                        module,
                        f"Failed to delete offloaded snapshot {snapname} on target {module.params['offload']}",
                    )
                    if module.params["eradicate"]:
                        res = delete_with_context(
                            array,
                            "delete_remote_protection_group_snapshots",
                            CONTEXT_API_VERSION,
                            module,
                            names=[snapname],
                            on=module.params["offload"],
                        )
                        check_response(
                            res,
                            module,
                            f"Failed to eradicate offloaded snapshot {snapname} on target {module.params['offload']}",
                        )
                else:
                    if module.params["eradicate"]:
                        changed = True
                        res = delete_with_context(
                            array,
                            "delete_remote_protection_group_snapshots",
                            CONTEXT_API_VERSION,
                            module,
                            names=[snapname],
                            on=module.params["offload"],
                        )
                        check_response(
                            res,
                            module,
                            f"Failed to eradicate offloaded snapshot {snapname} on target {module.params['offload']}",
                        )
        else:
            module.fail_json(
                msg="Offload target {0} does not exist or not connected".format(
                    module.params["offload"]
                )
            )
    else:
        module.fail_json(msg="Protection Group name not in the correct format")

    module.exit_json(changed=changed)


def delete_pgsnapshot(module, array):
    """Delete Protection Group Snapshot"""
    changed = True
    if not module.check_mode:
        snapname = module.params["name"] + "." + module.params["suffix"]
        res = patch_with_context(
            array,
            "patch_protection_group_snapshots",
            CONTEXT_API_VERSION,
            module,
            names=[snapname],
            protection_group_snapshot=ProtectionGroupSnapshotPatch(destroyed=True),
        )
        check_response(res, module, f"Failed to delete pgroup {snapname}")
        if module.params["eradicate"]:
            res = delete_with_context(
                array,
                "delete_protection_group_snapshots",
                CONTEXT_API_VERSION,
                module,
                names=[snapname],
            )
            check_response(res, module, f"Failed to delete pgroup {snapname}")
    module.exit_json(changed=changed)


def eradicate_pgsnapshot(module, array):
    """Eradicate Protection Group Snapshot"""
    changed = True
    if not module.check_mode:
        snapname = module.params["name"] + "." + module.params["suffix"]
        res = delete_with_context(
            array,
            "delete_protection_group_snapshots",
            CONTEXT_API_VERSION,
            module,
            names=[snapname],
        )
        check_response(res, module, f"Failed to delete pgroup {snapname}")
    module.exit_json(changed=changed)


def update_pgsnapshot(module, array):
    """Update Protection Group Snapshot - basically just rename..."""
    changed = True
    if not module.check_mode:
        current_name = module.params["name"] + "." + module.params["suffix"]
        new_name = module.params["name"] + "." + module.params["target"]
        res = patch_with_context(
            array,
            "patch_protection_group_snapshots",
            CONTEXT_API_VERSION,
            module,
            names=[current_name],
            protection_group_snapshot=ProtectionGroupSnapshotPatch(name=new_name),
        )
        check_response(res, module, f"Failed to rename {current_name} to {new_name}")
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            suffix=dict(type="str"),
            restore=dict(type="str"),
            offload=dict(type="str"),
            throttle=dict(type="bool", default=False),
            overwrite=dict(type="bool", default=False),
            target=dict(type="str"),
            eradicate=dict(type="bool", default=False),
            now=dict(type="bool", default=False),
            apply_retention=dict(type="bool", default=False),
            remote=dict(type="bool", default=False),
            state=dict(
                type="str",
                default="present",
                choices=["absent", "present", "copy", "rename"],
            ),
            with_default_protection=dict(type="bool", default=True),
            add_to_pgs=dict(type="list", elements="str"),
            context=dict(type="str", default=""),
        )
    )

    required_if = [("state", "copy", ["suffix", "restore"])]
    mutually_exclusive = [
        ["now", "remote"],
    ]

    module = AnsibleModule(
        argument_spec,
        required_if=required_if,
        mutually_exclusive=mutually_exclusive,
        supports_check_mode=True,
    )
    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is not installed")
    state = module.params["state"]
    pattern = re.compile("^(?=.*[a-zA-Z-])[a-zA-Z0-9]([a-zA-Z0-9-]{0,63}[a-zA-Z0-9])?$")
    if state == "present":
        if module.params["suffix"] is None:
            suffix = "snap-" + str(
                (datetime.utcnow() - datetime(1970, 1, 1, 0, 0, 0, 0)).total_seconds()
            )
            module.params["suffix"] = suffix.replace(".", "")
        else:
            if module.params["restore"]:
                pattern = re.compile(
                    "^[0-9]{0,63}$|^(?=.*[a-zA-Z-])[a-zA-Z0-9]([a-zA-Z0-9-]{0,63}[a-zA-Z0-9])?$"
                )
            if not pattern.match(module.params["suffix"]):
                module.fail_json(
                    msg="Suffix name {0} does not conform to suffix name rules".format(
                        module.params["suffix"]
                    )
                )

    # For single volume restore, default target to restore volume name
    # For restore=all, target defaults to source pgroup name (handled in function)
    if (
        not module.params["target"]
        and module.params["restore"]
        and module.params["restore"] != "all"
    ):
        module.params["target"] = module.params["restore"]

    if state == "rename" and module.params["target"] is not None:
        if not pattern.match(module.params["target"]):
            module.fail_json(
                msg="Suffix target {0} does not conform to suffix name rules".format(
                    module.params["target"]
                )
            )
    array = get_array(module)
    api_version = array.get_rest_version()

    # If context is empty and API supports context, set it to current array name
    if not module.params["context"] and LooseVersion(
        CONTEXT_API_VERSION
    ) <= LooseVersion(api_version):
        fleet_res = array.get_fleets()
        if fleet_res.status_code == 200 and list(fleet_res.items):
            module.params["context"] = list(array.get_arrays().items)[0].name

    pgroup = get_pgroup(module, array)
    if not pgroup:
        if state == "absent" and not module.params["offload"]:
            # A local snapshot cannot outlive its protection group, so the
            # snapshot is already absent. Offloaded snapshots can, so those
            # still need the group to be addressable.
            module.exit_json(changed=False)
        else:
            module.fail_json(
                msg="Protection Group {0} does not exist.".format(module.params["name"])
            )
    pgsnap = get_pgsnapshot(module, array)
    if pgsnap:
        pgsnap_deleted = pgsnap.destroyed
    if state != "absent" and module.params["offload"]:
        module.fail_json(
            msg="offload parameter not supported for state {0}".format(state)
        )
    elif state == "copy":
        if module.params["restore"] == "all":
            # Restore all volumes from pgroup snapshot
            # add_to_pgs and with_default_protection are not supported by post_protection_groups()
            if (
                module.params["add_to_pgs"]
                or not module.params["with_default_protection"]
            ):
                module.fail_json(
                    msg="add_to_pgs and with_default_protection are not supported when restore=all"
                )
            restore_pgsnapshot_all(module, array)
        else:
            # Restore single volume
            if module.params["overwrite"] and (
                module.params["add_to_pgs"] or module.params["with_default_protection"]
            ):
                module.fail_json(
                    msg="overwrite and add_to_pgs or with_default_protection are incompatible"
                )
            restore_pgsnapvolume(module, array)
    elif state == "present" and not pgsnap:
        create_pgsnapshot(module, array)
    elif state == "present" and pgsnap:
        module.exit_json(changed=False)
    elif (
        state == "absent" and module.params["offload"] and get_pgsnapshot(module, array)
    ):
        delete_offload_snapshot(module, array)
    elif state == "rename" and pgsnap:
        update_pgsnapshot(module, array)
    elif state == "absent" and pgsnap and not pgsnap_deleted:
        delete_pgsnapshot(module, array)
    elif state == "absent" and pgsnap and pgsnap_deleted and module.params["eradicate"]:
        eradicate_pgsnapshot(module, array)
    elif state == "absent" and not pgsnap:
        module.exit_json(changed=False)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
