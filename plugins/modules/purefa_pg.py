#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2017, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_pg
version_added: '1.0.0'
short_description: Manage protection groups on Everpure FlashArrays
description:
- Create, delete or modify protection groups on Everpure FlashArrays.
- If a protection group exists and you try to add non-valid types, eg. a host
  to a volume protection group the module will ignore the invalid types.
- Protection Groups on Offload targets are supported.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the protection group.
    type: str
    aliases: [ pgroup ]
    required: true
  state:
    description:
    - Define whether the protection group should exist or not.
    - If specified with I(volume) or I(host) or I(hostgroup) will
      act on those items in the protection group only.
    type: str
    default: present
    choices: [ absent, present ]
  volume:
    description:
    - List of existing volumes to add to protection group.
    - Note that volume are case-sensitive however FlashArray volume names are unique
      and ignore case - you cannot have I(volumea) and I(volumeA)
    type: list
    elements: str
  host:
    description:
    - List of existing hosts to add to protection group.
    - Note that hostnames are case-sensitive however FlashArray hostnames are unique
      and ignore case - you cannot have I(hosta) and I(hostA)
    type: list
    elements: str
  hostgroup:
    description:
    - List of existing hostgroups to add to protection group.
    - Note that hostgroups are case-sensitive however FlashArray hostgroup names are unique
      and ignore case - you cannot have I(groupa) and I(groupA)
    type: list
    elements: str
  eradicate:
    description:
    - Define whether to eradicate the protection group on delete and leave in trash.
    type : bool
    default: false
  enabled:
    description:
    - Define whether to enabled snapshots for the protection group.
    - When not specified a new protection group is created with its schedule
      enabled, and an existing protection group's schedule state is left
      unchanged.
    type : bool
  target:
    description:
    - List of remote arrays or offload target for replication protection group
      to connect to.
    - With I(state=absent) the listed targets are removed from the
      protection group.
    - Note that all replicated protection groups are asynchronous.
    - Target arrays or offload targets must already be connected to the source array.
    - Maximum number of targets per Portection Group is 4, assuming your
      configuration supports this.
    type: list
    elements: str
  rename:
    description:
    - Rename a protection group
    - If the source protection group is in a Pod or Volume Group 'container'
      you only need to provide the new protection group name in the same 'container'
    type: str
  safe_mode:
    description:
    - Enables SafeMode restrictions on the protection group
    - B(Once set disabling this can only be performed by Pure Technical Support)
    type: bool
    default: false
    version_added: '1.13.0'
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
- name: Create new local protection group
  everpure.flasharray.purefa_pg:
    name: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create new protection group called bar in pod called foo
  everpure.flasharray.purefa_pg:
    name: "foo::bar"
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create new replicated protection group
  everpure.flasharray.purefa_pg:
    name: foo
    target:
      - arrayb
      - arrayc
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create new replicated protection group to offload target and remote array
  everpure.flasharray.purefa_pg:
    name: foo
    target:
      - offload
      - arrayc
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create new protection group with snapshots disabled
  everpure.flasharray.purefa_pg:
    name: foo
    enabled: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete protection group
  everpure.flasharray.purefa_pg:
    name: foo
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Eradicate protection group foo on offload target where source array is arrayA
  everpure.flasharray.purefa_pg:
    name: "arrayA:foo"
    target: offload
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Rename protection group foo in pod arrayA to bar
  everpure.flasharray.purefa_pg:
    name: "arrayA::foo"
    rename: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create protection group for hostgroups
  everpure.flasharray.purefa_pg:
    name: bar
    hostgroup:
      - hg1
      - hg2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create protection group for hosts
  everpure.flasharray.purefa_pg:
    name: bar
    host:
      - host1
      - host2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create replicated protection group for volumes
  everpure.flasharray.purefa_pg:
    name: bar
    volume:
      - vol1
      - vol2
    target: arrayb
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Remove a volume from protection group
  everpure.flasharray.purefa_pg:
    name: bar
    volume:
      - vol1
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

import re
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    purefa_argument_spec,
    get_array,
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

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        ProtectionGroup,
        ReplicationSchedule,
        SnapshotSchedule,
    )
except ImportError:
    HAS_PURESTORAGE = False


RETENTION_LOCK_VERSION = "2.13"
CONTEXT_API_VERSION = "2.38"


def get_pod(module, array):
    """Get ActiveCluster Pod"""
    pod_name = "::".join(module.params["name"].split("::")[:-1])
    res = get_with_context(
        array, "get_pods", CONTEXT_API_VERSION, module, names=[pod_name]
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_targets(module, array):
    """Get Offload Targets"""
    targets = []
    target_details = list(
        get_with_context(array, "get_offloads", CONTEXT_API_VERSION, module).items
    )

    for target in target_details:
        if target.status in ["connected", "partially_connected"]:
            targets.append(target.name)
    return targets


def get_arrays(module, array):
    """Get Connected Arrays"""
    arrays = []
    array_details = list(
        get_with_context(
            array, "get_array_connections", CONTEXT_API_VERSION, module
        ).items
    )
    for array_detail in array_details:
        if array_detail.status in [
            "connected",
            "partially_connected",
        ]:
            arrays.append(array_detail.name)
    return arrays


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
        destroyed=False,
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_pgroup_sched(module, array):
    """Get Protection Group Schedule"""
    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        destroyed=False,
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def check_pg_on_offload(module, array):
    """Check if PG already exists on offload target"""
    array_name = list(
        get_with_context(array, "get_arrays", CONTEXT_API_VERSION, module).items
    )[0].name
    remote_pg = array_name + ":" + module.params["name"]
    res = get_with_context(
        array,
        "get_remote_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[remote_pg],
    )
    if res.status_code == 200:
        return list(res.items)[0].remote.name
    return None


def make_pgroup(module, array):
    """Create Protection Group"""
    changed = True
    if module.params["target"]:
        connected_targets = []
        connected_arrays = get_arrays(module, array)
        connected_targets = get_targets(module, array)
        offload_name = check_pg_on_offload(module, array)
        if offload_name and offload_name in module.params["target"][0:4]:
            module.fail_json(
                msg="Protection Group {0} already exists on offload target {1}.".format(
                    module.params["name"], offload_name
                )
            )

        connected_arrays = connected_arrays + connected_targets
        if not connected_arrays:
            module.fail_json(msg="No connected targets on source array.")
        if set(module.params["target"][0:4]).issubset(connected_arrays):
            if not module.check_mode:
                res = post_with_context(
                    array,
                    "post_protection_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                )
                check_response(
                    res,
                    module,
                    f"Failed to create protection group {module.params['name']}",
                )
                res = post_with_context(
                    array,
                    "post_protection_groups_targets",
                    CONTEXT_API_VERSION,
                    module,
                    group_names=[module.params["name"]],
                    member_names=module.params["target"][0:4],
                )
                check_response(
                    res,
                    module,
                    f"Failed to add targets to protection group {module.params['name']}",
                )
        else:
            module.fail_json(
                msg="Check all selected targets are connected to the source array."
            )
    else:
        if not module.check_mode:
            res = post_with_context(
                array,
                "post_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
            )
            check_response(
                res,
                module,
                f"Failed to create protection group {module.params['name']}",
            )
    if not module.check_mode:
        # A new protection group has its schedule enabled unless told otherwise
        enabled = True if module.params["enabled"] is None else module.params["enabled"]
        if module.params["target"]:
            res = patch_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    replication_schedule=ReplicationSchedule(enabled=enabled)
                ),
            )
        else:
            res = patch_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    snapshot_schedule=SnapshotSchedule(enabled=enabled)
                ),
            )
        check_response(res, module, f"Enabling pgroup {module.params['name']}")
        if module.params["volume"]:
            res = post_with_context(
                array,
                "post_protection_groups_volumes",
                CONTEXT_API_VERSION,
                module,
                group_names=[module.params["name"]],
                member_names=module.params["volume"],
            )
            check_response(
                res, module, f"Adding volumes to pgroup {module.params['name']}"
            )
        if module.params["host"]:
            res = post_with_context(
                array,
                "post_protection_groups_hosts",
                CONTEXT_API_VERSION,
                module,
                group_names=[module.params["name"]],
                member_names=module.params["host"],
            )
            check_response(
                res, module, f"Adding hosts to pgroup {module.params['name']}"
            )
        if module.params["hostgroup"]:
            res = post_with_context(
                array,
                "post_protection_groups_host_groups",
                CONTEXT_API_VERSION,
                module,
                group_names=[module.params["name"]],
                member_names=module.params["hostgroup"],
            )
            check_response(
                res,
                module,
                f"Adding hostgroups to pgroup {module.params['name']}",
            )
        if module.params["safe_mode"]:
            res = patch_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(retention_lock="ratcheted"),
            )
            check_response(
                res, module, f"Failed to set SafeMode on pgroup {module.params['name']}"
            )
    module.exit_json(changed=changed)


def rename_exists(module, array):
    """Determine if rename target already exists"""
    new_name = module.params["rename"]
    if "::" in module.params["name"]:
        # Containers nest (realm::pod), so keep everything but the leaf
        container = "::".join(module.params["name"].split("::")[:-1])
        new_name = container + "::" + module.params["rename"]
    elif ":" in module.params["name"]:
        container = module.params["name"].split(":")[0]
        new_name = container + ":" + module.params["rename"]
    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[new_name],
    )
    if res.status_code == 200:
        return True
    return False


def update_pgroup(module, array):
    """Update Protection Group"""
    api_version = array.get_rest_version()
    changed = renamed = False
    state = module.params["state"]
    if module.params["target"]:
        connected_targets = []
        connected_arrays = get_arrays(module, array)
        connected_targets = get_targets(module, array)
        connected_arrays = connected_arrays + connected_targets
        if not connected_arrays:
            module.fail_json(msg="No targets connected to source array.")
        current_connects = list(
            get_with_context(
                array,
                "get_protection_groups_targets",
                CONTEXT_API_VERSION,
                module,
                group_names=[module.params["name"]],
            ).items
        )
        current_targets = []

        if current_connects:
            for connect in current_connects:
                current_targets.append(connect.member.name)

        requested_targets = module.params["target"][0:4]
        if state == "present":
            # Only attach the targets that are not already attached
            new_targets = [t for t in requested_targets if t not in current_targets]
            if new_targets:
                if not set(new_targets).issubset(connected_arrays):
                    module.fail_json(
                        msg="Check all selected targets are connected to the source array."
                    )
                changed = True
                if not module.check_mode:
                    for target in new_targets:
                        res = post_with_context(
                            array,
                            "post_protection_groups_targets",
                            CONTEXT_API_VERSION,
                            module,
                            group_names=[module.params["name"]],
                            member_names=[target],
                        )
                        check_response(
                            res,
                            module,
                            f"Changing targets for pgroup {module.params['name']}",
                        )
        else:
            # state == absent: detach the listed targets that are attached
            old_targets = [t for t in requested_targets if t in current_targets]
            if old_targets:
                changed = True
                if not module.check_mode:
                    for target in old_targets:
                        res = delete_with_context(
                            array,
                            "delete_protection_groups_targets",
                            CONTEXT_API_VERSION,
                            module,
                            group_names=[module.params["name"]],
                            member_names=[target],
                        )
                        check_response(
                            res,
                            module,
                            f"Removing target {target} from pgroup {module.params['name']}",
                        )

    if (
        module.params["target"]
        and module.params["enabled"] is not None
        and module.params["enabled"]
        != get_pgroup_sched(module, array).replication_schedule.enabled
    ):
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    replication_schedule=ReplicationSchedule(
                        enabled=module.params["enabled"]
                    )
                ),
            )
            check_response(
                res,
                module,
                f"Changing replication enabled state of pgroup {module.params['name']}",
            )
    elif (
        not module.params["target"]
        and module.params["enabled"] is not None
        and module.params["enabled"]
        != get_pgroup_sched(module, array).snapshot_schedule.enabled
    ):
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                protection_group=ProtectionGroup(
                    snapshot_schedule=SnapshotSchedule(enabled=module.params["enabled"])
                ),
            )
            check_response(
                res,
                module,
                f"Changing snapshot enabled state of pgroup {module.params['name']}",
            )
    if (
        module.params["volume"]
        and get_pgroup(module, array).host_count == 0
        and get_pgroup(module, array).host_group_count == 0
    ):
        if get_pgroup(module, array).volume_count == 0:
            # Nothing to remove from an empty group
            if state == "present":
                changed = True
                if not module.check_mode:
                    res = post_with_context(
                        array,
                        "post_protection_groups_volumes",
                        CONTEXT_API_VERSION,
                        module,
                        group_names=[module.params["name"]],
                        member_names=module.params["volume"],
                    )
                    check_response(
                        res,
                        module,
                        f"Adding volumes to pgroup {module.params['name']}",
                    )
        else:
            pgvols = []
            vols = list(
                get_with_context(
                    array,
                    "get_protection_groups_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    group_names=[module.params["name"]],
                ).items
            )
            for vol in vols:
                pgvols.append(vol.member.name)
            if state == "present":
                new_vols = [x for x in module.params["volume"] if x not in pgvols]
                if new_vols:
                    changed = True
                    if not module.check_mode:
                        res = post_with_context(
                            array,
                            "post_protection_groups_volumes",
                            CONTEXT_API_VERSION,
                            module,
                            group_names=[module.params["name"]],
                            member_names=new_vols,
                        )
                        check_response(
                            res,
                            module,
                            f"Adding volumes in pgroup {module.params['name']}",
                        )
            else:
                old_vols = [x for x in module.params["volume"] if x in pgvols]
                if old_vols:
                    changed = True
                    if not module.check_mode:
                        res = delete_with_context(
                            array,
                            "delete_protection_groups_volumes",
                            CONTEXT_API_VERSION,
                            module,
                            group_names=[module.params["name"]],
                            member_names=old_vols,
                        )
                        check_response(
                            res,
                            module,
                            f"Removing volumes from pgroup {module.params['name']}",
                        )

    if (
        module.params["host"]
        and get_pgroup(module, array).volume_count == 0
        and get_pgroup(module, array).host_group_count == 0
    ):
        if get_pgroup(module, array).host_count == 0:
            # Nothing to remove from an empty group
            if state == "present":
                changed = True
                if not module.check_mode:
                    res = post_with_context(
                        array,
                        "post_protection_groups_hosts",
                        CONTEXT_API_VERSION,
                        module,
                        group_names=[module.params["name"]],
                        member_names=module.params["host"],
                    )
                    check_response(
                        res,
                        module,
                        f"Adding hosts to pgroup {module.params['name']}",
                    )
        else:
            pghosts = []
            hosts = list(
                get_with_context(
                    array,
                    "get_protection_groups_hosts",
                    CONTEXT_API_VERSION,
                    module,
                    group_names=[module.params["name"]],
                ).items
            )
            for host in hosts:
                pghosts.append(host.member.name)
            if state == "present":
                new_hosts = [x for x in module.params["host"] if x not in pghosts]
                if new_hosts:
                    changed = True
                    if not module.check_mode:
                        res = post_with_context(
                            array,
                            "post_protection_groups_hosts",
                            CONTEXT_API_VERSION,
                            module,
                            group_names=[module.params["name"]],
                            member_names=new_hosts,
                        )
                        check_response(
                            res,
                            module,
                            f"Adding hosts in pgroup {module.params['name']}",
                        )
            else:
                old_hosts = [x for x in module.params["host"] if x in pghosts]
                if old_hosts:
                    changed = True
                    if not module.check_mode:
                        res = delete_with_context(
                            array,
                            "delete_protection_groups_hosts",
                            CONTEXT_API_VERSION,
                            module,
                            group_names=[module.params["name"]],
                            member_names=old_hosts,
                        )
                        check_response(
                            res,
                            module,
                            f"Removing hosts from pgroup {module.params['name']}",
                        )

    if (
        module.params["hostgroup"]
        and get_pgroup(module, array).host_count == 0
        and get_pgroup(module, array).volume_count == 0
    ):
        if get_pgroup(module, array).host_group_count == 0:
            # Nothing to remove from an empty group
            if state == "present":
                changed = True
                if not module.check_mode:
                    res = post_with_context(
                        array,
                        "post_protection_groups_host_groups",
                        CONTEXT_API_VERSION,
                        module,
                        group_names=[module.params["name"]],
                        member_names=module.params["hostgroup"],
                    )
                    check_response(
                        res,
                        module,
                        f"Adding hostgroups in pgroup {module.params['name']}",
                    )
        else:
            pghostgs = []
            hostgs = list(
                get_with_context(
                    array,
                    "get_protection_groups_host_groups",
                    CONTEXT_API_VERSION,
                    module,
                    group_names=[module.params["name"]],
                ).items
            )
            for hostg in hostgs:
                pghostgs.append(hostg.member.name)
            if state == "present":
                new_hgs = [x for x in module.params["hostgroup"] if x not in pghostgs]
                if new_hgs:
                    changed = True
                    if not module.check_mode:
                        res = post_with_context(
                            array,
                            "post_protection_groups_host_groups",
                            CONTEXT_API_VERSION,
                            module,
                            group_names=[module.params["name"]],
                            member_names=new_hgs,
                        )
                        check_response(
                            res,
                            module,
                            f"Adding hostgroups in pgroup {module.params['name']}",
                        )
            else:
                old_hgs = [x for x in module.params["hostgroup"] if x in pghostgs]
                if old_hgs:
                    changed = True
                    if not module.check_mode:
                        res = delete_with_context(
                            array,
                            "delete_protection_groups_host_groups",
                            CONTEXT_API_VERSION,
                            module,
                            group_names=[module.params["name"]],
                            member_names=old_hgs,
                        )
                        check_response(
                            res,
                            module,
                            f"Removing hostgroups from pgroup {module.params['name']}",
                        )
    if module.params["rename"]:
        if not rename_exists(module, array):
            if "::" in module.params["name"]:
                container = "::".join(module.params["name"].split("::")[:-1])
                rename = container + "::" + module.params["rename"]
            elif ":" in module.params["name"]:
                container = module.params["name"].split(":")[0]
                rename = container + ":" + module.params["rename"]
            else:
                rename = module.params["rename"]
            renamed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_protection_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    protection_group=ProtectionGroup(name=rename),
                )
                module.params["name"] = rename
                check_response(res, module, f"Rename to {rename}")
        else:
            module.warn(
                "Rename failed. Protection group {0} already exists in container. Continuing with other changes...".format(
                    module.params["rename"]
                )
            )
    if LooseVersion(RETENTION_LOCK_VERSION) <= LooseVersion(api_version):
        current_pg = list(
            get_with_context(
                array,
                "get_protection_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
            ).items
        )[0]
        if current_pg.retention_lock == "unlocked" and module.params["safe_mode"]:
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_protection_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    protection_group=ProtectionGroup(retention_lock="ratcheted"),
                )
                check_response(
                    res,
                    module,
                    f"Failed to set SafeMode on protection group {module.params['name']}",
                )
        if current_pg.retention_lock == "ratcheted" and not module.params["safe_mode"]:
            module.warn(
                "Disabling SafeMode on protection group {0} can only be performed by Pure Technical Support".format(
                    module.params["name"]
                )
            )
    changed = changed or renamed
    module.exit_json(changed=changed)


def eradicate_pgroup(module, array):
    """Eradicate Protection Group"""
    changed = True
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_protection_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        )
        check_response(res, module, f"Eradicating pgroup {module.params['name']}")
    module.exit_json(changed=changed)


def delete_pgroup(module, array):
    """Delete Protection Group"""
    changed = True
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_protection_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            protection_group=ProtectionGroup(destroyed=True),
        )
        check_response(res, module, f"Deleting pgroup {module.params['name']}")
        if module.params["eradicate"]:
            eradicate_pgroup(module, array)

    module.exit_json(changed=changed)


def recover_pgroup(module, array):
    """Recover deleted protection group"""
    changed = True
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_protection_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            protection_group=ProtectionGroup(destroyed=False),
        )
        check_response(res, module, f"Recover pgroup {module.params['name']}")
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True, aliases=["pgroup"]),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            volume=dict(type="list", elements="str"),
            host=dict(type="list", elements="str"),
            hostgroup=dict(type="list", elements="str"),
            target=dict(type="list", elements="str"),
            safe_mode=dict(type="bool", default=False),
            eradicate=dict(type="bool", default=False),
            enabled=dict(type="bool"),
            rename=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    mutually_exclusive = [["volume", "host", "hostgroup"]]
    module = AnsibleModule(
        argument_spec, mutually_exclusive=mutually_exclusive, supports_check_mode=True
    )
    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required.")

    state = module.params["state"]
    array = get_array(module)
    pattern = re.compile("^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
    if module.params["rename"]:
        if not pattern.match(module.params["rename"]):
            module.fail_json(
                msg="Rename value {0} does not conform to naming convention".format(
                    module.params["rename"]
                )
            )
        if not pattern.match(module.params["name"].split(":")[-1]):
            module.fail_json(
                msg="Protection Group name {0} does not conform to naming convention".format(
                    module.params["name"]
                )
            )
    api_version = array.get_rest_version()
    if (
        LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version)
        and not module.params["context"]
    ):
        # If no context is provided set the context to the local array name
        fleet_res = array.get_fleets()
        if fleet_res.status_code == 200 and list(fleet_res.items):
            module.params["context"] = list(array.get_arrays().items)[0].name
    if module.params["safe_mode"] and LooseVersion(
        RETENTION_LOCK_VERSION
    ) > LooseVersion(api_version):
        module.fail_json(
            msg="API version does not support setting SafeMode on a protection group."
        )
    if ":" in module.params["name"]:
        if "::" in module.params["name"]:
            pgname = module.params["name"].split("::")[-1]
        else:
            pgname = module.params["name"].split(":")[1]
        if not pattern.match(pgname):
            module.fail_json(
                msg="Protection Group name {0} does not conform to naming convention".format(
                    pgname
                )
            )
    else:
        if not pattern.match(module.params["name"]):
            module.fail_json(
                msg="Protection Group name {0} does not conform to naming convention".format(
                    module.params["name"]
                )
            )

    pgroup = get_pgroup(module, array)
    xpgroup = get_pending_pgroup(module, array)
    if "::" in module.params["name"]:
        if not get_pod(module, array):
            if state == "absent":
                # No pod means no group to remove
                module.exit_json(changed=False)
            module.fail_json(
                msg="Pod {0} does not exist.".format(
                    "::".join(module.params["name"].split("::")[:-1])
                )
            )

    if module.params["host"]:
        host_exists = get_with_context(
            array,
            "get_hosts",
            CONTEXT_API_VERSION,
            module,
            names=module.params["host"],
        )
        check_response(host_exists, module, "Host not found")

    if module.params["hostgroup"]:
        hg_exists = get_with_context(
            array,
            "get_host_groups",
            CONTEXT_API_VERSION,
            module,
            names=module.params["hostgroup"],
        )
        check_response(hg_exists, module, "Host Group not found")

    if pgroup and state == "present":
        update_pgroup(module, array)
    elif (
        pgroup
        and state == "absent"
        and (
            module.params["volume"]
            or module.params["host"]
            or module.params["hostgroup"]
            or module.params["target"]
        )
    ):
        update_pgroup(module, array)
    elif pgroup and state == "absent":
        delete_pgroup(module, array)
    elif xpgroup and state == "absent" and module.params["eradicate"]:
        eradicate_pgroup(module, array)
    elif (
        not pgroup
        and not xpgroup
        and state == "present"
        and not module.params["rename"]
    ):
        make_pgroup(module, array)
    elif not pgroup and state == "present" and module.params["rename"]:
        module.exit_json(changed=False)
    elif xpgroup and state == "present":
        recover_pgroup(module, array)
    elif pgroup is None and state == "absent":
        module.exit_json(changed=False)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
