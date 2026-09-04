#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2026, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_server
version_added: '1.45.0'
short_description: Manage Everpure FlashArray file servers
description:
- Create, rename, reconfigure and delete file servers on Everpure FlashArrays.
- A file server is the identity a FlashArray presents its file protocols
  through. It ties together the DNS configuration used to resolve and publish
  the server, and the directory service the server authenticates against.
- The objects a file server serves are managed by their own modules -
  M(everpure.flasharray.purefa_fs) for file systems,
  M(everpure.flasharray.purefa_directory) for managed directories,
  M(everpure.flasharray.purefa_export) for exports and
  M(everpure.flasharray.purefa_policy) for the NFS, SMB and snapshot policies
  applied to them.
- The DNS and directory service configurations a file server refers to are
  managed by M(everpure.flasharray.purefa_dns) and
  M(everpure.flasharray.purefa_ds).
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the file server.
    type: str
    required: true
  state:
    description:
    - Define whether the file server should exist or not.
    default: present
    type: str
    choices: [ absent, present ]
  rename:
    description:
    - Value to rename the specified file server to.
    type: str
  dns:
    description:
    - Name of the DNS configuration the file server uses.
    - This is a DNS configuration with I(service=file), as created by
      M(everpure.flasharray.purefa_dns).
    - A new file server is given the array's management DNS configuration by
      default, so this is for moving one onto a DNS configuration of its own.
    - Set to an empty string to detach the current DNS configuration.
    - Not enough on its own to create a file server. See I(directory_service).
    type: str
  directory_service:
    description:
    - Name of the directory service configuration the file server
      authenticates against, as managed by M(everpure.flasharray.purefa_ds).
    - This is a directory service the file server can see. The array's own
      C(management) directory service is not one of them.
    - Set to an empty string to detach the current directory service.
    type: str
  local_directory_service:
    description:
    - Name of an existing local directory service to associate with the file
      server.
    - A local directory service belongs to one file server at a time, so this
      fails if another file server already has it.
    - Mutually exclusive with I(create_local_directory_service).
    type: str
  create_local_directory_service:
    description:
    - Name of a local directory service for the array to create and associate
      with the file server.
    - Only applies when the file server is created. Ignored for a file server
      that already exists.
    - Mutually exclusive with I(local_directory_service).
    type: str
  network_interfaces:
    description:
    - Names of the network interfaces the file server is reachable on, such as
      the file VIFs created by M(everpure.flasharray.purefa_network).
    - Declarative. Interfaces in the list that are not attached to this file
      server are attached, and interfaces attached to it that are not in the
      list are detached. An empty list detaches all of them.
    - Omit the option to leave the file server's interfaces alone. Detaching an
      interface stops clients reaching the file server through it, so this only
      ever acts on a task that names the interfaces explicitly.
    - An interface can be attached to one file server at a time.
    type: list
    elements: str
  cascade_delete:
    description:
    - Resource types to delete along with the file server, for objects that
      would otherwise block its deletion.
    - C(directory-services) is the only value the array accepts.
    - This does not remove a local directory service created for the server,
      which outlives it and has to be deleted separately.
    - Only applies when I(state=absent).
    type: list
    elements: str
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
notes:
- Requires Purity//FA REST API 2.44 or higher, which is where file servers
  first appear.
- A file server cannot be created from a name alone. One of
  I(directory_service), I(local_directory_service) or
  I(create_local_directory_service) is required.
"""

EXAMPLES = r"""
- name: Create file server the way the GUI does - network, DNS and directory service
  everpure.flasharray.purefa_server:
    name: filesvr1
    dns: filesvr1-dns
    create_local_directory_service: filesvr1-lds
    network_interfaces:
      - filevif1
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create file server joined to an existing directory service
  everpure.flasharray.purefa_server:
    name: filesvr2
    directory_service: filesvr2-ds
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Move an existing file server onto a different DNS configuration
  everpure.flasharray.purefa_server:
    name: filesvr2
    dns: new-dns
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Detach the directory service from a file server
  everpure.flasharray.purefa_server:
    name: filesvr2
    directory_service: ""
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename file server
  everpure.flasharray.purefa_server:
    name: filesvr2
    rename: filesvr3
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete file server, along with the directory services only it uses
  everpure.flasharray.purefa_server:
    name: filesvr1
    cascade_delete:
      - directory-services
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        NetworkInterfacePatch,
        Reference,
        ServerPatch,
        ServerPost,
    )
except ImportError:
    HAS_PURESTORAGE = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_api_version,
    check_response,
    get_with_context,
)

# File servers, and every option this module sends with them, arrived together
# in this version - there is no partial support to work around
SERVER_API_VERSION = "2.44"

# The settings that are references to another object, mapped to the field each
# is sent and read as
REFERENCE_OPTIONS = {
    "dns": "dns",
    "directory_service": "directory_services",
    "local_directory_service": "local_directory_service",
}
# The two the API models as a list of at most one reference, rather than as a
# single reference. Only these can be detached, by sending the empty list.
LIST_FIELDS = ("dns", "directory_services")
# The array refuses to create a file server that has none of these, with
# "At least one of the arguments is required". A DNS configuration on its own
# does not satisfy it - the array attaches the management one by default
# anyway - so the create is refused here with a message that names the options.
CREATE_REQUIRES = (
    "directory_service",
    "local_directory_service",
    "create_local_directory_service",
)


def _reference_name(server, field):
    """Return the name a server's reference field points at, or None"""
    value = getattr(server, field, None)
    if field in LIST_FIELDS:
        value = next(iter(value or []), None)
    return getattr(value, "name", None)


def _reference_value(field, name):
    """Build the value a reference field is sent as

    An empty name detaches what is there, which the API expresses as the empty
    list. main() refuses an empty name for the single-reference field, so the
    empty case only arises for the two list fields.
    """
    if field in LIST_FIELDS:
        return [Reference(name=name)] if name else []
    return Reference(name=name)


def _read_server(module, array, name):
    """Return the named file server, or None if the array does not have it"""
    res = get_with_context(
        array, "get_servers", SERVER_API_VERSION, module, names=[name]
    )
    if res.status_code != 200:
        return None
    return next(iter(list(res.items)), None)


def _attached_interfaces(module, array, server_name):
    """Names of the network interfaces currently attached to a file server

    A network interface names the servers it is attached to, rather than a
    server naming its interfaces, so this reads the interfaces and picks out
    the ones pointing back.
    """
    res = get_with_context(array, "get_network_interfaces", SERVER_API_VERSION, module)
    check_response(res, module, "Failed to list network interfaces")
    attached = []
    for interface in list(res.items):
        for reference in getattr(interface, "attached_servers", None) or []:
            if getattr(reference, "name", None) == server_name:
                attached.append(interface.name)
    return sorted(attached)


def _attach_interface(module, array, interface, server_name):
    """Attach an interface to a file server, or detach it when name is None"""
    res = get_with_context(
        array,
        "patch_network_interfaces",
        SERVER_API_VERSION,
        module,
        names=[interface],
        network=NetworkInterfacePatch(
            attached_servers=[Reference(name=server_name)] if server_name else []
        ),
    )
    action = "attach" if server_name else "detach"
    check_response(
        res,
        module,
        "Failed to {0} network interface {1}".format(action, interface),
    )


def _reconcile_interfaces(module, array, server_name):
    """Make the file server's attached interfaces match the task

    Returns whether anything needed changing. Does nothing at all when the
    task did not name the option, so a task that says nothing about networking
    never detaches an interface.
    """
    wanted = module.params["network_interfaces"]
    if wanted is None:
        return False
    wanted = sorted(set(wanted))
    current = _attached_interfaces(module, array, server_name)
    to_attach = [i for i in wanted if i not in current]
    to_detach = [i for i in current if i not in wanted]
    if not to_attach and not to_detach:
        return False
    if not module.check_mode:
        for interface in to_attach:
            _attach_interface(module, array, interface, server_name)
        for interface in to_detach:
            _attach_interface(module, array, interface, None)
    return True


def _requested_references(module):
    """The reference settings the task asked for, as API field names

    Only the options the task actually supplied are returned, so a task that
    does not mention a setting leaves it alone.
    """
    requested = {}
    for option, field in REFERENCE_OPTIONS.items():
        if module.params[option] is not None:
            requested[field] = module.params[option]
    return requested


def create_server(module, array):
    """Create a file server"""
    changed = True
    if not any(module.params[option] for option in CREATE_REQUIRES):
        module.fail_json(
            msg="Creating file server {0} requires one of {1}. The array "
            "refuses a file server created with none of them.".format(
                module.params["name"], ", ".join(CREATE_REQUIRES)
            )
        )
    if not module.check_mode:
        requested = _requested_references(module)
        kwargs = {"names": [module.params["name"]]}
        if requested:
            kwargs["server"] = ServerPost(
                **{
                    field: _reference_value(field, name)
                    for field, name in requested.items()
                }
            )
        if module.params["create_local_directory_service"]:
            kwargs["create_local_directory_service"] = module.params[
                "create_local_directory_service"
            ]
        res = get_with_context(
            array, "post_servers", SERVER_API_VERSION, module, **kwargs
        )
        check_response(
            res,
            module,
            "Failed to create file server {0}".format(module.params["name"]),
        )
    # The interfaces are attached after the server exists, since the
    # attachment is a property of the interface pointing at it
    _reconcile_interfaces(module, array, module.params["name"])
    module.exit_json(changed=changed)


def update_server(module, array, server):
    """Update the settings of an existing file server"""
    changed = False
    patch = {}
    for field, name in _requested_references(module).items():
        if _reference_name(server, field) != (name or None):
            patch[field] = _reference_value(field, name)
    if patch:
        changed = True
        if not module.check_mode:
            res = get_with_context(
                array,
                "patch_servers",
                SERVER_API_VERSION,
                module,
                names=[module.params["name"]],
                server=ServerPatch(**patch),
            )
            check_response(
                res,
                module,
                "Failed to update file server {0}".format(module.params["name"]),
            )
    if _reconcile_interfaces(module, array, module.params["name"]):
        changed = True
    module.exit_json(changed=changed)


def rename_server(module, array):
    """Rename a file server"""
    changed = True
    if _read_server(module, array, module.params["rename"]):
        module.fail_json(
            msg="Target file server {0} already exists".format(module.params["rename"])
        )
    if not module.check_mode:
        res = get_with_context(
            array,
            "patch_servers",
            SERVER_API_VERSION,
            module,
            names=[module.params["name"]],
            server=ServerPatch(name=module.params["rename"]),
        )
        check_response(
            res,
            module,
            "Failed to rename file server {0} to {1}".format(
                module.params["name"], module.params["rename"]
            ),
        )
    module.exit_json(changed=changed)


def delete_server(module, array):
    """Delete a file server"""
    changed = True
    if not module.check_mode:
        kwargs = {"names": [module.params["name"]]}
        if module.params["cascade_delete"]:
            kwargs["cascade_delete"] = module.params["cascade_delete"]
        res = get_with_context(
            array, "delete_servers", SERVER_API_VERSION, module, **kwargs
        )
        check_response(
            res,
            module,
            "Failed to delete file server {0}".format(module.params["name"]),
        )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            rename=dict(type="str"),
            dns=dict(type="str"),
            directory_service=dict(type="str"),
            local_directory_service=dict(type="str"),
            create_local_directory_service=dict(type="str"),
            network_interfaces=dict(type="list", elements="str"),
            cascade_delete=dict(type="list", elements="str"),
            context=dict(type="str", default=""),
        )
    )

    # The API refuses these two together: one names a local directory service
    # to create, the other an existing one to attach
    mutually_exclusive = [["local_directory_service", "create_local_directory_service"]]

    module = AnsibleModule(
        argument_spec,
        mutually_exclusive=mutually_exclusive,
        supports_check_mode=True,
    )

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    # dns and directory_service are lists of at most one reference, which the
    # empty list detaches. local_directory_service is a single reference, and
    # the API documents no value that clears it, so an empty string is refused
    # here rather than sent as a guess.
    if module.params["local_directory_service"] == "":
        module.fail_json(
            msg="local_directory_service cannot be set to an empty string. "
            "The REST API provides no way to detach a local directory service "
            "from a file server."
        )

    array = get_array(module)
    check_api_version(array, SERVER_API_VERSION, module, "File servers")

    state = module.params["state"]
    server = _read_server(module, array, module.params["name"])

    if state == "present" and module.params["rename"]:
        if server:
            rename_server(module, array)
        elif _read_server(module, array, module.params["rename"]):
            # Already renamed, so re-running the same task has nothing left to
            # do. Creating the old name back would be the opposite of what was
            # asked for.
            module.exit_json(changed=False)
        else:
            module.fail_json(
                msg="File server {0} not found to rename".format(module.params["name"])
            )
    elif state == "present" and not server:
        create_server(module, array)
    elif state == "present":
        update_server(module, array, server)
    elif state == "absent" and server:
        delete_server(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
