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
module: purefa_localgroup
version_added: '1.45.0'
short_description: Manage Everpure FlashArray local groups
description:
- Create, rename, reconfigure and delete groups inside a local directory
  service on Everpure FlashArrays.
- Every group belongs to one local directory service, which is managed by
  M(everpure.flasharray.purefa_lds). Group names are only unique within a
  service, so I(local_directory_service) is always required.
- Each local directory service is created holding its own C(Administrators),
  C(Guests), C(Backup Operators) and C(Audit Operators) groups. Those are
  built-in - the array allows neither modifying nor deleting them - so this
  module reports no change for a I(state=present) task that asks nothing of
  them, and fails rather than pretending otherwise if a change is requested.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the local group
    type: str
    required: true
  local_directory_service:
    description:
    - Name of the local directory service the group belongs to.
    - Required because group names repeat across local directory services.
    type: str
    required: true
  state:
    description:
    - Define whether the local group should exist or not.
    default: present
    choices: [ absent, present ]
    type: str
  gid:
    description:
    - Group ID to give the group.
    - The array assigns one when the group is created without it.
    - Group IDs only have to be unique within a local directory service.
    type: int
  email:
    description:
    - Email address to associate with the group.
    type: str
  rename:
    description:
    - Value to rename the specified local group to
    - Re-running a rename task reports no change, as long as the group is
      already known by the new name.
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
- Supported from Purity//FA 6.8.0 or higher. Local groups themselves go back
  further, but the parameters that scope a request to one local directory
  service arrived with the service object itself, and without them a request
  cannot be aimed reliably once an array holds more than one service.
- Deleting the local directory service deletes every group in it. See
  M(everpure.flasharray.purefa_lds).
"""

EXAMPLES = r"""
- name: Create local group backup in local directory service foo
  everpure.flasharray.purefa_localgroup:
    name: backup
    local_directory_service: foo
    gid: 70001
    email: backup@example.com
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create local group with an array-assigned GID
  everpure.flasharray.purefa_localgroup:
    name: reporting
    local_directory_service: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Change the email address of local group backup
  everpure.flasharray.purefa_localgroup:
    name: backup
    local_directory_service: foo
    email: storage@example.com
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename local group backup to archive
  everpure.flasharray.purefa_localgroup:
    name: backup
    local_directory_service: foo
    rename: archive
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete local group backup
  everpure.flasharray.purefa_localgroup:
    name: backup
    local_directory_service: foo
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import LocalGroupPatch, LocalGroupPost
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

# Local groups date from 2.21, but the local_directory_service_names parameter
# that scopes a request to one service arrived with the service object in 2.44.
# Without it a request cannot be aimed reliably, because group names repeat in
# every service, so that is the floor for this module.
GROUP_API_VERSION = "2.44"
CONTEXT_VERSION = "2.38"

# The settings this module reconciles, mapped to the field each is read as
SETTINGS = ("gid", "email")


def read_group(module, array, name):
    """Return the named group from the requested service, or None

    A bare name lookup matches the group of that name in *every* local
    directory service on the array, so the service has to be part of the
    query. Anything other than 200 counts as absent - the array answers an
    unknown name with 400, not 404.
    """
    res = get_with_context(
        array,
        "get_directory_services_local_groups",
        CONTEXT_VERSION,
        module,
        names=[name],
        filter="local_directory_service.name='{0}'".format(
            module.params["local_directory_service"]
        ),
    )
    if res.status_code != 200:
        return None
    return next(iter(list(res.items)), None)


def _scope(module):
    """The parameters that aim a write at one local directory service"""
    return {"local_directory_service_names": [module.params["local_directory_service"]]}


def _wanted_changes(module, group):
    """Return the settings that differ from what the array holds

    An option the play leaves out is never a change, which is what keeps a
    task that only names the group idempotent.
    """
    changes = {}
    for setting in SETTINGS:
        wanted = module.params[setting]
        if wanted is None:
            continue
        if wanted != getattr(group, setting, None):
            changes[setting] = wanted
    return changes


def create_group(module, array):
    """Create a local group"""
    if not module.check_mode:
        res = post_with_context(
            array,
            "post_directory_services_local_groups",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            local_group=LocalGroupPost(
                gid=module.params["gid"], email=module.params["email"]
            ),
            **_scope(module)
        )
        check_response(
            res,
            module,
            "Failed to create local group {0}".format(module.params["name"]),
        )
    module.exit_json(changed=True)


def update_group(module, array, group):
    """Bring an existing local group into line with the play"""
    changes = _wanted_changes(module, group)
    if changes and getattr(group, "built_in", False):
        module.fail_json(
            msg="Local group {0} is built-in and cannot be modified".format(
                module.params["name"]
            )
        )
    if changes and not module.check_mode:
        res = patch_with_context(
            array,
            "patch_directory_services_local_groups",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            local_group=LocalGroupPatch(**changes),
            **_scope(module)
        )
        check_response(
            res,
            module,
            "Failed to update local group {0}".format(module.params["name"]),
        )
    module.exit_json(changed=bool(changes))


def rename_group(module, array, group):
    """Rename a local group"""
    if getattr(group, "built_in", False):
        module.fail_json(
            msg="Local group {0} is built-in and cannot be renamed".format(
                module.params["name"]
            )
        )
    if read_group(module, array, module.params["rename"]):
        module.fail_json(
            msg="Target local group {0} already exists".format(module.params["rename"])
        )
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_directory_services_local_groups",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            local_group=LocalGroupPatch(name=module.params["rename"]),
            **_scope(module)
        )
        check_response(
            res,
            module,
            "Failed to rename local group {0}".format(module.params["name"]),
        )
    module.exit_json(changed=True)


def check_renamed_group(module, array):
    """Report on a rename whose source group has already gone

    A completed rename leaves nothing under the old name, so a second run of
    the same task must not create the source again.
    """
    if not read_group(module, array, module.params["rename"]):
        module.fail_json(
            msg="Local group {0} not found to rename".format(module.params["name"])
        )
    module.exit_json(changed=False)


def delete_group(module, array, group):
    """Delete a local group"""
    if getattr(group, "built_in", False):
        module.fail_json(
            msg="Local group {0} is built-in and cannot be deleted".format(
                module.params["name"]
            )
        )
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_directory_services_local_groups",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            **_scope(module)
        )
        check_response(
            res,
            module,
            "Failed to delete local group {0}".format(module.params["name"]),
        )
    module.exit_json(changed=True)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            name=dict(type="str", required=True),
            local_directory_service=dict(type="str", required=True),
            gid=dict(type="int"),
            email=dict(type="str"),
            rename=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    check_api_version(array, GROUP_API_VERSION, module, "Local groups")

    state = module.params["state"]
    group = read_group(module, array, module.params["name"])

    if state == "present" and module.params["rename"]:
        if group:
            rename_group(module, array, group)
        else:
            check_renamed_group(module, array)
    elif state == "present" and not group:
        create_group(module, array)
    elif state == "present":
        update_group(module, array, group)
    elif state == "absent" and group:
        delete_group(module, array, group)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
