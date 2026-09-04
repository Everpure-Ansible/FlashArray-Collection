#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2020, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_directory
version_added: '1.5.0'
short_description: Manage FlashArray File System Directories
description:
- Create/Delete FlashArray File Systems
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the directory
    type: str
    required: true
  state:
    description:
    - Define whether the directory should exist or not.
    default: present
    choices: [ absent, present ]
    type: str
  filesystem:
    description:
    - Name of the filesystem the directory links to.
    type: str
    required: true
  path:
    description:
    - Path of the managed directory in the file system
    - If not provided will default to I(name)
    type: str
  rename:
    description:
    - Value to rename the specified directory to
    - Re-running a rename task reports no change, as long as the directory
      is already known by the new name.
    type: str
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
    version_added: '1.39.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create directory foo in filesysten bar with path zeta
  everpure.flasharray.purefa_directory:
    name: foo
    filesystem: bar
    path: zeta
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename directory foo to fin in filesystem bar
  everpure.flasharray.purefa_directory:
    name: foo
    rename: fin
    filesystem: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete directory foo in filesystem bar
  everpure.flasharray.purefa_directory:
    name: foo
    filesystem: bar
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient import flasharray
except ImportError:
    HAS_PURESTORAGE = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    get_with_context,
    post_with_context,
    patch_with_context,
    delete_with_context,
    check_response,
)

CONTEXT_VERSION = "2.38"


def delete_dir(module, array):
    """Delete a file system directory"""
    changed = True
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_directories",
            CONTEXT_VERSION,
            module,
            names=[module.params["filesystem"] + ":" + module.params["name"]],
        )
        check_response(
            res, module, f"Failed to delete file system {module.params['name']}"
        )
    module.exit_json(changed=changed)


def rename_target(module):
    """Return the fully qualified name a rename would give the directory"""
    return module.params["filesystem"] + ":" + module.params["rename"]


def check_renamed_dir(module, array):
    """Report on a rename whose source directory has already gone

    A completed rename leaves nothing under the old name, so a second run of
    the same task must not create the source again - that would leave the file
    system holding both the renamed directory and a fresh empty one.
    """
    target_name = rename_target(module)
    res = get_with_context(
        array,
        "get_directories",
        CONTEXT_VERSION,
        module,
        names=[target_name],
    )
    if res.status_code != 200:
        module.fail_json(
            msg="Directory {0} not found to rename".format(
                module.params["filesystem"] + ":" + module.params["name"]
            )
        )
    if list(res.items)[0].destroyed:
        module.fail_json(
            msg="Directory {0} exists, but in destroyed state".format(target_name)
        )
    module.exit_json(changed=False)


def rename_dir(module, array):
    """Rename a file system directory"""
    changed = False
    target = get_with_context(
        array,
        "get_directories",
        CONTEXT_VERSION,
        module,
        names=[rename_target(module)],
    )
    if target.status_code != 200:
        changed = True
        if not module.check_mode:
            directory = flasharray.DirectoryPatch(name=rename_target(module))
            res = patch_with_context(
                array,
                "patch_directories",
                CONTEXT_VERSION,
                module,
                names=[module.params["filesystem"] + ":" + module.params["name"]],
                directory=directory,
            )
            check_response(
                res, module, f"Failed to rename file system {module.params['name']}"
            )
    else:
        module.fail_json(
            msg="Target file system {0} already exists".format(module.params["rename"])
        )
    module.exit_json(changed=changed)


def create_dir(module, array):
    """Create a file system directory"""
    changed = False
    if not module.params["path"]:
        module.params["path"] = module.params["name"]
    all_fs_res = get_with_context(
        array,
        "get_directories",
        CONTEXT_VERSION,
        module,
        file_system_names=[module.params["filesystem"]],
    )
    all_fs = list(all_fs_res.items)
    for check in all_fs:
        if module.params["path"] == check.path[1:]:
            module.fail_json(
                msg="Path {0} already existis in file system {1}".format(
                    module.params["path"], module.params["filesystem"]
                )
            )
    changed = True
    if not module.check_mode:
        directory = flasharray.DirectoryPost(
            directory_name=module.params["name"], path=module.params["path"]
        )
        res = post_with_context(
            array,
            "post_directories",
            CONTEXT_VERSION,
            module,
            file_system_names=[module.params["filesystem"]],
            directory=directory,
        )
        check_response(
            res, module, f"Failed to create file system {module.params['name']}"
        )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            filesystem=dict(type="str", required=True),
            name=dict(type="str", required=True),
            rename=dict(type="str"),
            path=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    state = module.params["state"]

    res = get_with_context(
        array,
        "get_file_systems",
        CONTEXT_VERSION,
        module,
        names=[module.params["filesystem"]],
    )
    if res.status_code == 200:
        filesystem = list(res.items)[0]
    else:
        module.fail_json(
            msg="Selected file system {0} does not exist".format(
                module.params["filesystem"]
            )
        )
    res = get_with_context(
        array,
        "get_directories",
        CONTEXT_VERSION,
        module,
        names=[module.params["filesystem"] + ":" + module.params["name"]],
    )
    exists = bool(res.status_code == 200)

    if state == "present" and not exists and module.params["rename"]:
        check_renamed_dir(module, array)
    elif state == "present" and not exists:
        create_dir(module, array)
    elif (
        state == "present"
        and exists
        and module.params["rename"]
        and not filesystem.destroyed
    ):
        rename_dir(module, array)
    elif state == "absent" and exists:
        delete_dir(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
