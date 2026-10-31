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
module: purefa_connect
version_added: '1.0.0'
short_description: Manage replication connections between two FlashArrays
description:
- Manage array connections to specified target array
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  state:
    description:
    - Create or delete array connection
    default: present
    type: str
    choices: [ absent, present ]
  target_url:
    description:
    - Management IP address of remote array.
    type: str
    required: true
  target_api:
    description:
    - API token for target array
    type: str
  connection:
    description:
    - Type of connection between arrays.
    type: str
    choices: [ sync, async ]
    default: async
  transport:
    description:
    - Type of transport protocol to use for replication
    type: str
    choices: [ ip, fc ]
    default: ip
  encrypted:
    description:
    - Defines if the array connection will be encrypted
    type: bool
    default: false
    version_added: '1.30.0'
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
    version_added: '1.39.0'
  renew_key:
    description:
    - Update array connection with a new encryption key.
    - If set to true, other array connection attributes will not be modified.
    type: bool
    default: false
    version_added: '1.40.0'
  refresh:
    description:
    - Array will attempt to communicate with the connection peer in order to update
      the connection attributes on both arrays with any changes that have occurred.
    - If set to true, other array connection attributes will not be modified.
    type: bool
    default: false
    version_added: '1.40.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create an IPv4 async connection to remote array
  everpure.flasharray.purefa_connect:
    target_url: 10.10.10.20
    target_api: 9c0b56bc-f941-f7a6-9f85-dcc3e9a8f7d6
    connection: async
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
- name: Create an IPv6 async connection to remote array
  everpure.flasharray.purefa_connect:
    target_url: "[2001:db8:abcd:12::10]"
    target_api: 9c0b56bc-f941-f7a6-9f85-dcc3e9a8f7d6
    connection: async
    fa_url: "[2001:db8:abcd:12::13]"
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
- name: Delete connection to remote array
  everpure.flasharray.purefa_connect:
    state: absent
    target_url: 10.10.10.20
    target_api: 9c0b56bc-f941-f7a6-9f85-dcc3e9a8f7d6
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PYPURECLIENT = True
try:
    from pypureclient.flasharray import (
        ArrayConnectionPost,
        ArrayConnectionPatch,
        Client,
    )
except ImportError:
    HAS_PYPURECLIENT = False

HAS_DISTRO = True
try:
    import distro
except ImportError:
    HAS_DISTRO = False

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
    delete_with_context,
    get_with_context,
    patch_with_context,
    post_with_context,
)
import platform
import socket

ENCRYPT_VERSION = "2.33"
CONTEXT_VERSION = "2.38"


def _lookup(address):
    """Perform Reverse DNS lookup on IP address"""
    fqdn = socket.getnameinfo((address, 0), 0)[0]
    shortname = fqdn.split(".")[0]
    return shortname, fqdn


def _check_connected(module, array):
    """Return the existing replication connection to the target, or None

    A fleet-management connection to the same peer shares its management
    address, so only replication connections are candidates; otherwise an
    existing sync connection would be reported as needing a type change.
    """
    res = get_with_context(array, "get_array_connections", CONTEXT_VERSION, module)
    if res.status_code != 200:
        return None
    target_url = module.params["target_url"].strip("[]")
    addresses = {target_url}
    try:
        addresses.update(_lookup(target_url))
    except (OSError, UnicodeError):
        pass
    for target in list(res.items):
        if getattr(target, "type", None) == "fleet-management":
            continue
        if getattr(target, "management_address", None) in addresses:
            return target
    return None


def break_connection(module, array, target_array):
    """Break connection between arrays"""
    changed = True
    res = get_with_context(array, "get_arrays", CONTEXT_VERSION, module)
    source_array = list(res.items)[0].name
    if getattr(target_array, "management_address", None) is None:
        module.fail_json(
            msg="disconnect can only happen from the array that formed the connection"
        )
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_array_connections",
            CONTEXT_VERSION,
            module,
            names=[target_array.name],
        )
        check_response(
            res, module, f"Failed to disconnect {target_array.name} from {source_array}"
        )
    module.exit_json(changed=changed)


def update_connection(module, array, target_array):
    """Change existing array connection"""
    changed = False
    if HAS_DISTRO:
        user_agent = "%(base)s %(class)s/%(version)s (%(platform)s)" % {
            "base": "Ansible",
            "class": __name__,
            "version": 1.5,
            "platform": distro.name(pretty=True),
        }
    else:
        user_agent = "%(base)s %(class)s/%(version)s (%(platform)s)" % {
            "base": "Ansible",
            "class": __name__,
            "version": 1.5,
            "platform": platform.platform(),
        }
    api_version = array.get_rest_version()
    res = get_with_context(array, "get_arrays", CONTEXT_VERSION, module)
    source_array = list(res.items)[0].name
    #
    # Special cases
    #
    if module.params["renew_key"]:
        # No other attributes can be changed when doing this
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_array_connections",
                CONTEXT_VERSION,
                module,
                names=[target_array.name],
                renew_encryption_key=True,
                array_connection=ArrayConnectionPatch(),
            )
            check_response(
                res,
                module,
                f"Failed to renew encryption key for connection to {target_array.name}",
            )
        module.exit_json(changed=changed)
    if module.params["refresh"]:
        # No other attributes can be changed when doing this
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_array_connections",
                CONTEXT_VERSION,
                module,
                names=[target_array.name],
                refresh=True,
                array_connection=ArrayConnectionPatch(),
            )
            check_response(
                res, module, f"Failed to refresh connection to {target_array.name}"
            )
        module.exit_json(changed=changed)
    #
    # Special cases complete
    #
    if LooseVersion(ENCRYPT_VERSION) <= LooseVersion(api_version):
        if module.params["encrypted"]:
            encrypted = "encrypted"
        else:
            encrypted = "unencrypted"
        if target_array.encryption != encrypted:
            # Changing the encryption type requires the connection key
            remote_system = Client(
                target=module.params["target_url"],
                api_token=module.params["target_api"],
                user_agent=user_agent,
            )
            connection_key = list(
                remote_system.get_array_connections_connection_key(
                    encrypted=module.params["encrypted"]
                ).items
            )[0].connection_key
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_array_connections",
                    CONTEXT_VERSION,
                    module,
                    names=[target_array.name],
                    array_connection=ArrayConnectionPatch(
                        encryption=encrypted, connection_key=connection_key
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to change encryption for {target_array.name}",
                )
    if module.params["connection"] != target_array.type:
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_array_connections",
                CONTEXT_VERSION,
                module,
                names=[target_array.name],
                array_connection=ArrayConnectionPatch(type=module.params["connection"]),
            )
            check_response(
                res,
                module,
                f"Failed to change connection type for {target_array.name}",
            )
    module.exit_json(changed=changed)


def create_connection(module, array):
    """Create connection between arrays"""
    changed = True
    api_version = array.get_rest_version()
    if HAS_DISTRO:
        user_agent = "%(base)s %(class)s/%(version)s (%(platform)s)" % {
            "base": "Ansible",
            "class": __name__,
            "version": 1.5,
            "platform": distro.name(pretty=True),
        }
    else:
        user_agent = "%(base)s %(class)s/%(version)s (%(platform)s)" % {
            "base": "Ansible",
            "class": __name__,
            "version": 1.5,
            "platform": platform.platform(),
        }
    remote_system = Client(
        target=module.params["target_url"],
        api_token=module.params["target_api"],
        user_agent=user_agent,
    )
    try:
        connections = remote_system.get_array_connections_connection_key(
            encrypted=module.params["encrypted"]
        )
    except TypeError:
        if module.params["encrypted"]:
            module.warn(
                "Remote array version of Purity//FA does not support "
                "encryption. Continuing without encryption"
            )
        connections = remote_system.get_array_connections_connection_key()

    connection_key = list(connections.items)[0].connection_key
    if LooseVersion(ENCRYPT_VERSION) <= LooseVersion(api_version):
        if module.params["encrypted"]:
            encrypted = "encrypted"
        else:
            encrypted = "unencrypted"
        array_connection = ArrayConnectionPost(
            type=module.params["connection"].lower(),
            management_address=module.params["target_url"].strip("[]"),
            replication_transport=module.params["transport"],
            connection_key=connection_key,
            encryption=encrypted,
        )
    else:
        array_connection = ArrayConnectionPost(
            type=module.params["connection"].lower(),
            management_address=module.params["target_url"].strip("[]"),
            replication_transport=module.params["transport"],
            connection_key=connection_key,
        )
    if not module.check_mode:
        res = post_with_context(
            array,
            "post_array_connections",
            CONTEXT_VERSION,
            module,
            array_connection=array_connection,
        )
        check_response(res, module, "Array Connection")
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            connection=dict(type="str", default="async", choices=["async", "sync"]),
            transport=dict(type="str", default="ip", choices=["ip", "fc"]),
            target_url=dict(type="str", required=True),
            target_api=dict(type="str"),
            encrypted=dict(type="bool", default=False),
            renew_key=dict(type="bool", default=False),
            refresh=dict(type="bool", default=False),
            context=dict(type="str", default=""),
        )
    )

    required_if = [("state", "present", ["target_api"])]

    module = AnsibleModule(
        argument_spec, required_if=required_if, supports_check_mode=True
    )

    if not HAS_PYPURECLIENT:
        module.fail_json(msg="pypureclient sdk is required for this module")

    state = module.params["state"]
    array = get_array(module)
    target_array = _check_connected(module, array)
    # REST 2 changed connection names, so update
    module.params["connection"] = module.params["connection"] + "-replication"

    if state == "present" and target_array is None:
        create_connection(module, array)
    elif state == "present" and target_array is not None:
        update_connection(module, array, target_array)
    elif state == "absent" and target_array is not None:
        break_connection(module, array, target_array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
