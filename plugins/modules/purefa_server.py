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
    - Set to an empty string to detach the current DNS configuration.
    type: str
  directory_service:
    description:
    - Name of the directory service configuration the file server
      authenticates against, as managed by M(everpure.flasharray.purefa_ds).
    - Set to an empty string to detach the current directory service.
    type: str
  local_directory_service:
    description:
    - Name of an existing local directory service to associate with the file
      server.
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
  cascade_delete:
    description:
    - Resource types to delete along with the file server, for objects that
      would otherwise block its deletion.
    - C(directory-services) is the value documented by the REST API.
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
"""

EXAMPLES = r"""
- name: Create file server, having the array create its local directory service
  everpure.flasharray.purefa_server:
    name: filesvr1
    dns: filesvr1-dns
    create_local_directory_service: filesvr1-lds
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create file server joined to an existing directory service
  everpure.flasharray.purefa_server:
    name: filesvr2
    dns: filesvr2-dns
    directory_service: data
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
    from pypureclient.flasharray import Reference, ServerPatch, ServerPost
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
    module.exit_json(changed=changed)


def rename_server(module, array):
    """Rename a file server"""
    changed = True
    res = get_with_context(
        array,
        "get_servers",
        SERVER_API_VERSION,
        module,
        names=[module.params["rename"]],
    )
    if res.status_code == 200 and list(res.items):
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
    res = get_with_context(
        array,
        "get_servers",
        SERVER_API_VERSION,
        module,
        names=[module.params["name"]],
    )
    server = next(iter(list(res.items)), None) if res.status_code == 200 else None

    if state == "present" and not server:
        create_server(module, array)
    elif state == "present" and module.params["rename"]:
        rename_server(module, array)
    elif state == "present":
        update_server(module, array, server)
    elif state == "absent" and server:
        delete_server(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
