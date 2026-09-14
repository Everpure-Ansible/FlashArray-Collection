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
module: purefa_user
version_added: '1.0.0'
short_description: Create, modify or delete FlashArray local user account
description:
- Create, modify or delete local users on a Everpure FlashArray.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  state:
    description:
    - Create, delete or update local user account
    default: present
    type: str
    choices: [ absent, present ]
  name:
    description:
    - The name of the local user account
    type: str
    required: true
  role:
    description:
    - Sets the local user's access level to the array
    type: str
    default: readonly
    choices: [ readonly, ops_admin, storage_admin, array_admin ]
  password:
    description:
    - Password for the local user.
    type: str
  old_password:
    description:
    - If changing an existing password, you must provide the old password for security
    type: str
  api:
    description:
    - Define whether to create an API token for this user
    - Token can be exposed using the I(debug) module
    type: bool
    default: false
  timeout:
    description:
      - The duration of API token validity.
      - Valid values are weeks (w), days(d), hours(h), minutes(m) and seconds(s).
    type: str
    default: "0"
    version_added: "1.34.0"
  public_key:
    description:
      - Public key for SSH access.
      - To remove existing key use an empty string
    type: str
    version_added: "1.34.0"
  ad_user:
    description:
      - Whether the user is in the AD system
      - Not required for local users
    type: bool
    default: false
    version_added: "1.37.0"
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create new user ansible with API token
  everpure.flasharray.purefa_user:
    name: ansible
    password: apassword
    role: storage_admin
    api: true
    timeout: 2d
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: result

  debug:
    msg: "API Token: {{ result['user_info']['user_api'] }}"

- name: Overwrite/add SSH public key for existing user
  everpure.flasharray.purefa_user:
    name: ansible
    role: array_admin
    public_key: "{{lookup('file', 'id_rsa.pub') }}"
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Remove existing SSH public key from user
  everpure.flasharray.purefa_user:
    name: ansible
    role: array_admin
    public_key: ""
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Change role type for existing user
  everpure.flasharray.purefa_user:
    name: ansible
    role: array_admin
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Change password type for existing user (NOT IDEMPOTENT)
  everpure.flasharray.purefa_user:
    name: ansible
    password: anewpassword
    old_password: apassword
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create an API token (TTL of 2 days) and assign a public key to an AD user
  everpure.flasharray.purefa_user:
    name: ansible-ad
    ad_user: true
    public_key: "{{lookup('file', 'id_rsa.pub') }}"
    api: true
    timeout: 2d
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Change API token and token timeout for existing user
  everpure.flasharray.purefa_user:
    name: ansible
    api: true
    role: array_admin
    timeout: 1d
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: result

  debug:
    msg: "API Token: {{ result['user_info']['user_api'] }}"
"""

RETURN = r"""
"""


HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import AdminPost, AdminPatch, AdminRole
except ImportError:
    HAS_PURESTORAGE = False

import re
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.common import (
    convert_time_to_millisecs,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_response,
)


def get_user(module, array):
    """Return Local User Account or None"""
    res = array.get_admins(names=[module.params["name"]])
    if res.status_code != 200:
        return None
    return list(res.items)[0]


def create_local_user(module, array, user):
    """Create or Update Local User Account"""
    changed = key_changed = api_changed = role_changed = passwd_changed = False
    role = module.params["role"]
    api_token = "No API token created"
    if not user:
        changed = True
        if not module.check_mode:
            res = array.post_admins(
                names=[module.params["name"]],
                admin=AdminPost(
                    role=AdminRole(name=role),
                    password=module.params["password"],
                ),
            )
            check_response(
                res, module, f"Failed to create user {module.params['name']}"
            )
            if module.params["api"]:
                ttl = convert_time_to_millisecs(module.params["timeout"])
                res = array.post_admins_api_tokens(
                    names=[module.params["name"]], timeout=ttl
                )
                check_response(res, module, "Failed to create API token")
                api_token = list(res.items)[0].api_token.token
            if module.params["public_key"]:
                res = array.patch_admins(
                    names=[module.params["name"]],
                    admin=AdminPatch(public_key=module.params["public_key"]),
                )
                check_response(res, module, "Failed to add SSH key")
    else:
        if module.params["password"] and not module.params["old_password"]:
            module.exit_json(changed=changed)
        if (
            module.params["password"]
            and module.params["old_password"]
            and module.params["password"] != module.params["old_password"]
        ):
            passwd_changed = True
            if not module.check_mode:
                res = array.patch_admins(
                    names=[module.params["name"]],
                    admin=AdminPatch(
                        password=module.params["password"],
                        old_password=module.params["old_password"],
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Local User {module.params['name']} password reset failed. Check old password",
                )
        if module.params["api"]:
            api_changed = True
            if not module.check_mode:
                ttl = convert_time_to_millisecs(module.params["timeout"])
                res = array.delete_admins_api_tokens(names=[module.params["name"]])
                check_response(res, module, "Failed to delete original API token")
                res = array.post_admins_api_tokens(
                    names=[module.params["name"]], timeout=ttl
                )
                check_response(res, module, "Failed to recreate API token")
                api_token = list(res.items)[0].api_token.token
        if module.params["role"] and module.params["role"] != getattr(
            user.role, "name", None
        ):
            if module.params["name"] != "pureuser":
                role_changed = True
                if not module.check_mode:
                    res = array.patch_admins(
                        names=[module.params["name"]],
                        admin=AdminPatch(role=AdminRole(name=module.params["role"])),
                    )
                    check_response(
                        res,
                        module,
                        f"Local User {module.params['name']} role change failed",
                    )
            else:
                module.warn("Role for 'pureuser' cannot be modified.")
        if module.params["public_key"] is not None and module.params[
            "public_key"
        ] != getattr(user, "public_key", ""):
            key_changed = True
            if not module.check_mode:
                res = array.patch_admins(
                    names=[module.params["name"]],
                    admin=AdminPatch(public_key=module.params["public_key"]),
                )
                check_response(res, module, "Failed to change SSH key")
        changed = bool(passwd_changed or role_changed or api_changed or key_changed)
    module.exit_json(changed=changed, user_info=api_token)


def update_ad_user(module, array, user):
    """Update AD user API token and/or SSH key"""
    api_token = "No API token created"
    api_changed = ssh_changed = False
    if module.params["api"]:
        api_changed = True
        if not module.check_mode:
            ttl = convert_time_to_millisecs(module.params["timeout"])
            if user:
                res = array.delete_admins_api_tokens(names=[module.params["name"]])
                check_response(res, module, "Failed to delete original API token")
            res = array.post_admins_api_tokens(
                names=[module.params["name"]], timeout=ttl
            )
            check_response(res, module, "Failed to create API token")
            api_token = list(res.items)[0].api_token.token
    # An empty string clears the key, so this is checked against None rather
    # than for truthiness. An AD user with no array-side state is not returned
    # by get_admins, so there is no current key to compare against.
    if module.params["public_key"] is not None:
        current_key = getattr(user, "public_key", None) if user else None
        if module.params["public_key"] != (current_key or ""):
            ssh_changed = True
            if not module.check_mode:
                res = array.patch_admins(
                    names=[module.params["name"]],
                    admin=AdminPatch(public_key=module.params["public_key"]),
                )
                check_response(res, module, "Failed to add SSH key")
    changed = bool(api_changed or ssh_changed)
    module.exit_json(changed=changed, user_info=api_token)


def delete_local_user(module, array):
    """Delete Local User Account"""
    changed = True
    if not module.check_mode:
        res = array.delete_admins(names=[module.params["name"]])
        check_response(
            res, module, f"User Account {module.params['name']} deletion failed"
        )
    module.exit_json(changed=changed)


def delete_ad_user(module, array, user):
    """Delete AD User Account references"""
    changed = False
    if not module.check_mode:
        if user:
            changed = True
            res = array.delete_admins_api_tokens(names=[module.params["name"]])
            check_response(
                res,
                module,
                f"AD Account {module.params['name']} API token deletion failed",
            )
            if hasattr(user, "public_key"):
                res = array.patch_admins(
                    names=[module.params["name"]],
                    admin=AdminPatch(public_key=""),
                )
                check_response(
                    res,
                    module,
                    f"AD Account {module.params['name']} public key deletion failed",
                )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(required=True, type="str"),
            role=dict(
                type="str",
                choices=["readonly", "ops_admin", "storage_admin", "array_admin"],
                default="readonly",
            ),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            password=dict(type="str", no_log=True),
            old_password=dict(type="str", no_log=True),
            api=dict(type="bool", default=False),
            timeout=dict(type="str", default="0"),
            public_key=dict(type="str", no_log=True),
            ad_user=dict(type="bool", default=False),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    state = module.params["state"]
    array = get_array(module)
    # These are Purity's rules for the local account names the array itself
    # creates. Directory service users are named by the directory, in formats
    # such as first.last that the array accepts perfectly well, so the pattern
    # must not be applied to them - see #1060.
    if not module.params["ad_user"]:
        pattern = re.compile("^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$")
        if not pattern.match(module.params["name"]):
            module.fail_json(
                msg="name must contain a minimum of 1 and a maximum of 32 characters "
                "(alphanumeric or `-`). All letters must be lowercase."
            )
    user = get_user(module, array)
    local_user = getattr(user, "is_local", False)
    if state == "present" and not local_user and module.params["ad_user"]:
        update_ad_user(module, array, user)
    if state == "absent" and local_user:
        delete_local_user(module, array)
    if state == "absent" and not local_user:
        delete_ad_user(module, array, user)
    elif state == "present" and not module.params["ad_user"]:
        create_local_user(module, array, user)
    else:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
