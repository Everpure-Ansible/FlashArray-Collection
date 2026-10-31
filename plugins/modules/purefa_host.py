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
module: purefa_host
version_added: '1.0.0'
short_description: Manage hosts on Everpure FlashArrays
description:
- Create, delete or modify hosts on Everpure FlashArrays.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
notes:
- If specifying C(lun) option ensure host support requested value
options:
  name:
    description:
    - The name of the host.
    - Note that hostnames are case-sensitive however FlashArray hostnames are unique
      and ignore case - you cannot have I(hosta) and I(hostA)
    - Multi-host support available from Purity//FA 6.0.0
      B(***NOTE***) Manual deletion of individual hosts created
      using multi-host will cause idempotency to fail
    - Multi-host support only exists for host creation
    type: str
    required: true
    aliases: [ host ]
  protocol:
    description:
    - Defines the host connection protocol for volumes.
    - DEPRECATED No longer a necessary parameter
    type: str
    choices: [ fc, iscsi, nvme, mixed ]
  rename:
    description:
    - The name to rename to.
    - Note that hostnames are case-sensitive however FlashArray hostnames are unique
      and ignore case - you cannot have I(hosta) and I(hostA)
    type: str
  state:
    description:
    - Define whether the host should exist or not.
    - When removing host all connected volumes will be disconnected.
    type: str
    default: present
    choices: [ absent, present ]
  wwns:
    type: list
    elements: str
    description:
    - List of wwns of the host.
    - This is the complete desired set of WWNs. The host is reconciled to match
      it, adding any that are missing and removing any that are not listed, so a
      single WWN can be removed by simply omitting it from the list.
    - WWNs in the FlashArray OUI (C(52:4A:93)) are rejected by the array
      with "Cannot specify a FlashArray WWN"; use the initiator's own WWN.
  iqn:
    type: list
    elements: str
    description:
    - List of IQNs of the host.
    - This is the complete desired set of IQNs; the host is reconciled to match
      it, adding and removing IQNs as needed.
  nqn:
    type: list
    elements: str
    description:
    - List of NQNs of the host. Note that NMVe hosts can only possess NQNs.
    - This is the complete desired set of NQNs; the host is reconciled to match
      it, adding and removing NQNs as needed.
      Multi-protocol is not allowed for these hosts.
  volume:
    type: str
    description:
    - Volume name to map to the host.
  lun:
    description:
    - LUN ID to assign to volume for host. Must be unique.
    - If not provided the ID will be automatically assigned.
    - Range for LUN ID is 1 to 4095.
    type: int
  count:
    description:
    - Number of hosts to be created in a multiple host creation
    - Only supported from Purity//FA v6.0.0 and higher
    type: int
  start:
    description:
    - Number at which to start the multiple host creation index
    - Only supported from Purity//FA v6.0.0 and higher
    type: int
    default: 0
  digits:
    description:
    - Number of digits to use for multiple host count. This
      will pad the index number with zeros where necessary
    - Only supported from Purity//FA v6.0.0 and higher
    - Range is between 1 and 10
    type: int
    default: 1
  suffix:
    description:
    - Suffix string, if required, for multiple host create
    - Host names will be formed as I(<name>#<suffix>), where
      I(#) is a placeholder for the host index
      See associated descriptions
    - Suffix string is optional
    - Only supported from Purity//FA v6.0.0 and higher
    type: str
  personality:
    type: str
    description:
    - Define which operating system the host is. Recommended for
      ActiveCluster integration.
    - The C(nutanix-mgmt) and C(nutanix-cluster) personalities are only
      supported from REST API 2.50 and higher.
    default: ''
    choices: ['hpux', 'vms', 'aix', 'esxi', 'solaris', 'hitachi-vsp', 'oracle-vm-server', 'nutanix-mgmt', 'nutanix-cluster', 'delete', '']
  preferred_array:
    type: list
    elements: str
    description:
    - List of preferred arrays in an ActiveCluster environment.
    - To remove existing preferred arrays from the host, specify I(delete).
  target_user:
    type: str
    description:
    - Sets the target user name for CHAP authentication
    - Required with I(target_password)
    - To clear the username/password pair use I(clear) as the password
  target_password:
    type: str
    description:
    - Sets the target password for CHAP authentication
    - Password length between 12 and 255 characters
    - To clear the username/password pair use I(clear) as the password
    - SETTING A PASSWORD IS NON-IDEMPOTENT
  host_user:
    type: str
    description:
    - Sets the host user name for CHAP authentication
    - Required with I(host_password)
    - To clear the username/password pair use I(clear) as the password
  host_password:
    type: str
    description:
    - Sets the host password for CHAP authentication
    - Password length between 12 and 255 characters
    - To clear the username/password pair use I(clear) as the password
    - SETTING A PASSWORD IS NON-IDEMPOTENT
  vlan:
    type: str
    description:
    - The VLAN ID that the host is associated with.
    - If not set or set to I(any), the host can access any VLAN.
    - If set to I(untagged), the host can only access untagged VLANs.
    - If set to a number between 1 and 4094, the host can only access the specified VLAN with that number.
    version_added: '1.16.0'
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
    version_added: '1.33.0'
  move:
    description:
    - Move a host in and out of a local member realm(s) or local array
    - Provide the name of realm(s) to move to
    - To move to the local array, specify C(local)
    - Host cannot have connected volume(s) for move operation
    type: list
    elements: str
    version_added: '1.35.0'
  modify_resource_access:
    description:
    - Describes how to modify a resource accesses of a resource when
      that resource is moved.
    - The none value indicates that no resource access should be modified.
    - The create value is used when a resource is moving out of a realm into
      the array and it needs to create a resource access of the moved
      resource to the realm from which it is moving.
    - The delete value is used when a resource that is moving from an array
      into a realm already has a resource access into that realm.
    type: str
    choices: ["none", "create", "delete"]
    default: none
    version_added: '1.35.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create new AIX host
  everpure.flasharray.purefa_host:
    name: foo
    personality: aix
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create host bar in existing realm foo
  everpure.flasharray.purefa_host:
    name: foo::bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create 10 hosts with index starting at 10 but padded with 3 digits
  everpure.flasharray.purefa_host:
    name: foo
    personality: vms
    suffix: bar
    count: 10
    start: 10
    digits: 3
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Rename host foo to bar
  everpure.flasharray.purefa_host:
    name: foo
    rename: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete host
  everpure.flasharray.purefa_host:
    name: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Make host bar with wwn ports
  everpure.flasharray.purefa_host:
    name: bar
    wwns:
      - 00:00:00:00:00:00:00:00
      - 11:11:11:11:11:11:11:11
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Make host bar with iSCSI ports
  everpure.flasharray.purefa_host:
    name: bar
    iqn:
      - iqn.1994-05.com.redhat:7d366003913
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Make host bar with NVMe ports
  everpure.flasharray.purefa_host:
    name: bar
    nqn:
      - nqn.2014-08.com.vendor:nvme:nvm-subsystem-sn-d78432
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Make mixed protocol host
  everpure.flasharray.purefa_host:
    name: bar
    iqn:
      - iqn.1994-05.com.redhat:7d366003914
    wwns:
      - 00:00:00:00:00:00:00:01
      - 11:11:11:11:11:11:11:12
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Map host foo to volume bar as LUN ID 12
  everpure.flasharray.purefa_host:
    name: foo
    volume: bar
    lun: 12
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Disconnect volume bar from host foo
  everpure.flasharray.purefa_host:
    name: foo
    volume: bar
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Add preferred arrays to host foo
  everpure.flasharray.purefa_host:
    name: foo
    preferred_array:
      - array1
      - array2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete preferred arrays from host foo
  everpure.flasharray.purefa_host:
    name: foo
    preferred_array: delete
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete existing WWNs from host foo (does not delete host object)
  everpure.flasharray.purefa_host:
    name: foo
    wwns: ""
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Set CHAP target and host username/password pairs
  everpure.flasharray.purefa_host:
    name: foo
    target_user: user1
    target_password: passwrodpassword
    host_user: user2
    host_password: passwrodpassword
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete CHAP target and host username/password pairs
  everpure.flasharray.purefa_host:
    name: foo
    target_user: user
    target_password: clear
    host_user: user
    host_password: clear
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Move host foo from the array to realm bar
  everpure.flasharray.purefa_host:
    name: foo
    move: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Move host foo from realm bar back to array
  everpure.flasharray.purefa_host:
    name: bar::foo
    move: local
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename host foo in realm test to bar
  everpure.flasharray.purefa_host:
    name: test::foo
    rename: test::bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        Chap,
        HostPatch,
        HostPost,
        ConnectionPost,
        Reference,
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
    get_with_context,
    check_response,
    get_cached_api_version,
)

VLAN_API_VERSION = "2.16"
CONTEXT_API_VERSION = "2.38"
REALMS_CONTEXT_VERSION = "2.47"
NUTANIX_API_VERSION = "2.50"


def _is_cbs(array, is_cbs=False):
    """Is the selected array a Cloud Block Store"""
    # api_version = array.get_rest_version()
    #
    # Until get_controller has context_names we can check against a target system
    # so CBS can't be support for Fusion until 6.8.4??
    #
    # if LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version):
    #    model = list(
    #        array.get_controllers(context_names=[module.params["context"]]).items
    #    )[0].model
    # else:
    model = list(array.get_controllers().items)[0].model
    is_cbs = bool("CBS" in model)
    return is_cbs


def _set_host_initiators(module, array):
    """Set host initiators."""
    if module.params["nqn"]:
        res = get_with_context(
            array,
            "patch_hosts",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            host=HostPatch(nqns=module.params["nqn"]),
        )
        check_response(
            res, module, f"Setting of NVMe NQN for host {module.params['name']}"
        )
    if module.params["iqn"]:
        res = get_with_context(
            array,
            "patch_hosts",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            host=HostPatch(iqns=module.params["iqn"]),
        )
        check_response(
            res, module, f"Setting of iSCSI IQN for host {module.params['name']}"
        )
    if module.params["wwns"]:
        res = get_with_context(
            array,
            "patch_hosts",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            host=HostPatch(wwns=module.params["wwns"]),
        )
        check_response(
            res, module, f"Setting of FC WWNs for host {module.params['name']}"
        )


def _sync_initiators(module, array, add_field, remove_field, desired, current, error):
    """Reconcile a single initiator type to the desired set.

    The FlashArray ``patch_hosts`` API exposes three fields per initiator type:
    ``wwns``/``iqns``/``nqns`` *replace* the whole associated list, while
    ``add_*`` associates extra initiators and ``remove_*`` disassociates
    specific ones. We use the ``add_*``/``remove_*`` pair (never the replacing
    field) so that only the genuinely changed initiators are touched: an
    unwanted WWN/IQN/NQN is dropped by omitting it from the list, and the
    initiators that stay are left untouched rather than being removed and
    re-added (which would needlessly disrupt their existing sessions).

    Returns True if a change was (or would be) made.
    """
    to_add = [item for item in desired if item not in current]
    to_remove = [item for item in current if item not in desired]
    if not to_add and not to_remove:
        return False
    if not module.check_mode:
        patch = {}
        if to_add:
            patch[add_field] = to_add
        if to_remove:
            patch[remove_field] = to_remove
        res = get_with_context(
            array,
            "patch_hosts",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            host=HostPatch(**patch),
        )
        check_response(res, module, error)
    return True


def _update_host_initiators(module, array, answer=False):
    """Reconcile host initiators (iSCSI, NVMe and FC) to the requested set"""
    current_connectors = get_host(module, array)
    if module.params["nqn"]:
        desired = [] if module.params["nqn"] == [""] else module.params["nqn"]
        if _sync_initiators(
            module,
            array,
            "add_nqns",
            "remove_nqns",
            desired,
            current_connectors.nqns or [],
            f"Change of NVMe NQNs on host {module.params['name']}",
        ):
            answer = True
    if module.params["iqn"]:
        desired = [] if module.params["iqn"] == [""] else module.params["iqn"]
        if _sync_initiators(
            module,
            array,
            "add_iqns",
            "remove_iqns",
            desired,
            current_connectors.iqns or [],
            f"Change of iSCSI IQNs on host {module.params['name']}",
        ):
            answer = True
    if module.params["wwns"]:
        module.params["wwns"] = [
            wwn.replace(":", "").upper() for wwn in module.params["wwns"]
        ]
        desired = [] if module.params["wwns"] == [""] else module.params["wwns"]
        if _sync_initiators(
            module,
            array,
            "add_wwns",
            "remove_wwns",
            desired,
            current_connectors.wwns or [],
            f"Change of FC WWNs on host {module.params['name']}",
        ):
            answer = True
    return answer


def _connect_new_volume(module, array):
    """Connect volume to host"""
    if not module.check_mode:
        kwargs = {
            "host_names": [module.params["name"]],
            "volume_names": [module.params["volume"]],
        }
        if module.params["lun"]:
            kwargs["connection"] = ConnectionPost(lun=module.params["lun"])
        res = get_with_context(
            array, "post_connections", CONTEXT_API_VERSION, module, **kwargs
        )
        check_response(
            res,
            module,
            f"Failed to connect volume {module.params['volume']} to host {module.params['name']}",
        )
    return True


def _disconnect_volume(module, array):
    """Disconnect volume from host"""
    if not module.check_mode:
        res = get_with_context(
            array,
            "delete_connections",
            CONTEXT_API_VERSION,
            module,
            host_names=[module.params["name"]],
            volume_names=[module.params["volume"]],
        )
        check_response(
            res,
            module,
            f"Failed to disconnect volume {module.params['volume']} from host {module.params['name']}",
        )
    return True


def _set_host_personality(module, array):
    """Set host personality"""
    personality = (
        "" if module.params["personality"] == "delete" else module.params["personality"]
    )
    res = get_with_context(
        array,
        "patch_hosts",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        host=HostPatch(personality=personality),
    )
    check_response(
        res, module, f"Failed to set personality on host {module.params['name']}"
    )


def _set_preferred_array(module, array):
    """Set preferred array list"""
    if module.params["preferred_array"] != ["delete"]:
        preferred_array_list = []
        for preferred_array in module.params["preferred_array"]:
            preferred_array_list.append(Reference(name=preferred_array))
    else:
        preferred_array_list = []
    res = get_with_context(
        array,
        "patch_hosts",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        host=HostPatch(preferred_arrays=preferred_array_list),
    )
    check_response(
        res, module, f"Failed to set preferred arrays on host {module.params['name']}"
    )


def _set_chap_security(module, array):
    """Set CHAP usernames and passwords"""
    pattern = re.compile("[^ ]{12,255}")
    if module.params["host_user"]:
        if not pattern.match(module.params["host_password"]):
            module.fail_json(
                msg="host_password must contain a minimum of 12 and a maximum of 255 characters"
            )
        res = get_with_context(
            array,
            "patch_hosts",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            host=HostPatch(
                chap=Chap(
                    host_user=module.params["host_user"],
                    host_password=module.params["host_password"],
                )
            ),
        )
        check_response(res, module, "Failed to set CHAP host username and password")
    if module.params["target_user"]:
        if not pattern.match(module.params["target_password"]):
            module.fail_json(
                msg="target_password must contain a minimum of 12 and a maximum of 255 characters"
            )
        res = get_with_context(
            array,
            "patch_hosts",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            host=HostPatch(
                chap=Chap(
                    target_user=module.params["target_user"],
                    target_password=module.params["target_password"],
                )
            ),
        )
        check_response(res, module, "Failed to set CHAP target username and password")


def _update_chap_security(module, array, answer=False):
    """Change CHAP usernames and passwords"""
    pattern = re.compile("[^ ]{12,255}")
    chap = get_host(module, array).chap
    if module.params["host_user"]:
        if module.params["host_password"] == "clear":
            # An absent attribute and an empty string both mean "not set"
            if getattr(chap, "host_user", ""):
                answer = True
                if not module.check_mode:
                    res = get_with_context(
                        array,
                        "patch_hosts",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["name"]],
                        host=HostPatch(chap=Chap(host_user="", host_password="")),
                    )
                    check_response(
                        res, module, "Failed to clear CHAP host username and password"
                    )
        else:
            if not pattern.match(module.params["host_password"]):
                module.fail_json(
                    msg="host_password must contain a minimum of 12 and a maximum of 255 characters"
                )
            answer = True
            if not module.check_mode:
                res = get_with_context(
                    array,
                    "patch_hosts",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    host=HostPatch(
                        chap=Chap(
                            host_user=module.params["host_user"],
                            host_password=module.params["host_password"],
                        )
                    ),
                )
                check_response(
                    res, module, "Failed to update CHAP host username and password"
                )
    if module.params["target_user"]:
        if module.params["target_password"] == "clear":
            # An absent attribute and an empty string both mean "not set"
            if getattr(chap, "target_user", ""):
                answer = True
                if not module.check_mode:
                    res = get_with_context(
                        array,
                        "patch_hosts",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["name"]],
                        host=HostPatch(chap=Chap(target_user="", target_password="")),
                    )
                    check_response(
                        res, module, "Failed to clear CHAP target username and password"
                    )
        else:
            if not pattern.match(module.params["target_password"]):
                module.fail_json(
                    msg="target_password must contain a minimum of 12 and a maximum of 255 characters"
                )
            answer = True
            if not module.check_mode:
                res = get_with_context(
                    array,
                    "patch_hosts",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    host=HostPatch(
                        chap=Chap(
                            target_user=module.params["target_user"],
                            target_password=module.params["target_password"],
                        )
                    ),
                )
                check_response(
                    res, module, "Failed to update CHAP target username and password"
                )
    return answer


def _update_host_personality(module, array, answer=False):
    """Change host personality"""
    host = get_host(module, array)
    if not hasattr(host, "personality") and module.params["personality"] != "delete":
        answer = True
        if not module.check_mode:
            res = get_with_context(
                array,
                "patch_hosts",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                host=HostPatch(personality=module.params["personality"]),
            )
            check_response(res, module, "Update host personality")
    if hasattr(host, "personality"):
        if module.params["personality"] == "delete":
            answer = True
            if not module.check_mode:
                res = get_with_context(
                    array,
                    "patch_hosts",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    host=HostPatch(personality=""),
                )
                check_response(res, module, "Host personality deletion")
        elif host.personality != module.params["personality"]:
            answer = True
            if not module.check_mode:
                res = get_with_context(
                    array,
                    "patch_hosts",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    host=HostPatch(personality=module.params["personality"]),
                )
                check_response(res, module, "Host personality change")
    return answer


def _update_preferred_array(module, array, answer=False):
    """Update existing preferred array list"""
    preferred_array = get_host(module, array).preferred_arrays
    if preferred_array == [] and module.params["preferred_array"] != ["delete"]:
        answer = True
        preferred_array_list = []
        for preferred_array in module.params["preferred_array"]:
            preferred_array_list.append(Reference(name=preferred_array))
        if not module.check_mode:
            res = get_with_context(
                array,
                "patch_hosts",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                host=HostPatch(preferred_arrays=preferred_array_list),
            )
            check_response(
                res,
                module,
                f"Preferred array list creation for host {module.params['name']}",
            )
    elif preferred_array != []:
        if module.params["preferred_array"] == ["delete"]:
            answer = True
            if not module.check_mode:
                res = get_with_context(
                    array,
                    "patch_hosts",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    host=HostPatch(preferred_arrays=[]),
                )
                check_response(
                    res,
                    module,
                    f"Preferred array list deletion for {module.params['name']}",
                )
        else:
            current_preferred_array_list = []
            for array_name in preferred_array:
                current_preferred_array_list.append(array_name.name)
            if sorted(current_preferred_array_list) != sorted(
                module.params["preferred_array"]
            ):
                answer = True
                if not module.check_mode:
                    preferred_array_list = []
                    for array_name in module.params["preferred_array"]:
                        preferred_array_list.append(Reference(name=array_name))
                    res = get_with_context(
                        array,
                        "patch_hosts",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["name"]],
                        host=HostPatch(preferred_arrays=preferred_array_list),
                    )
                    check_response(
                        res,
                        module,
                        f"Preferred array list change for {module.params['name']}",
                    )
    return answer


def _set_vlan(module, array):
    res = get_with_context(
        array,
        "patch_hosts",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        host=HostPatch(vlan=module.params["vlan"]),
    )
    if res.status_code != 200:
        module.warn(
            "Failed to set host VLAN ID. Error: {0}".format(res.errors[0].message)
        )


def _update_vlan(module, array):
    changed = False
    host_vlan = getattr(get_host(module, array), "vlan", None)
    if module.params["vlan"] != host_vlan:
        changed = True
        if not module.check_mode:
            res = get_with_context(
                array,
                "patch_hosts",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                host=HostPatch(vlan=module.params["vlan"]),
            )
            check_response(res, module, "Failed to update host VLAN ID")
    return changed


def get_multi_hosts(module, array):
    """Return True is all hosts exist"""
    hosts = []
    for host_num in range(
        module.params["start"], module.params["count"] + module.params["start"]
    ):
        if module.params["suffix"]:
            hosts.append(
                module.params["name"]
                + str(host_num).zfill(module.params["digits"])
                + module.params["suffix"]
            )
        else:
            hosts.append(
                module.params["name"] + str(host_num).zfill(module.params["digits"])
            )
    return len(_get_hosts(module, array, hosts)) == len(hosts)


def _get_hosts(module, array, names):
    kwargs = {"names": names}
    # allow_errors only exists on the hosts GET endpoint from REST 2.38, and is
    # only required alongside context_names (a name absent from the given
    # context otherwise returns 400). It is therefore only sent when a context
    # is in use; without a context, older arrays would reject the unsupported
    # argument (#1016).
    if module.params.get("context"):
        kwargs["allow_errors"] = True
    res = get_with_context(
        array,
        "get_hosts",
        CONTEXT_API_VERSION,
        module,
        **kwargs,
    )
    return list(getattr(res, "items", []) or [])


def _get_named_host(module, array, name):
    hosts = _get_hosts(module, array, [name])
    return hosts[0] if hosts else None


def get_host(module, array):
    """Return host or None"""
    return _get_named_host(module, array, module.params["name"])


def rename_exists(module, array):
    """Determine if rename target already exists"""
    return _get_named_host(module, array, module.params["rename"]) is not None


def make_multi_hosts(module, array):
    """Create multiple hosts"""
    changed = True
    if not module.check_mode:
        hosts = []
        for host_num in range(
            module.params["start"], module.params["count"] + module.params["start"]
        ):
            if module.params["suffix"]:
                hosts.append(
                    module.params["name"]
                    + str(host_num).zfill(module.params["digits"])
                    + module.params["suffix"]
                )
            else:
                hosts.append(
                    module.params["name"] + str(host_num).zfill(module.params["digits"])
                )
        if module.params["personality"]:
            host = HostPost(personality=module.params["personality"])
        else:
            host = HostPost()
        res = get_with_context(
            array, "post_hosts", CONTEXT_API_VERSION, module, names=hosts, host=host
        )
        check_response(
            res,
            module,
            f"Multi-Host {module.params['name']}#{module.params['suffix']} creation",
        )
    module.exit_json(changed=changed)


def make_host(module, array):
    """Create a new host"""
    changed = True
    if not module.check_mode:
        res = get_with_context(
            array,
            "post_hosts",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            host=HostPost(),
        )
        check_response(res, module, f"Host {module.params['name']} creation")
        if module.params["vlan"]:
            _set_vlan(module, array)
        _set_host_initiators(module, array)
        if module.params["personality"]:
            _set_host_personality(module, array)
        if module.params["preferred_array"]:
            _set_preferred_array(module, array)
        if module.params["host_user"] or module.params["target_user"]:
            _set_chap_security(module, array)
        if module.params["volume"]:
            if module.params["lun"]:
                res = get_with_context(
                    array,
                    "post_connections",
                    CONTEXT_API_VERSION,
                    module,
                    host_names=[module.params["name"]],
                    volume_names=[module.params["volume"]],
                    connection=ConnectionPost(lun=module.params["lun"]),
                )
            else:
                res = get_with_context(
                    array,
                    "post_connections",
                    CONTEXT_API_VERSION,
                    module,
                    host_names=[module.params["name"]],
                    volume_names=[module.params["volume"]],
                )
            check_response(res, module, "Volume connection")
    module.exit_json(changed=changed)


def update_host(module, array):
    """Modify a host"""
    changed = False
    renamed = False
    vol_changed = False
    vlan_changed = False
    api_version = get_cached_api_version(array)
    if module.params["state"] == "present":
        if (
            LooseVersion(VLAN_API_VERSION) <= LooseVersion(api_version)
            and module.params["vlan"]
        ):
            vlan_changed = _update_vlan(module, array)
        if module.params["rename"]:
            if not rename_exists(module, array):
                if not module.check_mode:
                    res = get_with_context(
                        array,
                        "patch_hosts",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["name"]],
                        host=HostPatch(name=module.params["rename"]),
                    )
                    check_response(
                        res,
                        module,
                        f"Rename host {module.params['name']} to {module.params['rename']}",
                    )
                    module.params["name"] = module.params["rename"]
                    renamed = True
            else:
                module.warn(
                    "Rename failed. Target hostname {0} already exists. "
                    "Continuing with any other changes...".format(
                        module.params["rename"]
                    )
                )
        init_changed = pers_changed = pref_changed = chap_changed = False
        volumes = list(
            get_with_context(
                array,
                "get_connections",
                CONTEXT_API_VERSION,
                module,
                host_names=[module.params["name"]],
            ).items
        )
        if module.params["iqn"] or module.params["wwns"] or module.params["nqn"]:
            init_changed = _update_host_initiators(module, array)
        if module.params["volume"]:
            current_vols = [vol.volume.name for vol in volumes]
            if not module.params["volume"] in current_vols:
                vol_changed = _connect_new_volume(module, array)
        if module.params["personality"]:
            pers_changed = _update_host_personality(module, array)
        if module.params["preferred_array"]:
            pref_changed = _update_preferred_array(module, array)
        if module.params["target_user"] or module.params["host_user"]:
            chap_changed = _update_chap_security(module, array)
        changed = (
            init_changed
            or vol_changed
            or pers_changed
            or pref_changed
            or chap_changed
            or vlan_changed
            or renamed
        )
    else:
        if module.params["volume"]:
            volumes = list(
                get_with_context(
                    array,
                    "get_connections",
                    CONTEXT_API_VERSION,
                    module,
                    host_names=[module.params["name"]],
                ).items
            )
            current_vols = [vol.volume.name for vol in volumes]
            if module.params["volume"] in current_vols:
                vol_changed = _disconnect_volume(module, array)
            changed = vol_changed
    module.exit_json(changed=changed)


def delete_host(module, array):
    """Delete a host"""
    changed = True
    if not module.check_mode:
        host_res = get_host(module, array)
        has_hg = hasattr(host_res.host_group, "name")
        if has_hg:
            host_group_name = host_res.host_group.name
            res = get_with_context(
                array,
                "delete_host_groups_hosts",
                CONTEXT_API_VERSION,
                module,
                group_names=[host_group_name],
                member_names=[module.params["name"]],
            )
            check_response(
                res,
                module,
                f"Removing host {module.params['name']} from hostgroup",
            )
        volumes = list(
            get_with_context(
                array,
                "get_connections",
                CONTEXT_API_VERSION,
                module,
                host_names=[module.params["name"]],
            ).items
        )
        current_vols = [vol.volume.name for vol in volumes]
        if current_vols:
            res = get_with_context(
                array,
                "delete_connections",
                CONTEXT_API_VERSION,
                module,
                host_names=[module.params["name"]],
                volume_names=current_vols,
            )
            check_response(res, module, f"Host {module.params['name']} volume detach")
        res = get_with_context(
            array,
            "delete_hosts",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        )
        check_response(res, module, f"Host {module.params['name']} deletion")
    module.exit_json(changed=changed)


def move_host(module, array):
    """Move host between realms and the local array"""
    if module.params["context"] != "":
        module.fail_json(msg="context is not yet supported for host move function")
    local_array = list(array.get_arrays().items)[0].name
    # current_realm = ""
    if len(module.params["move"]) > 1 and len(module.params["move"]) != module.params[
        "move"
    ].count("local"):
        module.fail_json(msg="Cannot mix local with another realm in move target list")
    if "local" in module.params["move"] and "::" not in module.params["name"]:
        module.fail_json(msg="host must be provided with current realm name")
    # if "::" in module.params["name"]:
    #    current_realm = module.params["name"].split("::")[0]
    current_connections = get_host(module, array).connection_count
    if current_connections > 0:
        module.fail_json(msg="Hosts cannot be moved with existing volume connections.")
    changed = True
    if not module.check_mode:
        if "local" in module.params["move"]:
            res = get_with_context(
                array,
                "patch_hosts",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                from_member_names=[module.params["name"].split("::")[0]],
                to_member_names=[local_array],
                modify_resource_access=module.params["modify_resource_access"],
                host=HostPatch(),
            )
            check_response(
                res,
                module,
                f"Failed to move host {module.params['name']} to local array",
            )
        else:
            res = get_with_context(
                array,
                "get_realms",
                REALMS_CONTEXT_VERSION,
                module,
                names=module.params["move"],
            )
            if res.status_code != 200:
                module.fail_json(
                    msg="Move target(s) error: {0}".format(res.errors[0].message)
                )
            if "::" not in module.params["name"]:
                source_realm = local_array
            else:
                source_realm = module.params["name"].split("::")[0]
            res = get_with_context(
                array,
                "patch_hosts",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                from_member_names=[source_realm],
                to_member_names=module.params["move"],
                modify_resource_access=module.params["modify_resource_access"],
                host=HostPatch(),
            )
            check_response(
                res,
                module,
                f"Failed to move host {module.params['name']} to realm {module.params['move']}",
            )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True, aliases=["host"]),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            protocol=dict(
                type="str",
                choices=["fc", "iscsi", "nvme", "mixed"],
                removed_from_collection="everpure.flasharray",
                removed_in_version="2.0.0",
            ),
            nqn=dict(type="list", elements="str"),
            iqn=dict(type="list", elements="str"),
            wwns=dict(type="list", elements="str"),
            host_password=dict(type="str", no_log=True),
            host_user=dict(type="str"),
            target_password=dict(type="str", no_log=True),
            target_user=dict(type="str"),
            volume=dict(type="str"),
            rename=dict(type="str"),
            lun=dict(type="int"),
            count=dict(type="int"),
            start=dict(type="int", default=0),
            digits=dict(type="int", default=1),
            suffix=dict(type="str"),
            personality=dict(
                type="str",
                default="",
                choices=[
                    "hpux",
                    "vms",
                    "aix",
                    "esxi",
                    "solaris",
                    "hitachi-vsp",
                    "oracle-vm-server",
                    "nutanix-mgmt",
                    "nutanix-cluster",
                    "delete",
                    "",
                ],
            ),
            preferred_array=dict(type="list", elements="str"),
            vlan=dict(type="str"),
            context=dict(type="str", default=""),
            move=dict(type="list", elements="str"),
            modify_resource_access=dict(
                type="str", default="none", choices=["none", "create", "delete"]
            ),
        )
    )

    required_together = [
        ["host_password", "host_user"],
        ["target_password", "target_user"],
    ]
    mutually_exclusive = [
        ["nqn", "iqn"],
        ["nqn", "wwns"],
    ]

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=True,
        required_together=required_together,
        mutually_exclusive=mutually_exclusive,
    )

    if not HAS_PURESTORAGE:
        module.fail_json(
            msg="py-pure-client sdk is required to support 'vlan' parameter"
        )
    array = get_array(module)
    api_version = get_cached_api_version(array)
    pattern = re.compile("^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
    if module.params["rename"]:
        rename = module.params["rename"]
        if "::" in module.params["rename"]:
            rename = module.params["rename"].split("::")[1]
        if not pattern.match(rename):
            module.fail_json(
                msg="Rename value {0} does not conform to naming convention".format(
                    module.params["rename"]
                )
            )
    host_name = module.params["name"]
    if "::" in module.params["name"]:
        host_name = module.params["name"].split("::")[1]
    if not pattern.match(host_name):
        module.fail_json(
            msg="Host name {0} does not conform to naming convention".format(
                module.params["name"]
            )
        )
    if _is_cbs(array):
        if module.params["wwns"] or module.params["nqn"]:
            module.fail_json(msg="Cloud Block Store only supports iSCSI as a protocol")
    state = module.params["state"]
    if module.params["suffix"]:
        suffix_len = len(module.params["suffix"])
    else:
        suffix_len = 0
    if (
        LooseVersion(VLAN_API_VERSION) > LooseVersion(api_version)
        and module.params["vlan"]
    ):
        module.fail_json(
            msg="'vlan' parameter is not supported until Purity//FA 6.3.4 or higher"
        )
    if module.params["personality"] in [
        "nutanix-mgmt",
        "nutanix-cluster",
    ] and LooseVersion(NUTANIX_API_VERSION) > LooseVersion(api_version):
        module.fail_json(
            msg="'{0}' personality is not supported until REST API 2.50 or higher".format(
                module.params["personality"]
            )
        )
    if module.params["vlan"] and module.params["vlan"] not in ["any", "untagged"]:
        try:
            vlan = int(module.params["vlan"])
            if vlan not in range(1, 4094):
                module.fail_json(msg="VLAN must be set to a number between 1 and 4094")
        except Exception:
            module.fail_json(
                msg="Invalid string for VLAN. Must be 'any', 'untagged' or a number between 1 and 4094"
            )
    if module.params["count"]:
        if module.params["digits"] and module.params["digits"] not in range(1, 10):
            module.fail_json(msg="'digits' must be in the range of 1 to 10")
        if module.params["start"] < 0:
            module.fail_json(msg="'start' must be a positive number")
        if "::" in module.params["name"]:
            host_name = module.params["name"].split("::")[1]
        if not pattern.match(host_name):
            module.fail_json(
                msg="Host name pattern {0} does not conform to naming convention".format(
                    module.params["name"]
                )
            )
        elif module.params["suffix"] and not pattern.match(module.params["suffix"]):
            module.fail_json(
                msg="Suffix pattern {0} does not conform to naming convention".format(
                    module.params["suffix"]
                )
            )
        elif (
            len(module.params["name"])
            + max(
                len(str(module.params["count"] + module.params["start"])),
                module.params["digits"],
            )
            + suffix_len
            > 63
        ):
            module.fail_json(msg="Host name length exceeds maximum allowed")
        host = get_multi_hosts(module, array)
        if state == "absent":
            module.fail_json(
                msg="'count' is only supported with state=present; "
                "delete hosts individually by name"
            )
        if not host and state == "present":
            make_multi_hosts(module, array)
    else:
        host = get_host(module, array)
        if module.params["lun"] and not 1 <= module.params["lun"] <= 4095:
            module.fail_json(
                msg="LUN ID of {0} is out of range (1 to 4095)".format(
                    module.params["lun"]
                )
            )
        if module.params["volume"]:
            res = get_with_context(
                array,
                "get_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["volume"]],
            )
            if res.status_code != 200:
                module.exit_json(changed=False)
        if module.params["preferred_array"] and module.params["preferred_array"] != [
            "delete"
        ]:
            connections = get_with_context(
                array,
                "get_array_connections",
                CONTEXT_API_VERSION,
                module,
                total_item_count=True,
            )
            if connections.status_code != 200:
                module.fail_json(
                    msg="Failed to get existing array connections. Error: {0}".format(
                        connections.errors[0].message
                    )
                )
            if connections.total_item_count == 0:
                module.fail_json(
                    msg="No target arrays connected to source array - preferred arrays not possible."
                )
            else:
                all_connected_arrays = list(
                    get_with_context(
                        array, "get_array_connections", CONTEXT_API_VERSION, module
                    ).items
                )
                current_arrays = [
                    list(
                        get_with_context(
                            array, "get_arrays", CONTEXT_API_VERSION, module
                        ).items
                    )[0].name
                ]
                for current_array in all_connected_arrays:
                    if current_array.type == "sync-replication":
                        current_arrays.append(current_array.name)
            for array_to_connect in module.params["preferred_array"]:
                if array_to_connect not in current_arrays:
                    module.fail_json(
                        msg="Array {0} is not a synchronously connected array.".format(
                            array_to_connect
                        )
                    )

        if (
            host is None
            and state == "present"
            and not module.params["rename"]
            and not module.params["move"]
        ):
            make_host(module, array)
        elif host is None and state == "present" and module.params["rename"]:
            module.exit_json(changed=False)
        elif host and state == "present" and not module.params["move"]:
            update_host(module, array)
        elif host and state == "present" and module.params["move"]:
            move_host(module, array)
        elif host and state == "absent" and module.params["volume"] is not None:
            update_host(module, array)
        elif host and state == "absent" and not module.params["volume"]:
            delete_host(module, array)
        elif host is None and state == "absent":
            module.exit_json(changed=False)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
