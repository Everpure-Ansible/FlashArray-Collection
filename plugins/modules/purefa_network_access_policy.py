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
module: purefa_network_access_policy
version_added: '1.41.0'
short_description: Manage FlashArray Network Access Policies
description:
- Manage FlashArray network-access policies introduced with Purity//FA 6.10.5
  and FlashArray REST API 2.52.
- Controls inbound access to management interfaces using ordered allow/deny rules.
- Only one policy can be active array-wide at a time. The default policy allows
  all access. If no rule matches, access is blocked.
author:
- Pure Storage Ansible Team (@avk) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the network-access policy.
    type: str
    required: true
  state:
    description:
    - Define whether the policy (or rule) should exist or not.
    default: present
    choices: [ absent, present ]
    type: str
  enabled:
    description:
    - Define if the policy is enabled or not.
    - On create, defaults to C(false) when not specified so a new policy
      is not enabled implicitly.
    - On update, an omitted value leaves the current enabled state
      unchanged so unrelated rule tasks do not re-enable a policy that
      was intentionally disabled.
    type: bool
  rename:
    description:
    - New name of the policy.
    - Re-running a rename task reports no change if the policy is already known
      by the new name.
    type: str
  active:
    description:
    - When C(true), makes this policy the active array-wide network-access policy
      via C(PATCH /arrays).
    - The policy must be enabled before it can be activated.
    - Setting C(active) to C(false) is not supported; activate another policy to
      replace the current one.
    type: bool
  effect:
    description:
    - Effect of the rule being added or updated.
    - Required together with I(client) and I(interfaces) when adding a rule.
    choices: [ allow, deny ]
    type: str
  client:
    description:
    - Client address the rule applies to.
    - Accepts an IPv4 address, IPv6 address, CIDR subnet, or C(*) for all clients.
    - Required together with I(effect) and I(interfaces) when adding a rule.
    type: str
  interfaces:
    description:
    - Management interfaces the rule applies to.
    - Required together with I(effect) and I(client) when adding a rule.
    type: list
    elements: str
    choices:
    - management-ssh
    - management-rest-api
    - management-rest-api-v1
    - management-rest-api-v2
    - management-web-ui
    - snmp
  index:
    description:
    - Desired evaluation position of the rule within the policy.
    - The array enforces ordering constraints (deny before allow; individual IP
      before CIDR; CIDR before C(*)).
    type: int
  rule_name:
    description:
    - Name of an existing rule to update or delete.
    - When supplied with I(state=absent), deletes the named rule instead of the
      whole policy.
    - When supplied with any of I(effect), I(client), I(interfaces), or I(index),
      updates the named rule with a partial patch. Attributes not supplied are
      left unchanged.
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
"""

EXAMPLES = r"""
- name: Create an empty network-access policy
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create a network-access policy with an initial deny rule for a subnet
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    effect: deny
    client: 10.20.30.0/24
    interfaces:
      - management-ssh
      - management-web-ui
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Add an allow-all rule to an existing network-access policy
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    effect: allow
    client: "*"
    interfaces:
      - management-ssh
      - management-rest-api
      - management-web-ui
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Update a specific rule in a network-access policy
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    rule_name: restricted.1
    effect: deny
    client: 192.168.0.0/16
    interfaces:
      - management-ssh
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete a rule from a network-access policy
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    rule_name: restricted.1
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Disable a network-access policy
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    enabled: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Activate a network-access policy array-wide
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    active: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename a network-access policy
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    rename: restricted-mgmt
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete a network-access policy
  everpure.flasharray.purefa_network_access_policy:
    name: restricted
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        PolicyPost,
        PolicyPatch,
        Arrays,
        Reference,
        PolicyRuleNetworkAccessPost,
        PolicyrulenetworkaccesspostRules,
        PolicyRuleNetworkAccessPatch,
        PolicyrulenetworkaccesspatchRules,
    )
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
    get_with_context,
    post_with_context,
    patch_with_context,
    delete_with_context,
    check_response,
)

MIN_REQUIRED_API_VERSION = "2.52"
CONTEXT_VERSION = "2.38"


def check_renamed_policy(module, array):
    """Report on a rename whose source has already gone.

    A completed rename leaves nothing under the old name. A second run of
    the same task must not create the source again — that would leave both
    the renamed policy and a fresh empty one on the array.
    """
    res = get_with_context(
        array,
        "get_policies_network_access",
        CONTEXT_VERSION,
        module,
        names=[module.params["rename"]],
    )
    if res.status_code != 200:
        module.fail_json(msg=f"Policy {module.params['name']} not found to rename")
    items = list(res.items)
    if not items:
        module.fail_json(
            msg=f"Lookup for renamed policy {module.params['rename']} returned no items"
        )
    if items[0].destroyed:
        module.fail_json(
            msg=f"Policy {module.params['rename']} exists, but in destroyed state"
        )
    module.exit_json(changed=False)


def rename_policy(module, array):
    """Rename a network-access policy."""
    res = get_with_context(
        array,
        "get_policies_network_access",
        CONTEXT_VERSION,
        module,
        names=[module.params["rename"]],
    )
    if res.status_code == 200:
        module.fail_json(
            msg=f"Rename failed - target policy {module.params['rename']} already exists"
        )
    changed = True
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_policies_network_access",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            policy=PolicyPatch(name=module.params["rename"]),
        )
        check_response(
            res,
            module,
            f"Renaming network-access policy {module.params['name']} to {module.params['rename']}",
        )
    module.exit_json(changed=changed)


def create_policy(module, array):
    """Create a network-access policy and optionally add an initial rule."""
    if module.params["active"] and not (
        module.params["effect"]
        and module.params["client"]
        and module.params["interfaces"]
    ):
        module.fail_json(
            msg="Cannot activate a network-access policy with no rules — "
            "activating an empty policy blocks all management access. "
            "Provide effect, client, and interfaces to create an initial rule."
        )

    changed = True
    if not module.check_mode:
        changed = False
        enabled = (
            module.params["enabled"] if module.params["enabled"] is not None else False
        )
        res = post_with_context(
            array,
            "post_policies_network_access",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            policy=PolicyPost(enabled=enabled),
        )
        if res.status_code == 200:
            changed = True
            if (
                module.params["effect"]
                and module.params["client"]
                and module.params["interfaces"]
            ):
                rule_kwargs = dict(
                    effect=module.params["effect"],
                    client=module.params["client"],
                    interfaces=module.params["interfaces"],
                )
                if module.params["index"] is not None:
                    rule_kwargs["index"] = module.params["index"]
                rule = PolicyRuleNetworkAccessPost(
                    rules=[PolicyrulenetworkaccesspostRules(**rule_kwargs)]
                )
                res = post_with_context(
                    array,
                    "post_policies_network_access_rules",
                    CONTEXT_VERSION,
                    module,
                    policy_names=[module.params["name"]],
                    rules=rule,
                )
                check_response(
                    res,
                    module,
                    f"Creating rule for network-access policy {module.params['name']}",
                )
            if module.params["active"]:
                res = patch_with_context(
                    array,
                    "patch_arrays",
                    CONTEXT_VERSION,
                    module,
                    array=Arrays(
                        network_access_policy=Reference(name=module.params["name"])
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Setting network-access policy {module.params['name']} as active",
                )
        else:
            module.fail_json(
                msg=f"Failed to create network-access policy {module.params['name']}. "
                f"Error: {res.errors[0].message}"
            )
    module.exit_json(changed=changed)


def update_policy(module, array):
    """Update an existing network-access policy."""
    changed = changed_enable = changed_rule = False

    res = get_with_context(
        array,
        "get_policies_network_access",
        CONTEXT_VERSION,
        module,
        names=[module.params["name"]],
    )
    if res.status_code != 200:
        module.fail_json(
            msg=f"Failed to read network-access policy {module.params['name']}"
        )
    items = list(res.items)
    if not items:
        module.fail_json(
            msg=f"Network-access policy {module.params['name']} lookup returned no items"
        )
    current_enabled = items[0].enabled

    if (
        module.params["enabled"] is not None
        and current_enabled != module.params["enabled"]
    ):
        changed_enable = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_policies_network_access",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                policy=PolicyPatch(enabled=module.params["enabled"]),
            )
            if res.status_code != 200:
                module.fail_json(
                    msg=f"Failed to enable/disable network-access policy {module.params['name']}"
                )

    rule_attrs_given = any(
        [module.params["effect"], module.params["client"], module.params["interfaces"]]
    )

    if module.params["rule_name"] and (
        rule_attrs_given or module.params["index"] is not None
    ):
        res = get_with_context(
            array,
            "get_policies_network_access_rules",
            CONTEXT_VERSION,
            module,
            names=[module.params["rule_name"]],
        )
        if res.status_code != 200:
            module.fail_json(
                msg=f"Rule {module.params['rule_name']} not found in "
                f"network-access policy {module.params['name']}"
            )
        current_rule = list(res.items)[0]
        current_interfaces = sorted(getattr(current_rule, "interfaces", []) or [])
        new_interfaces = (
            sorted(module.params["interfaces"])
            if module.params["interfaces"] is not None
            else current_interfaces
        )
        current_config = {
            "effect": getattr(current_rule, "effect", None),
            "client": getattr(current_rule, "client", None),
            "interfaces": current_interfaces,
            "index": getattr(current_rule, "index", None),
        }
        new_config = {
            "effect": module.params["effect"] or current_config["effect"],
            "client": module.params["client"] or current_config["client"],
            "interfaces": new_interfaces,
            "index": (
                module.params["index"]
                if module.params["index"] is not None
                else current_config["index"]
            ),
        }
        if new_config != current_config:
            changed_rule = True
            if not module.check_mode:
                patch_kwargs = {}
                if module.params["effect"]:
                    patch_kwargs["effect"] = module.params["effect"]
                if module.params["client"]:
                    patch_kwargs["client"] = module.params["client"]
                if module.params["interfaces"] is not None:
                    patch_kwargs["interfaces"] = module.params["interfaces"]
                if module.params["index"] is not None:
                    patch_kwargs["index"] = module.params["index"]
                res = patch_with_context(
                    array,
                    "patch_policies_network_access_rules",
                    CONTEXT_VERSION,
                    module,
                    policy_names=[module.params["name"]],
                    names=[module.params["rule_name"]],
                    rules=PolicyRuleNetworkAccessPatch(
                        rules=[PolicyrulenetworkaccesspatchRules(**patch_kwargs)]
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Updating rule {module.params['rule_name']} for "
                    f"network-access policy {module.params['name']}",
                )
    elif (
        not module.params["rule_name"]
        and module.params["effect"]
        and module.params["client"]
        and module.params["interfaces"]
    ):
        res = get_with_context(
            array,
            "get_policies_network_access_rules",
            CONTEXT_VERSION,
            module,
            policy_names=[module.params["name"]],
        )
        existing_rules = list(res.items) if res.status_code == 200 else []
        match = next(
            (
                r
                for r in existing_rules
                if getattr(r, "effect", None) == module.params["effect"]
                and getattr(r, "client", None) == module.params["client"]
                and sorted(getattr(r, "interfaces", []) or [])
                == sorted(module.params["interfaces"])
            ),
            None,
        )
        if match is None:
            changed_rule = True
            if not module.check_mode:
                rule_kwargs = dict(
                    effect=module.params["effect"],
                    client=module.params["client"],
                    interfaces=module.params["interfaces"],
                )
                if module.params["index"] is not None:
                    rule_kwargs["index"] = module.params["index"]
                rule = PolicyRuleNetworkAccessPost(
                    rules=[PolicyrulenetworkaccesspostRules(**rule_kwargs)]
                )
                res = post_with_context(
                    array,
                    "post_policies_network_access_rules",
                    CONTEXT_VERSION,
                    module,
                    policy_names=[module.params["name"]],
                    rules=rule,
                )
                check_response(
                    res,
                    module,
                    f"Adding rule to network-access policy {module.params['name']}",
                )
        elif (
            module.params["index"] is not None
            and getattr(match, "index", None) != module.params["index"]
        ):
            changed_rule = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_policies_network_access_rules",
                    CONTEXT_VERSION,
                    module,
                    policy_names=[module.params["name"]],
                    names=[getattr(match, "name")],
                    rules=PolicyRuleNetworkAccessPatch(
                        rules=[
                            PolicyrulenetworkaccesspatchRules(
                                index=module.params["index"]
                            )
                        ]
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Reordering rule {getattr(match, 'name')} in "
                    f"network-access policy {module.params['name']}",
                )

    changed_active = False
    if module.params["active"]:
        rules_res = get_with_context(
            array,
            "get_policies_network_access_rules",
            CONTEXT_VERSION,
            module,
            policy_names=[module.params["name"]],
        )
        has_current_rules = rules_res.status_code == 200 and bool(list(rules_res.items))
        will_have_rules = has_current_rules or (module.check_mode and changed_rule)
        if not will_have_rules:
            module.fail_json(
                msg=f"Cannot activate network-access policy {module.params['name']} "
                "with no rules — activating an empty policy blocks all management "
                "access. Add at least one rule first."
            )

        arr_res = get_with_context(
            array,
            "get_arrays",
            CONTEXT_VERSION,
            module,
        )
        is_active = False
        if arr_res.status_code == 200:
            arr_items = list(arr_res.items)
            if arr_items:
                active_policy = getattr(arr_items[0], "network_access_policy", None)
                if (
                    active_policy
                    and getattr(active_policy, "name", None) == module.params["name"]
                ):
                    is_active = True
        if not is_active:
            changed_active = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_arrays",
                    CONTEXT_VERSION,
                    module,
                    array=Arrays(
                        network_access_policy=Reference(name=module.params["name"])
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Setting network-access policy {module.params['name']} as active",
                )

    if changed_enable or changed_rule or changed_active:
        changed = True
    module.exit_json(changed=changed)


def delete_policy(module, array):
    """Delete a rule or the whole network-access policy."""
    if module.params["rule_name"]:
        check_res = get_with_context(
            array,
            "get_policies_network_access_rules",
            CONTEXT_VERSION,
            module,
            names=[module.params["rule_name"]],
        )
        if check_res.status_code != 200:
            module.exit_json(changed=False)
        changed = True
        if not module.check_mode:
            res = delete_with_context(
                array,
                "delete_policies_network_access_rules",
                CONTEXT_VERSION,
                module,
                policy_names=[module.params["name"]],
                names=[module.params["rule_name"]],
            )
            if res.status_code != 200:
                module.fail_json(
                    msg=f"Failed to delete rule {module.params['rule_name']} "
                    f"from network-access policy {module.params['name']}. "
                    f"Error: {res.errors[0].message}"
                )
    else:
        arr_res = get_with_context(
            array,
            "get_arrays",
            CONTEXT_VERSION,
            module,
        )
        if arr_res.status_code == 200:
            arr_items = list(arr_res.items)
            if arr_items:
                active_policy = getattr(arr_items[0], "network_access_policy", None)
                if (
                    active_policy
                    and getattr(active_policy, "name", None) == module.params["name"]
                ):
                    module.fail_json(
                        msg=f"Cannot delete network-access policy {module.params['name']} "
                        f"because it is the active array policy. Activate another policy first."
                    )
        changed = True
        if not module.check_mode:
            res = delete_with_context(
                array,
                "delete_policies_network_access",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
            )
            if res.status_code != 200:
                module.fail_json(
                    msg=f"Deletion of network-access policy {module.params['name']} failed. "
                    f"Error: {res.errors[0].message}"
                )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            enabled=dict(type="bool"),
            rename=dict(type="str"),
            active=dict(type="bool"),
            effect=dict(type="str", choices=["allow", "deny"]),
            client=dict(type="str"),
            interfaces=dict(
                type="list",
                elements="str",
                choices=[
                    "management-ssh",
                    "management-rest-api",
                    "management-rest-api-v1",
                    "management-rest-api-v2",
                    "management-web-ui",
                    "snmp",
                ],
            ),
            index=dict(type="int"),
            rule_name=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=True,
    )

    if module.params["active"] and module.params["enabled"] is False:
        module.fail_json(msg="Cannot activate a disabled network-access policy")

    if module.params["interfaces"] is not None and not module.params["interfaces"]:
        module.fail_json(
            msg="interfaces must contain at least one management interface"
        )

    rule_attrs = [
        module.params["effect"],
        module.params["client"],
        module.params["interfaces"],
    ]
    if not module.params["rule_name"] and any(rule_attrs) and not all(rule_attrs):
        module.fail_json(
            msg="Adding a rule requires effect, client, and interfaces to be "
            "provided together. To modify an existing rule, supply rule_name "
            "with any subset of these attributes."
        )

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    api_version = array.get_rest_version()
    if LooseVersion(MIN_REQUIRED_API_VERSION) > LooseVersion(api_version):
        module.fail_json(
            msg="FlashArray REST version not supported for network-access policies. "
            "Minimum version required: {0}".format(MIN_REQUIRED_API_VERSION)
        )

    state = module.params["state"]
    exists = bool(
        get_with_context(
            array,
            "get_policies_network_access",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
        ).status_code
        == 200
    )

    if state == "present" and not exists and module.params["rename"]:
        check_renamed_policy(module, array)
    elif state == "present" and not exists:
        create_policy(module, array)
    elif state == "present" and exists and module.params["rename"]:
        rename_policy(module, array)
    elif state == "present" and exists:
        update_policy(module, array)
    elif state == "absent" and exists:
        delete_policy(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
