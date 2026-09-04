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
module: purefa_localuser
version_added: '1.45.0'
short_description: Manage Everpure FlashArray local users
description:
- Create, rename, reconfigure and delete users inside a local directory service
  on Everpure FlashArrays, and manage the groups they belong to.
- Every user belongs to one local directory service, which is managed by
  M(everpure.flasharray.purefa_lds). User names are only unique within a
  service, so I(local_directory_service) is always required. The groups a user
  joins are managed by M(everpure.flasharray.purefa_localgroup).
- Each local directory service is created holding its own C(Administrator) and
  C(Guest) users. Those are built-in - the array allows them to be modified,
  which is how a password is set on a new service's C(Administrator), but not
  deleted.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the local user
    type: str
    required: true
  local_directory_service:
    description:
    - Name of the local directory service the user belongs to.
    - Required because user names repeat across local directory services.
    type: str
    required: true
  state:
    description:
    - Define whether the local user should exist or not.
    default: present
    choices: [ absent, present ]
    type: str
  password:
    description:
    - Password for the local user.
    - Required when creating a user.
    - Whether an existing user's password is reset is controlled by
      I(update_password).
    type: str
  update_password:
    description:
    - C(on_create) only sets the password when the user is created, which keeps
      a task that carries a password idempotent.
    - C(always) resets the password on every run. The array does not allow a
      password to be read back, so there is nothing to compare against and such
      a task always reports a change.
    default: on_create
    choices: [ always, on_create ]
    type: str
  primary_group:
    description:
    - Name of the group to make the user's primary group.
    - Required when creating a user, and the group has to exist already.
    - A user must belong to a group before it can become their primary group.
      This module joins the group first when it has to.
    type: str
  groups:
    description:
    - The groups the user belongs to besides I(primary_group).
    - This is declarative - groups not in the list are left, and the user is
      removed from any others. Omit it to leave the user's groups alone.
    - The primary group is always a membership and is ignored if listed here.
    type: list
    elements: str
  uid:
    description:
    - User ID to give the user.
    - The array assigns one when the user is created without it.
    - User IDs only have to be unique within a local directory service.
    type: int
  email:
    description:
    - Email address to associate with the user.
    type: str
  enabled:
    description:
    - Whether the user is allowed to authenticate.
    type: bool
  rename:
    description:
    - Value to rename the specified local user to
    - Re-running a rename task reports no change, as long as the user is
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
- Supported from Purity//FA 6.8.0 or higher. Local users themselves go back
  further, but the parameters that scope a request to one local directory
  service arrived with the service object itself, and without them a request
  cannot be aimed reliably once an array holds more than one service.
- The array limits a local user name to 20 characters. Alphanumeric US
  ASCII, spaces and symbols are allowed, but not control characters, and not
  the symbols C(/), C(\\), C([), C(]), C(:), C(;), C(|), C(=), C(,), C(+),
  C(*), C(?), C(<), C(>) or C(@). A name may not be digits alone, and may
  neither start nor end with a dot or a space.
- Creating a user requires both I(password) and I(primary_group). The array
  refuses either on its own.
- Deleting the local directory service deletes every user in it. See
  M(everpure.flasharray.purefa_lds).
"""

EXAMPLES = r"""
- name: Create local user fred in local directory service foo
  everpure.flasharray.purefa_localuser:
    name: fred
    local_directory_service: foo
    password: "{{ fred_password }}"
    primary_group: users
    uid: 71000
    email: fred@example.com
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create local user fred in two extra groups
  everpure.flasharray.purefa_localuser:
    name: fred
    local_directory_service: foo
    password: "{{ fred_password }}"
    primary_group: users
    groups:
    - backup
    - reporting
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Remove fred from every group except his primary one
  everpure.flasharray.purefa_localuser:
    name: fred
    local_directory_service: foo
    groups: []
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Set the password on a new service's built-in Administrator
  everpure.flasharray.purefa_localuser:
    name: Administrator
    local_directory_service: foo
    password: "{{ admin_password }}"
    update_password: always
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Disable local user fred
  everpure.flasharray.purefa_localuser:
    name: fred
    local_directory_service: foo
    enabled: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete local user fred
  everpure.flasharray.purefa_localuser:
    name: fred
    local_directory_service: foo
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        LocalUserMembershipPost,
        LocalUserPatch,
        LocalUserPost,
        LocalusermembershippostGroups,
        Reference,
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

# Local users date from 2.21, but the local_directory_service_names parameter
# that scopes a request to one service arrived with the service object in 2.44.
# User names repeat in every service, so that is the floor for this module.
USER_API_VERSION = "2.44"
CONTEXT_VERSION = "2.38"

# The plain settings this module reconciles by comparing what the array holds
SETTINGS = ("uid", "email", "enabled")


def _scope(module):
    """The parameters that aim a write at one local directory service"""
    return {"local_directory_service_names": [module.params["local_directory_service"]]}


def _service_filter(module):
    """A filter clause restricting a read to one local directory service"""
    return "local_directory_service.name='{0}'".format(
        module.params["local_directory_service"]
    )


def read_user(module, array, name):
    """Return the named user from the requested service, or None

    A bare name lookup matches the user of that name in every local directory
    service on the array, so the service has to be part of the query. Anything
    other than 200 counts as absent - the array answers an unknown name with
    400, not 404.
    """
    res = get_with_context(
        array,
        "get_directory_services_local_users",
        CONTEXT_VERSION,
        module,
        names=[name],
        filter=_service_filter(module),
    )
    if res.status_code != 200:
        return None
    return next(iter(list(res.items)), None)


def read_memberships(module, array, name):
    """Return {group name: is primary} for the named user"""
    res = get_with_context(
        array,
        "get_directory_services_local_users_members",
        CONTEXT_VERSION,
        module,
        filter="member.name='{0}' and {1}".format(name, _service_filter(module)),
    )
    if res.status_code != 200:
        return {}
    found = {}
    for member in list(res.items):
        group = getattr(getattr(member, "group", None), "name", None)
        if group:
            found[group] = bool(getattr(member, "is_primary_group", False))
    return found


def _primary_group_name(user):
    """The name of a user's primary group, or None"""
    return getattr(getattr(user, "primary_group", None), "name", None)


def _plain_changes(module, user):
    """Return the plain settings that differ from what the array holds

    An option the play leaves out is never a change, which keeps a task that
    only names the user idempotent.
    """
    changes = {}
    for setting in SETTINGS:
        wanted = module.params[setting]
        if wanted is None:
            continue
        if wanted != getattr(user, setting, None):
            changes[setting] = wanted
    return changes


def _join_group(module, array, group):
    """Add the user to a group"""
    res = post_with_context(
        array,
        "post_directory_services_local_users_members",
        CONTEXT_VERSION,
        module,
        member_names=[module.params["name"]],
        local_membership=LocalUserMembershipPost(
            groups=[LocalusermembershippostGroups(group=Reference(name=group))]
        ),
        **_scope(module)
    )
    check_response(
        res,
        module,
        "Failed to add local user {0} to group {1}".format(
            module.params["name"], group
        ),
    )


def _leave_group(module, array, group):
    """Remove the user from a group"""
    res = delete_with_context(
        array,
        "delete_directory_services_local_users_members",
        CONTEXT_VERSION,
        module,
        member_names=[module.params["name"]],
        group_names=[group],
        **_scope(module)
    )
    check_response(
        res,
        module,
        "Failed to remove local user {0} from group {1}".format(
            module.params["name"], group
        ),
    )


def _patch_user(module, array, target, **fields):
    """Patch the named user with the given fields

    The user to patch is positional and deliberately not called "name", so a
    rename can pass name= as one of the fields without colliding with it.
    """
    res = patch_with_context(
        array,
        "patch_directory_services_local_users",
        CONTEXT_VERSION,
        module,
        names=[target],
        local_user=LocalUserPatch(**fields),
        **_scope(module)
    )
    check_response(res, module, "Failed to update local user {0}".format(target))


def create_user(module, array):
    """Create a local user

    The array refuses a create without both a password and a primary group, so
    say which one is missing rather than passing the refusal through.
    """
    for required in ("password", "primary_group"):
        if not module.params[required]:
            module.fail_json(
                msg="{0} is required to create local user {1}".format(
                    required, module.params["name"]
                )
            )
    if not module.check_mode:
        res = post_with_context(
            array,
            "post_directory_services_local_users",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            local_user=LocalUserPost(
                password=module.params["password"],
                primary_group=Reference(name=module.params["primary_group"]),
                uid=module.params["uid"],
                email=module.params["email"],
                enabled=module.params["enabled"],
            ),
            **_scope(module)
        )
        check_response(
            res,
            module,
            "Failed to create local user {0}".format(module.params["name"]),
        )
        for group in module.params["groups"] or []:
            if group != module.params["primary_group"]:
                _join_group(module, array, group)
    module.exit_json(changed=True)


def _reconcile_primary_group(module, array, user, memberships):
    """Make the requested group the user's primary group

    The array refuses to make a group primary unless the user is already a
    member of it, so the membership goes in first.
    """
    wanted = module.params["primary_group"]
    if not wanted or wanted == _primary_group_name(user):
        return False
    if not module.check_mode:
        if wanted not in memberships:
            _join_group(module, array, wanted)
        _patch_user(
            module, array, module.params["name"], primary_group=Reference(name=wanted)
        )
    return True


def _reconcile_groups(module, array, user, memberships):
    """Bring the user's other group memberships into line

    Omitting the option leaves the memberships alone. The primary group is
    always a membership and the array will not let it be removed, so it is
    never in the removal set.
    """
    wanted = module.params["groups"]
    if wanted is None:
        return False
    primary = module.params["primary_group"] or _primary_group_name(user)
    wanted = {group for group in wanted if group != primary}
    current = {group for group, is_primary in memberships.items() if not is_primary}
    if primary:
        current.discard(primary)
    to_join = wanted - current
    to_leave = current - wanted
    if not module.check_mode:
        for group in sorted(to_join):
            _join_group(module, array, group)
        for group in sorted(to_leave):
            _leave_group(module, array, group)
    return bool(to_join or to_leave)


def update_user(module, array, user):
    """Bring an existing local user into line with the play"""
    changed = False
    memberships = read_memberships(module, array, module.params["name"])

    changes = _plain_changes(module, user)
    if changes:
        changed = True
        if not module.check_mode:
            _patch_user(module, array, module.params["name"], **changes)

    if _reconcile_primary_group(module, array, user, memberships):
        changed = True
        memberships = (
            memberships
            if module.check_mode
            else read_memberships(module, array, module.params["name"])
        )

    if _reconcile_groups(module, array, user, memberships):
        changed = True

    # A password cannot be read back, so there is nothing to compare it
    # against. Only reset it when the play asks for that explicitly.
    if module.params["password"] and module.params["update_password"] == "always":
        changed = True
        if not module.check_mode:
            _patch_user(
                module, array, module.params["name"], password=module.params["password"]
            )

    module.exit_json(changed=changed)


def rename_user(module, array):
    """Rename a local user"""
    if read_user(module, array, module.params["rename"]):
        module.fail_json(
            msg="Target local user {0} already exists".format(module.params["rename"])
        )
    if not module.check_mode:
        _patch_user(module, array, module.params["name"], name=module.params["rename"])
    module.exit_json(changed=True)


def check_renamed_user(module, array):
    """Report on a rename whose source user has already gone

    A completed rename leaves nothing under the old name, so a second run of
    the same task must not create the source again.
    """
    if not read_user(module, array, module.params["rename"]):
        module.fail_json(
            msg="Local user {0} not found to rename".format(module.params["name"])
        )
    module.exit_json(changed=False)


def delete_user(module, array, user):
    """Delete a local user"""
    if getattr(user, "built_in", False):
        module.fail_json(
            msg="Local user {0} is built-in and cannot be deleted".format(
                module.params["name"]
            )
        )
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_directory_services_local_users",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            **_scope(module)
        )
        check_response(
            res,
            module,
            "Failed to delete local user {0}".format(module.params["name"]),
        )
    module.exit_json(changed=True)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            name=dict(type="str", required=True),
            local_directory_service=dict(type="str", required=True),
            password=dict(type="str", no_log=True),
            update_password=dict(
                type="str",
                default="on_create",
                choices=["always", "on_create"],
                no_log=False,
            ),
            primary_group=dict(type="str"),
            groups=dict(type="list", elements="str"),
            uid=dict(type="int"),
            email=dict(type="str"),
            enabled=dict(type="bool"),
            rename=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    check_api_version(array, USER_API_VERSION, module, "Local users")

    state = module.params["state"]
    user = read_user(module, array, module.params["name"])

    if state == "present" and module.params["rename"]:
        if user:
            rename_user(module, array)
        else:
            check_renamed_user(module, array)
    elif state == "present" and not user:
        create_user(module, array)
    elif state == "present":
        update_user(module, array, user)
    elif state == "absent" and user:
        delete_user(module, array, user)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
