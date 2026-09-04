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
module: purefa_lds
version_added: '1.45.0'
short_description: Manage Everpure FlashArray local directory services
description:
- Create, rename, reconfigure and delete local directory services on Everpure
  FlashArrays.
- A local directory service holds users and groups on the array itself, for
  file serving that does not authenticate against an external directory. It is
  attached to a file server, which is managed by
  M(everpure.flasharray.purefa_server).
- Every local directory service is created with its own built-in users and
  groups - C(Administrator) and C(Guest), and the C(Administrators),
  C(Guests), C(Backup Operators) and C(Audit Operators) groups. Those cannot be
  deleted, and their names are therefore repeated in every local directory
  service on the array.
- External directory services are managed by
  M(everpure.flasharray.purefa_ds).
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the local directory service
    type: str
    required: true
  state:
    description:
    - Define whether the local directory service should exist or not.
    - Deleting a local directory service also deletes every user and group it
      holds. See the note on I(state=absent).
    default: present
    choices: [ absent, present ]
    type: str
  domain:
    description:
    - Domain name the local directory service serves.
    - The array defaults this to the name of the local directory service when
      it is created without one.
    - Two local directory services may share a domain.
    type: str
  rename:
    description:
    - Value to rename the specified local directory service to
    - Re-running a rename task reports no change, as long as the local
      directory service is already known by the new name.
    type: str
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
- Supported from Purity//FA 6.8.0 or higher.
- Deleting a local directory service is not recoverable. The array removes
  every user and group inside it at the same time, including any password set
  on those users.
- A local directory service that is in use by a file server cannot be deleted.
  Detach it with M(everpure.flasharray.purefa_server) first.
"""

EXAMPLES = r"""
- name: Create local directory service foo
  everpure.flasharray.purefa_lds:
    name: foo
    domain: foo.example.com
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create local directory service bar, letting the array set the domain
  everpure.flasharray.purefa_lds:
    name: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Change the domain of local directory service foo
  everpure.flasharray.purefa_lds:
    name: foo
    domain: new.example.com
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename local directory service foo to bar
  everpure.flasharray.purefa_lds:
    name: foo
    rename: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete local directory service foo and everything in it
  everpure.flasharray.purefa_lds:
    name: foo
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        LocalDirectoryService,
        LocalDirectoryServicePost,
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
    delete_with_context,
    get_with_context,
    patch_with_context,
    post_with_context,
)

# Local directory services became manageable in their own right in this
# version. The users and groups inside them go back to 2.21, but there is no
# way to address the containing service before this.
LDS_API_VERSION = "2.44"
CONTEXT_VERSION = "2.38"


def read_lds(module, array, name):
    """Return the named local directory service, or None

    A name the array does not have comes back as 400, not 404, so anything
    other than 200 counts as absent.
    """
    res = get_with_context(
        array,
        "get_directory_services_local_directory_services",
        CONTEXT_VERSION,
        module,
        names=[name],
    )
    if res.status_code != 200:
        return None
    return next(iter(list(res.items)), None)


def create_lds(module, array):
    """Create a local directory service"""
    if not module.check_mode:
        local_directory = LocalDirectoryServicePost(domain=module.params["domain"])
        res = post_with_context(
            array,
            "post_directory_services_local_directory_services",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            local_directory=local_directory,
        )
        check_response(
            res,
            module,
            "Failed to create local directory service {0}".format(
                module.params["name"]
            ),
        )
    module.exit_json(changed=True)


def update_lds(module, array, lds):
    """Bring the domain of an existing local directory service into line

    An omitted domain leaves whatever the array already has, which is what
    makes a play that only names the service idempotent.
    """
    wanted = module.params["domain"]
    changed = bool(wanted) and wanted != getattr(lds, "domain", None)
    if changed and not module.check_mode:
        res = patch_with_context(
            array,
            "patch_directory_services_local_directory_services",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            local_directory=LocalDirectoryService(domain=wanted),
        )
        check_response(
            res,
            module,
            "Failed to change the domain of local directory service "
            "{0}".format(module.params["name"]),
        )
    module.exit_json(changed=changed)


def rename_lds(module, array):
    """Rename a local directory service"""
    if read_lds(module, array, module.params["rename"]):
        module.fail_json(
            msg="Target local directory service {0} already exists".format(
                module.params["rename"]
            )
        )
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_directory_services_local_directory_services",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            local_directory=LocalDirectoryService(name=module.params["rename"]),
        )
        check_response(
            res,
            module,
            "Failed to rename local directory service {0}".format(
                module.params["name"]
            ),
        )
    module.exit_json(changed=True)


def check_renamed_lds(module, array):
    """Report on a rename whose source has already gone

    A completed rename leaves nothing under the old name, so a second run of
    the same task must not create the source again - that would leave the array
    holding both the renamed service and a fresh empty one.
    """
    if not read_lds(module, array, module.params["rename"]):
        module.fail_json(
            msg="Local directory service {0} not found to rename".format(
                module.params["name"]
            )
        )
    module.exit_json(changed=False)


def delete_lds(module, array):
    """Delete a local directory service, and everything inside it"""
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_directory_services_local_directory_services",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
        )
        check_response(
            res,
            module,
            "Failed to delete local directory service {0}".format(
                module.params["name"]
            ),
        )
    module.exit_json(changed=True)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            name=dict(type="str", required=True),
            domain=dict(type="str"),
            rename=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    check_api_version(array, LDS_API_VERSION, module, "Local directory services")

    state = module.params["state"]
    lds = read_lds(module, array, module.params["name"])

    if state == "present" and module.params["rename"]:
        if lds:
            rename_lds(module, array)
        else:
            check_renamed_lds(module, array)
    elif state == "present" and not lds:
        create_lds(module, array)
    elif state == "present":
        update_lds(module, array, lds)
    elif state == "absent" and lds:
        delete_lds(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
