#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2018, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_hg
version_added: '1.0.0'
short_description: Manage hostgroups on Everpure FlashArrays
description:
- Create, delete or modify hostgroups on Everpure FlashArrays.
author:
- Everpure ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the hostgroup.
    type: str
    required: true
    aliases: [ hostgroup ]
  state:
    description:
    - Define whether the hostgroup should exist or not.
    type: str
    default: present
    choices: [ absent, present ]
  host:
    type: list
    elements: str
    description:
    - List of existing hosts to add to hostgroup.
    - Note that hostnames are case-sensitive however FlashArray hostnames are unique
      and ignore case - you cannot have I(hosta) and I(hostA)
  volume:
    type: list
    elements: str
    description:
    - List of existing volumes to add to hostgroup.
    - Note that volumes are case-sensitive however FlashArray volume names are unique
      and ignore case - you cannot have I(volumea) and I(volumeA)
  lun:
    description:
    - LUN ID to assign to volume for hostgroup. Must be unique.
    - Only applicable when only one volume is specified for connection.
    - If not provided the ID will be automatically assigned.
    - Range for LUN ID is 1 to 4095.
    type: int
  rename:
    description:
    - New name of hostgroup
    type: str
    version_added: '1.10.0'
  eradicate:
    description:
    - Whether to eradicate a deleted host group or not
    - Host groups are removed immediately by the array and have no
      recoverable (destroyed) state, so this parameter currently has
      no effect. It is accepted for backwards compatibility.
    type: bool
    default: false
    version_added: '1.32.0'
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
- name: Create empty hostgroup
  everpure.flasharray.purefa_hg:
    name: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Add hosts and volumes to existing or new hostgroup
  everpure.flasharray.purefa_hg:
    name: foo
    host:
      - host1
      - host2
    volume:
      - vol1
      - vol2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete hosts and volumes from hostgroup
  everpure.flasharray.purefa_hg:
    name: foo
    host:
      - host1
      - host2
    volume:
      - vol1
      - vol2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

# This will disconnect all hosts and volumes in the hostgroup
- name: Delete hostgroup
  everpure.flasharray.purefa_hg:
    name: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Rename hostgroup
  everpure.flasharray.purefa_hg:
    name: foo
    rename: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create host group with hosts and volumes
  everpure.flasharray.purefa_hg:
    name: bar
    host:
      - host1
      - host2
    volume:
      - vol1
      - vol2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        ConnectionPost,
        HostGroupPatch,
        HostPatch,
        ReferenceNoId,
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
    get_with_context,
    post_with_context,
    patch_with_context,
    delete_with_context,
)

CONTEXT_API_VERSION = "2.38"


def rename_exists(module, array):
    """Determine if rename target already exists"""
    res = get_with_context(
        array,
        "get_host_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["rename"]],
    )
    return bool(res.status_code == 200)


def get_hostgroup_hosts(module, array):
    hostgroup = None
    res = get_with_context(
        array,
        "get_host_groups_hosts",
        CONTEXT_API_VERSION,
        module,
        group_names=[module.params["name"]],
    )
    if res.status_code == 200:
        hostgroup = list(res.items)
    return hostgroup


def get_hostgroup(module, array):
    hostgroup = None
    res = get_with_context(
        array,
        "get_host_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
    )
    if res.status_code == 200:
        hostgroup = list(res.items)[0]
    return hostgroup


def make_hostgroup(module, array):
    if module.params["rename"]:
        if rename_exists(module, array):
            # Source is gone and the rename target exists: the rename has
            # already been done, so this is a no-op.
            module.exit_json(changed=False)
        module.fail_json(
            msg="Hostgroup {0} does not exist - rename failed.".format(
                module.params["name"]
            )
        )
    changed = True
    if not module.check_mode:
        res = post_with_context(
            array,
            "post_host_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        )
        check_response(
            res, module, f"Failed to create hostgroup {module.params['name']}"
        )
        if module.params["host"]:
            res = post_with_context(
                array,
                "post_host_groups_hosts",
                CONTEXT_API_VERSION,
                module,
                group_names=[module.params["name"]],
                member_names=module.params["host"],
            )
            check_response(res, module, "Failed to add host to hostgroup")
        if module.params["volume"]:
            if len(module.params["volume"]) == 1 and module.params["lun"]:
                res = post_with_context(
                    array,
                    "post_connections",
                    CONTEXT_API_VERSION,
                    module,
                    host_group_names=[module.params["name"]],
                    volume_names=[module.params["volume"][0]],
                    connection=ConnectionPost(lun=module.params["lun"]),
                )
                check_response(
                    res,
                    module,
                    f"Failed to add volume {module.params['volume'][0]} with LUN ID {module.params['lun']}",
                )
            else:
                res = post_with_context(
                    array,
                    "post_connections",
                    CONTEXT_API_VERSION,
                    module,
                    host_group_names=[module.params["name"]],
                    volume_names=module.params["volume"],
                )
                check_response(res, module, "Failed to add volumes to hostgroup")
    module.exit_json(changed=changed)


def update_hostgroup(module, array):
    changed = False
    renamed = False
    hgroup = get_hostgroup_hosts(module, array)
    current_hostgroup = module.params["name"]
    volumes = list(
        get_with_context(
            array,
            "get_connections",
            CONTEXT_API_VERSION,
            module,
            host_group_names=[module.params["name"]],
        ).items
    )
    if module.params["state"] == "present":
        if module.params["rename"]:
            if not rename_exists(module, array):
                if not module.check_mode:
                    res = patch_with_context(
                        array,
                        "patch_host_groups",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["name"]],
                        host_group=HostGroupPatch(name=module.params["rename"]),
                    )
                    check_response(res, module, f"Rename to {module.params['rename']}")
                    current_hostgroup = module.params["rename"]
                    renamed = True
            else:
                module.warn(
                    "Rename failed. Hostgroup {0} already exists. Continuing with other changes...".format(
                        module.params["rename"]
                    )
                )
        if module.params["host"]:
            hosts = list(module.params["host"])
            hghosts = []
            for host in hgroup:
                hghosts.append(host.member.name)
            new_hosts = list(set(hosts).difference(hghosts))
            if new_hosts:
                if not module.check_mode:
                    res = patch_with_context(
                        array,
                        "patch_hosts",
                        CONTEXT_API_VERSION,
                        module,
                        host=HostPatch(
                            host_group=ReferenceNoId(name=current_hostgroup)
                        ),
                        names=new_hosts,
                    )
                    check_response(res, module, "Failed to add host(s) to hostgroup")
                changed = True
        if module.params["volume"]:
            if volumes:
                current_vols = [vol.volume.name for vol in volumes]
                vols = list(module.params["volume"])
                new_volumes = list(set(vols).difference(set(current_vols)))
                if len(new_volumes) == 1 and module.params["lun"]:
                    if not module.check_mode:
                        res = post_with_context(
                            array,
                            "post_connections",
                            CONTEXT_API_VERSION,
                            module,
                            host_group_names=[current_hostgroup],
                            volume_names=[new_volumes[0]],
                            connection=ConnectionPost(lun=module.params["lun"]),
                        )
                        check_response(
                            res,
                            module,
                            f"Failed to add volume {new_volumes[0]} with LUN ID {module.params['lun']}",
                        )
                    changed = True
                else:
                    for cvol in new_volumes:
                        if not module.check_mode:
                            res = post_with_context(
                                array,
                                "post_connections",
                                CONTEXT_API_VERSION,
                                module,
                                host_group_names=[current_hostgroup],
                                volume_names=[cvol],
                            )
                            check_response(
                                res,
                                module,
                                f"Failed to connect volume {cvol} to hostgroup {current_hostgroup}",
                            )
                        changed = True
            else:
                if len(module.params["volume"]) == 1 and module.params["lun"]:
                    if not module.check_mode:
                        res = post_with_context(
                            array,
                            "post_connections",
                            CONTEXT_API_VERSION,
                            module,
                            host_group_names=[current_hostgroup],
                            volume_names=[module.params["volume"][0]],
                            connection=ConnectionPost(lun=module.params["lun"]),
                        )
                        check_response(
                            res,
                            module,
                            f"Failed to add volume {module.params['volume']} with LUN ID {module.params['lun']}",
                        )
                    changed = True
                else:
                    for cvol in module.params["volume"]:
                        if not module.check_mode:
                            res = post_with_context(
                                array,
                                "post_connections",
                                CONTEXT_API_VERSION,
                                module,
                                host_group_names=[current_hostgroup],
                                volume_names=[cvol],
                            )
                            check_response(
                                res,
                                module,
                                f"Failed to connect volume {cvol} to hostgroup {current_hostgroup}",
                            )
                        changed = True
    else:
        if module.params["host"]:
            old_hosts = list(module.params["host"])
            hosts = []
            for host in hgroup:
                hosts.append(host.member.name)
            old_hosts = list(set(old_hosts).intersection(hosts))
            if old_hosts:
                if not module.check_mode:
                    res = delete_with_context(
                        array,
                        "delete_host_groups_hosts",
                        CONTEXT_API_VERSION,
                        module,
                        group_names=[current_hostgroup],
                        member_names=old_hosts,
                    )
                    check_response(
                        res,
                        module,
                        f"Failed to remove hosts {old_hosts} from hostgroup {current_hostgroup}",
                    )
                changed = True
        if module.params["volume"]:
            old_vols = list(module.params["volume"])
            old_volumes = list(
                set(old_vols).intersection(set([vol.volume.name for vol in volumes]))
            )
            if old_volumes:
                changed = True
                if not module.check_mode:
                    res = delete_with_context(
                        array,
                        "delete_connections",
                        CONTEXT_API_VERSION,
                        module,
                        host_group_names=[current_hostgroup],
                        volume_names=old_volumes,
                    )
                    check_response(
                        res,
                        module,
                        f"Failed to disconnect volumes from hostgroup {current_hostgroup}",
                    )
    changed = changed or renamed
    module.exit_json(changed=changed)


def delete_hostgroup(module, array):
    changed = False
    res = get_with_context(
        array,
        "get_connections",
        CONTEXT_API_VERSION,
        module,
        host_group_names=[module.params["name"]],
    )
    if res.status_code == 200:
        vols = list(res.items)
    else:
        check_response(
            res,
            module,
            f"Failed to get volume connection for hostgroup {module.params['name']}",
        )
    # The array returns one connection row per member host, so a volume
    # connected to a group of N hosts appears N times. Sending a name more
    # than once makes delete_connections fail with HTTP 500, so keep the
    # first occurrence of each.
    remove_vols = list(dict.fromkeys(vol.volume.name for vol in vols))
    if remove_vols:
        changed = True
        if not module.check_mode:
            res = delete_with_context(
                array,
                "delete_connections",
                CONTEXT_API_VERSION,
                module,
                host_group_names=[module.params["name"]],
                volume_names=remove_vols,
            )
            check_response(
                res,
                module,
                f"Failed to disconnect volumes from hostgroup {module.params['name']}",
            )
    hgroup = get_hostgroup_hosts(module, array)
    hghosts = []
    for host in hgroup:
        hghosts.append(host.member.name)
    if hghosts:
        changed = True
        if not module.check_mode:
            res = delete_with_context(
                array,
                "delete_host_groups_hosts",
                CONTEXT_API_VERSION,
                module,
                group_names=[hgroup[0].group.name],
                member_names=hghosts,
            )
            check_response(res, module, "Failed to remove hosts from hostgroup")
    # The host group itself is always removed, so this is always a change
    changed = True
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_host_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        )
        check_response(
            res, module, f"Failed to delete hostgroup {module.params['name']}"
        )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True, aliases=["hostgroup"]),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            host=dict(type="list", elements="str"),
            lun=dict(type="int"),
            rename=dict(type="str"),
            volume=dict(type="list", elements="str"),
            eradicate=dict(type="bool", default=False),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    state = module.params["state"]
    array = get_array(module)
    api_version = array.get_rest_version()
    if (
        LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version)
        and not module.params["context"]
    ):
        # If no context is provided set the context to the local array name
        fleet_res = array.get_fleets()
        if fleet_res.status_code == 200 and list(fleet_res.items):
            module.params["context"] = list(array.get_arrays().items)[0].name
    hostgroup = get_hostgroup(module, array)

    if module.params["host"]:
        res = get_with_context(
            array,
            "get_hosts",
            CONTEXT_API_VERSION,
            module,
            names=module.params["host"],
        )
        if res.status_code == 400:
            module.fail_json(msg="Host {0} not found".format(res.errors[0].context))
    if module.params["lun"] and state == "present":
        if not module.params["volume"]:
            module.fail_json(msg="LUN ID must be specified with a volume name")
        if len(module.params["volume"]) > 1:
            module.fail_json(msg="LUN ID cannot be specified with multiple volumes.")

    if module.params["lun"] and not 1 <= module.params["lun"] <= 4095:
        module.fail_json(
            msg="LUN ID of {0} is out of range (1 to 4095)".format(module.params["lun"])
        )

    if module.params["volume"]:
        res = get_with_context(
            array,
            "get_volumes",
            CONTEXT_API_VERSION,
            module,
            names=module.params["volume"],
        )
        if res.status_code == 400:
            module.fail_json(msg="Volume {0} not found".format(res.errors[0].context))
    if hostgroup and state == "present":
        update_hostgroup(module, array)
    elif hostgroup and module.params["volume"] is not None and state == "absent":
        update_hostgroup(module, array)
    elif hostgroup and module.params["host"] is not None and state == "absent":
        update_hostgroup(module, array)
    elif hostgroup and state == "absent":
        delete_hostgroup(module, array)
    elif hostgroup is None and state == "absent":
        module.exit_json(changed=False)
    else:
        make_hostgroup(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
