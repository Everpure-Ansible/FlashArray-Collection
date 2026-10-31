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
      - The name of the user account.
    type: str
    required: true
  role:
    description:
    - Sets the local user's access level to the array
    - Mutually exclusive with I(access_policy).
    - A new user gets C(readonly) when neither I(role) nor I(access_policy) is
      set. An existing user's role or policy is only changed when I(role) or
      I(access_policy) is given.
    type: str
    choices: [ readonly, ops_admin, storage_admin, array_admin ]
  access_policy:
    description:
    - Name of a custom management access policy that gives the local user
      its permissions, instead of a built-in I(role).
    - The user gets no built-in role, so its access is limited to what the
      policy grants. For example, a policy granting C(storage) scoped to a
      realm makes a realm-scoped user.
    - The user becomes a member of this policy only, which replaces any
      role or other policy it had. The new membership is added before the
      old one is removed.
    - Setting I(role) on a user that has an access policy moves it back to
      that built-in role.
    - Mutually exclusive with I(role).
    - Local users only.
    - Requires Purity//FA 6.6.9, or higher (REST 2.36).
    type: str
    version_added: '1.46.0'
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
      - The array never returns a stored key (it reads back masked), so a
        task that sets a key is NOT IDEMPOTENT and reports changed on every
        run. Removing a key with an empty string is idempotent.
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

- name: Create a realm-scoped user from a custom management access policy, with an API token
  everpure.flasharray.purefa_user:
    name: ocp-csi
    password: apassword
    access_policy: ocp-realm-storage
    api: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: result

- name: Overwrite/add SSH public key for existing user (NOT IDEMPOTENT)
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

- name: Create an API token (TTL of 2 days) and assign a public key to an AD user (NOT IDEMPOTENT)
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
    from pypureclient.flasharray import (
        AdminPost,
        AdminPatch,
        AdminRole,
        PolicyMemberPost,
        PolicymemberpostMembers,
        ReferenceWithType,
    )
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
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)

POLICY_API_VERSION = "2.36"

LOCAL_NAME_PATTERN = re.compile("^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$")
# Deny only illegal characters: the separators the array splits or routes on,
# whitespace, and the C0/C1 control ranges. \Z rather than $, because $ would
# match before a trailing newline, which a name read with lookup("file", ...)
# carries.
AD_NAME_PATTERN = re.compile(r"\A[^\s\x00-\x1f\x7f-\x9f,/?&#]{1,128}\Z")


def _has_api_token(user):
    """True when the admin entry carries an API token

    The array reports a token as created_at/expires_at stamps (the value
    itself is only exposed on request); an admin without one has no
    api_token at all, which the SDK model raises AttributeError for.
    """
    token = getattr(user, "api_token", None)
    return bool(getattr(token, "created_at", None) or getattr(token, "token", None))


def _public_key_change(module, user):
    """Whether the requested public_key needs a patch

    The array masks a stored key, so a key that is set can never be compared
    with the request and is always re-applied (NOT IDEMPOTENT). Clearing a
    key is a change only when the array holds one.
    """
    requested = module.params["public_key"]
    if requested is None:
        return False
    if requested:
        return True
    return bool(getattr(user, "public_key", ""))


def get_user(module, array):
    """Return Local User Account or None"""
    res = array.get_admins(names=[module.params["name"]])
    if res.status_code != 200:
        return None
    return list(res.items)[0]


def set_access_policy(module, array, user, policy):
    """Make the user a member of exactly one management access policy.

    The array changes policy membership only through the policy members
    endpoints (PATCH admins refuses management_access_policies). The new
    membership is added before the old ones are removed, so the user is
    never left without access.
    """
    name = module.params["name"]
    current = [
        p.name for p in (getattr(user, "management_access_policies", None) or [])
    ]
    if policy not in current:
        res = array.post_policies_management_access_members(
            policy_names=[policy],
            members=PolicyMemberPost(
                members=[
                    PolicymemberpostMembers(
                        member=ReferenceWithType(name=name, resource_type="admins")
                    )
                ]
            ),
        )
        check_response(res, module, f"Adding {name} to access policy {policy}")
    for old in current:
        if old != policy:
            res = array.delete_policies_management_access_members(
                policy_names=[old], member_names=[name], member_types=["admins"]
            )
            check_response(res, module, f"Removing {name} from access policy {old}")


def create_local_user(module, array, user):
    """Create or Update Local User Account"""
    changed = key_changed = api_changed = role_changed = passwd_changed = False
    policy_changed = False
    # readonly is the default for a NEW user only. module.params["role"]
    # stays None when the task omits it, so the update path below can tell
    # "not given" from "readonly" and leave a policy-scoped user alone.
    role = module.params["role"] or "readonly"
    access_policy = module.params.get("access_policy")
    api_token = "No API token created"
    if not user:
        changed = True
        if not module.check_mode:
            if access_policy:
                admin = AdminPost(
                    management_access_policies=[ReferenceWithType(name=access_policy)],
                    password=module.params["password"],
                )
            else:
                admin = AdminPost(
                    role=AdminRole(name=role),
                    password=module.params["password"],
                )
            res = array.post_admins(names=[module.params["name"]], admin=admin)
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
            # The password cannot be changed, but the other attributes can
            module.warn(
                "password ignored for existing user: old_password is required "
                "to change it"
            )
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
                    f"Local User {module.params['name']} password reset (check the old password)",
                )
        if module.params["api"]:
            api_changed = True
            if not module.check_mode:
                ttl = convert_time_to_millisecs(module.params["timeout"])
                # Deleting a token that does not exist is an array error
                if _has_api_token(user):
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
                    if getattr(getattr(user, "role", None), "name", None) is None:
                        # A user that gets its access from a custom policy
                        # is not a role user: the array refuses a role
                        # change for it. Each built-in role is a built-in
                        # policy of the same name, so switch policies.
                        set_access_policy(module, array, user, module.params["role"])
                    else:
                        res = array.patch_admins(
                            names=[module.params["name"]],
                            admin=AdminPatch(
                                role=AdminRole(name=module.params["role"])
                            ),
                        )
                        check_response(
                            res,
                            module,
                            f"Local User {module.params['name']} role change",
                        )
            else:
                module.warn("Role for 'pureuser' cannot be modified.")
        if access_policy:
            current_policies = sorted(
                policy.name
                for policy in (getattr(user, "management_access_policies", None) or [])
            )
            if current_policies != [access_policy]:
                if module.params["name"] != "pureuser":
                    policy_changed = True
                    if not module.check_mode:
                        set_access_policy(module, array, user, access_policy)
                else:
                    module.warn("Access policy for 'pureuser' cannot be modified.")
        if _public_key_change(module, user):
            key_changed = True
            if not module.check_mode:
                res = array.patch_admins(
                    names=[module.params["name"]],
                    admin=AdminPatch(public_key=module.params["public_key"]),
                )
                check_response(res, module, "Failed to change SSH key")
        changed = bool(
            passwd_changed
            or role_changed
            or policy_changed
            or api_changed
            or key_changed
        )
    module.exit_json(changed=changed, user_info=api_token)


def update_ad_user(module, array, user):
    """Update AD user API token and/or SSH key"""
    api_token = "No API token created"
    api_changed = ssh_changed = False
    if module.params["api"]:
        api_changed = True
        ttl = convert_time_to_millisecs(module.params["timeout"])
        if not module.check_mode:
            if _has_api_token(user):
                res = array.delete_admins_api_tokens(names=[module.params["name"]])
                check_response(res, module, "Failed to delete original API token")
            res = array.post_admins_api_tokens(
                names=[module.params["name"]], timeout=ttl
            )
            check_response(
                res,
                module,
                (
                    "Failed to recreate API token"
                    if user
                    else "Failed to create API token"
                ),
            )
            api_token = list(res.items)[0].api_token.token
    if _public_key_change(module, user):
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
        check_response(res, module, f"User Account {module.params['name']} deletion")
    module.exit_json(changed=changed)


def delete_ad_user(module, array, user):
    """Delete AD User Account references"""
    changed = bool(user)
    if changed and not module.check_mode:
        if _has_api_token(user):
            res = array.delete_admins_api_tokens(names=[module.params["name"]])
            check_response(
                res,
                module,
                f"AD Account {module.params['name']} API token deletion",
            )
        if hasattr(user, "public_key"):
            res = array.patch_admins(
                names=[module.params["name"]],
                admin=AdminPatch(public_key=""),
            )
            check_response(
                res,
                module,
                f"AD Account {module.params['name']} public key deletion",
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
            ),
            access_policy=dict(type="str"),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            password=dict(type="str", no_log=True),
            old_password=dict(type="str", no_log=True),
            api=dict(type="bool", default=False),
            timeout=dict(type="str", default="0"),
            public_key=dict(type="str", no_log=True),
            ad_user=dict(type="bool", default=False),
        )
    )

    module = AnsibleModule(
        argument_spec,
        mutually_exclusive=[["role", "access_policy"]],
        supports_check_mode=True,
    )

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    if module.params.get("access_policy") and module.params["ad_user"]:
        module.fail_json(msg="access_policy applies to local users only")

    state = module.params["state"]
    array = get_array(module)
    if module.params.get("access_policy") and LooseVersion(
        array.get_rest_version()
    ) < LooseVersion(POLICY_API_VERSION):
        module.fail_json(
            msg="access_policy requires Purity//FA 6.6.9, or higher (REST 2.36)"
        )
    if module.params["ad_user"]:
        if not AD_NAME_PATTERN.match(module.params["name"]):
            module.fail_json(
                msg="name must contain a minimum of 1 and a maximum of 128 "
                "characters, and must not contain whitespace, control "
                "characters, or any of `,`, `/`, `?`, `&`, `#`."
            )
    elif not LOCAL_NAME_PATTERN.match(module.params["name"]):
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
