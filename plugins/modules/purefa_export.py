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
module: purefa_export
version_added: '1.5.0'
short_description: Manage FlashArray File System Exports
description:
- Create/Delete FlashArray File Systems Exports
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the export
    type: str
    required: true
  state:
    description:
    - Define whether the export should exist or not.
    - You must specify an NFS or SMB policy, or both on creation and deletion.
    default: present
    choices: [ absent, present ]
    type: str
  filesystem:
    description:
    - Name of the filesystem the export applies to
    type: str
    required: true
  directory:
    description:
    - Name of the managed directory in the file system the export applies to
    type: str
    required: true
  nfs_policy:
    description:
    - Name of NFS Policy to apply to the export
    type: str
  smb_policy:
    description:
    - Name of SMB Policy to apply to the export
    type: str
  server:
    description:
    - Name of the file server the export belongs to, as managed by
      M(everpure.flasharray.purefa_server).
    - An export name is unique per file server, so this also identifies which
      export is being managed when the same name is used on more than one.
    - Requires Purity//FA REST API 2.44 or higher.
    type: str
    version_added: '1.45.0'
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
- name: Create NFS and SMB exports for directory foo in filesysten bar
  everpure.flasharray.purefa_export:
    name: export1
    filesystem: bar
    directory: foo
    nfs_policy: nfs-example
    smb_policy: smb-example
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete NFS export for directory foo in filesystem bar
  everpure.flasharray.purefa_export:
    name: export1
    filesystem: bar
    directory: foo
    nfs_policy: nfs-example
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create an SMB export on file server filesvr1
  everpure.flasharray.purefa_export:
    name: export1
    filesystem: bar
    directory: foo
    smb_policy: smb-example
    server: filesvr1
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
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_api_version,
    check_response,
    delete_with_context,
    get_with_context,
    post_with_context,
)

MIN_REQUIRED_API_VERSION = "2.3"
CONTEXT_VERSION = "2.42"
# Exports gained a file server of their own in this version
SERVER_VERSION = "2.44"


def _export_found(module, res):
    """Whether an export lookup found the export being asked about

    Without a server the array's status code is the whole answer, which is how
    this module has always read these lookups. With one it is not enough: an
    export name is unique per file server, so the same name can come back from
    a different server than the one the task named. get_directory_exports has
    no server filter, so the items are checked here instead.
    """
    if res.status_code != 200:
        return False
    if not module.params["server"]:
        return True
    return any(
        getattr(getattr(export, "server", None), "name", None)
        == module.params["server"]
        for export in list(res.items)
    )


def _server_names(module):
    """The server_names to scope a patch or delete with, if any"""
    if module.params["server"]:
        return {"server_names": [module.params["server"]]}
    return {}


def delete_export(module, array):
    """Delete a file system export"""
    changed = False
    all_policies = []
    directory = module.params["filesystem"] + ":" + module.params["directory"]
    if not module.params["nfs_policy"] and not module.params["smb_policy"]:
        module.fail_json(msg="At least one policy must be provided")
    if module.params["nfs_policy"]:
        res = get_with_context(
            array,
            "get_directory_exports",
            CONTEXT_VERSION,
            module,
            export_names=[module.params["name"]],
            policy_names=[module.params["nfs_policy"]],
            directory_names=[directory],
        )
        if _export_found(module, res):
            all_policies.append(module.params["nfs_policy"])
    if module.params["smb_policy"]:
        res = get_with_context(
            array,
            "get_directory_exports",
            CONTEXT_VERSION,
            module,
            export_names=[module.params["name"]],
            policy_names=[module.params["smb_policy"]],
            directory_names=[directory],
        )
        if _export_found(module, res):
            all_policies.append(module.params["smb_policy"])
    if all_policies:
        changed = True
        if not module.check_mode:
            res = delete_with_context(
                array,
                "delete_directory_exports",
                CONTEXT_VERSION,
                module,
                export_names=[module.params["name"]],
                policy_names=all_policies,
                **_server_names(module),
            )
            check_response(
                res,
                module,
                f"Failed to delete file system export {module.params['name']}",
            )
    module.exit_json(changed=changed)


def create_export(module, array):
    """Create a file system export"""
    changed = False
    if not module.params["nfs_policy"] and not module.params["smb_policy"]:
        module.fail_json(msg="At least one policy must be provided")
    all_policies = []
    if module.params["nfs_policy"]:
        res = get_with_context(
            array,
            "get_policies_nfs",
            CONTEXT_VERSION,
            module,
            names=[module.params["nfs_policy"]],
        )
        check_response(
            res, module, f"NFS Policy {module.params['nfs_policy']} does not exist"
        )
        res = get_with_context(
            array,
            "get_directory_exports",
            CONTEXT_VERSION,
            module,
            export_names=[module.params["name"]],
            policy_names=[module.params["nfs_policy"]],
        )
        if not _export_found(module, res):
            all_policies.append(module.params["nfs_policy"])
    if module.params["smb_policy"]:
        res = get_with_context(
            array,
            "get_policies_smb",
            CONTEXT_VERSION,
            module,
            names=[module.params["smb_policy"]],
        )
        check_response(
            res, module, f"SMB Policy {module.params['smb_policy']} does not exist"
        )
        res = get_with_context(
            array,
            "get_directory_exports",
            CONTEXT_VERSION,
            module,
            export_names=[module.params["name"]],
            policy_names=[module.params["smb_policy"]],
        )
        if not _export_found(module, res):
            all_policies.append(module.params["smb_policy"])
    if all_policies:
        export_settings = {"export_name": module.params["name"]}
        if module.params["server"]:
            # post_directory_exports takes the server in the body, unlike the
            # patch and delete calls which scope it with server_names
            export_settings["server"] = flasharray.Reference(
                name=module.params["server"]
            )
        export = flasharray.DirectoryExportPost(**export_settings)
        changed = True
        if not module.check_mode:
            res = post_with_context(
                array,
                "post_directory_exports",
                CONTEXT_VERSION,
                module,
                directory_names=[
                    module.params["filesystem"] + ":" + module.params["directory"]
                ],
                exports=export,
                policy_names=all_policies,
            )
            check_response(
                res,
                module,
                f"Failed to create file system exports for "
                f"{module.params['filesystem']}:{module.params['directory']}",
            )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            filesystem=dict(type="str", required=True),
            directory=dict(type="str", required=True),
            name=dict(type="str", required=True),
            nfs_policy=dict(type="str"),
            smb_policy=dict(type="str"),
            server=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    required_if = [["state", "present", ["filesystem", "directory"]]]
    module = AnsibleModule(
        argument_spec, required_if=required_if, supports_check_mode=True
    )

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    api_version = array.get_rest_version()
    if LooseVersion(MIN_REQUIRED_API_VERSION) > LooseVersion(api_version):
        module.fail_json(
            msg="FlashArray REST version not supported. "
            "Minimum version required: {0}".format(MIN_REQUIRED_API_VERSION)
        )
    # Only gate on the file server version when a file server is actually
    # named, so exports on arrays below 2.44 keep working as before
    if module.params["server"]:
        check_api_version(array, SERVER_VERSION, module, "Exports on a file server")
    state = module.params["state"]

    res = get_with_context(
        array,
        "get_directory_exports",
        CONTEXT_VERSION,
        module,
        export_names=[module.params["name"]],
    )
    exists = _export_found(module, res)

    if state == "present":
        create_export(module, array)
    elif state == "absent" and exists:
        delete_export(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
