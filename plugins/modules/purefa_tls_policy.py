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
module: purefa_tls_policy
version_added: '1.46.0'
short_description: Manage Everpure FlashArray TLS policies
description:
- Create, update, rename or delete TLS policies on Everpure FlashArrays and
  manage the file servers they are attached to.
- A TLS policy is a reusable inbound TLS configuration. It controls the server
  certificate the array presents, the minimum TLS version and ciphers permitted,
  optional mutual-TLS verification of client certificates, and which protocols
  require TLS.
- In this release the only policy-aware protocol is NFS. A TLS policy attached
  to a file server applies to all of that server's VIFs.
- File servers are managed by M(everpure.flasharray.purefa_server). This module
  only attaches and detaches an existing TLS policy to and from them; it does
  not create or alter the servers themselves.
author:
- Everpure Ansible Team (@avk) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the TLS policy.
    type: str
    required: true
  state:
    description:
    - Define whether the TLS policy should exist or not.
    default: present
    type: str
    choices: [ absent, present ]
  enabled:
    description:
    - If C(true) the policy is enabled.
    - Defaults to C(true) on creation if not specified.
    type: bool
  rename:
    description:
    - Value to rename the specified TLS policy to.
    - The destination name must not already be in use.
    type: str
  appliance_certificate:
    description:
    - Name of the certificate the array presents as the server certificate in
      TLS negotiation with clients connecting to the file servers this policy
      applies to.
    - Required when creating a policy.
    type: str
  min_tls_version:
    description:
    - Minimum TLS version permitted for inbound connections.
    - C(default) lets the array pick a recommended minimum that may shift across
      software upgrades.
    type: str
    choices: [ default, '1.2', '1.3' ]
  enabled_tls_ciphers:
    description:
    - List of TLS ciphers to enable.
    - When supplied, only these ciphers will be enabled.
    - The literal value C(default) lets the array manage the enabled ciphers and
      adjust them across software upgrades.
    type: list
    elements: str
  disabled_tls_ciphers:
    description:
    - List of TLS ciphers to disable.
    type: list
    elements: str
  tls_enforced_for:
    description:
    - List of protocols for which TLS is required. A protocol not in the list is
      not forced to negotiate TLS by this policy.
    - Only C(nfs) is valid in this release. Values are matched case-insensitively.
    - Use an empty list to stop enforcing TLS for any protocol.
    type: list
    elements: str
  client_certificates_required:
    description:
    - If C(true), all clients must present a client certificate during TLS
      negotiation; failure to do so is rejected.
    - If C(false), client certificates are optional.
    type: bool
  verify_client_certificate_trust:
    description:
    - If C(true), certificates presented by clients undergo strict trust
      verification using the certificate referenced by
      I(trusted_client_certificate_authority).
    type: bool
  trusted_client_certificate_authority:
    description:
    - Name of the certificate used to verify certificates presented by clients
      when I(verify_client_certificate_trust) is C(true).
    - Set to an empty string (C("")) to clear a previously assigned trusted CA
      reference. This only applies on update; on create an empty string is
      treated the same as omitting the parameter.
    type: str
  servers:
    description:
    - Desired set of file servers this policy should be attached to.
    - Declarative. File servers in the list that are not attached to this policy
      are attached, and servers attached to this policy that are not in the list
      are detached. An empty list detaches the policy from all servers.
    - Omit the option to leave the policy's server attachments alone.
    - A file server has at most one TLS policy. Attaching this policy to a server
      that already has a different one fails; detach the existing policy first.
    - A TLS policy cannot be attached to a file server that has S3 VIFs.
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
- Requires Purity//FA REST API 2.54 or higher, which is where TLS policies and
  the server-policy attachment first appear.
"""

EXAMPLES = r"""
- name: Create a server-authenticated NFS TLS policy
  everpure.flasharray.purefa_tls_policy:
    name: nfs_tls_policy
    appliance_certificate: nfs_server_cert
    min_tls_version: '1.3'
    tls_enforced_for:
      - nfs
    enabled_tls_ciphers:
      - TLS_AES_256_GCM_SHA384
      - TLS_CHACHA20_POLY1305_SHA256
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create a mutual-TLS policy for NFS
  everpure.flasharray.purefa_tls_policy:
    name: nfs_mtls_policy
    appliance_certificate: nfs_server_cert
    tls_enforced_for:
      - nfs
    client_certificates_required: true
    verify_client_certificate_trust: true
    trusted_client_certificate_authority: nfs_client_ca
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Raise the minimum TLS version without touching anything else
  everpure.flasharray.purefa_tls_policy:
    name: nfs_tls_policy
    min_tls_version: '1.3'
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Attach a TLS policy to a set of file servers
  everpure.flasharray.purefa_tls_policy:
    name: nfs_tls_policy
    servers:
      - filesvr1
      - filesvr2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Detach a TLS policy from all file servers
  everpure.flasharray.purefa_tls_policy:
    name: nfs_tls_policy
    servers: []
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Clear the trusted client CA and disable client verification
  everpure.flasharray.purefa_tls_policy:
    name: nfs_mtls_policy
    verify_client_certificate_trust: false
    trusted_client_certificate_authority: ""
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Disable a TLS policy without deleting it
  everpure.flasharray.purefa_tls_policy:
    name: nfs_tls_policy
    enabled: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename a TLS policy
  everpure.flasharray.purefa_tls_policy:
    name: nfs_tls_policy
    rename: nfs_tls_policy_v2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete an unattached TLS policy
  everpure.flasharray.purefa_tls_policy:
    name: nfs_tls_policy
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        PolicyAssignmentPost,
        PolicyAssignmentPostPolicy,
        PolicyTlsPatch,
        PolicyTlsPost,
        Reference,
        ReferenceWithType,
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

# TLS policies, their attributes and the server-policy attachment all arrived
# together in this version - there is no partial support to work around
MIN_API_VERSION_TLS_POLICY = "2.54"
MIN_API_VERSION_TLS_SERVER_POLICY = "2.54"

# Only NFS is policy-aware in this release
VALID_ENFORCED_PROTOCOLS = ("nfs",)


def _tls_enforced_for(module):
    """The tls_enforced_for value, lowercased, or None when not supplied

    Only C(nfs) is valid in this release, so anything else fails the module
    rather than being sent to the array.
    """
    values = module.params["tls_enforced_for"]
    if values is None:
        return None
    normalized = [v.lower() for v in values]
    invalid = sorted({v for v in normalized if v not in VALID_ENFORCED_PROTOCOLS})
    if invalid:
        module.fail_json(
            msg="tls_enforced_for only supports {0} in this release. Invalid: "
            "{1}".format(", ".join(VALID_ENFORCED_PROTOCOLS), invalid)
        )
    return normalized


def _read_policy(module, array, name):
    """Return the named TLS policy, or None if the array does not have it"""
    res = get_with_context(
        array, "get_policies_tls", MIN_API_VERSION_TLS_POLICY, module, names=[name]
    )
    if res.status_code != 200:
        return None
    return next(iter(list(res.items)), None)


def _attached_servers(module, array):
    """Names of the file servers this policy is currently attached to

    A membership names the server as its C(member) and the policy as its
    C(policy), so this reads the memberships of the policy and picks out the
    server on each.
    """
    res = get_with_context(
        array,
        "get_servers_policies_tls",
        MIN_API_VERSION_TLS_SERVER_POLICY,
        module,
        policy_names=[module.params["name"]],
    )
    if res.status_code != 200:
        return []
    names = []
    for item in list(res.items):
        member_name = getattr(getattr(item, "member", None), "name", None)
        if member_name:
            names.append(member_name)
    return sorted(names)


def _validate_attachable(module, array, servers):
    """Validate every server exists and isn't bound to a different TLS policy

    Called for the to-attach subset only: a server already bound to this policy
    is a no-op upstream and never reaches here.
    """
    if not servers:
        return
    res = get_with_context(
        array,
        "get_servers",
        MIN_API_VERSION_TLS_SERVER_POLICY,
        module,
        names=servers,
    )
    if res.status_code != 200:
        module.fail_json(msg="File server(s) not found: {0}".format(servers))
    found = {getattr(s, "name", None) for s in list(res.items)}
    missing = [s for s in servers if s not in found]
    if missing:
        module.fail_json(msg="File server(s) not found: {0}".format(missing))

    res = get_with_context(
        array,
        "get_servers_policies_tls",
        MIN_API_VERSION_TLS_SERVER_POLICY,
        module,
        member_names=servers,
    )
    if res.status_code != 200:
        return
    our_name = module.params["name"]
    conflicts = []
    for item in list(res.items):
        policy_name = getattr(getattr(item, "policy", None), "name", None)
        server_name = getattr(getattr(item, "member", None), "name", None)
        if policy_name and policy_name != our_name:
            conflicts.append((server_name, policy_name))
    if conflicts:
        formatted = ", ".join("{0}=>{1}".format(s, p) for s, p in conflicts)
        module.fail_json(
            msg="Cannot attach TLS policy {0} - the following file server(s) "
            "already have a different TLS policy applied: {1}. Detach the "
            "existing policy before re-attaching.".format(our_name, formatted)
        )


def _attach_server(module, array, server):
    """Attach this policy to a file server"""
    res = get_with_context(
        array,
        "post_servers_policies_tls",
        MIN_API_VERSION_TLS_SERVER_POLICY,
        module,
        member_names=[server],
        policies=PolicyAssignmentPost(
            policies=[
                PolicyAssignmentPostPolicy(policy=Reference(name=module.params["name"]))
            ]
        ),
    )
    check_response(
        res,
        module,
        "Failed to attach TLS policy {0} to file server {1}".format(
            module.params["name"], server
        ),
    )


def _detach_server(module, array, server):
    """Detach this policy from a file server"""
    res = get_with_context(
        array,
        "delete_servers_policies_tls",
        MIN_API_VERSION_TLS_SERVER_POLICY,
        module,
        policy_names=[module.params["name"]],
        member_names=[server],
    )
    check_response(
        res,
        module,
        "Failed to detach TLS policy {0} from file server {1}".format(
            module.params["name"], server
        ),
    )


def _reconcile_servers(module, array):
    """Make the policy's attached servers match the task

    Returns whether anything needed changing. Does nothing at all when the task
    did not name the option, so a task that says nothing about servers never
    detaches one.
    """
    wanted = module.params["servers"]
    if wanted is None:
        return False
    wanted = sorted(set(wanted))
    current = _attached_servers(module, array)
    to_attach = [s for s in wanted if s not in current]
    to_detach = [s for s in current if s not in wanted]
    if not to_attach and not to_detach:
        return False
    if to_attach:
        _validate_attachable(module, array, to_attach)
    if not module.check_mode:
        for server in to_attach:
            _attach_server(module, array, server)
        for server in to_detach:
            _detach_server(module, array, server)
    return True


def _build_post_kwargs(module):
    """Build kwargs for PolicyTlsPost from the options the task supplied

    Only options the task actually set are included, so the array applies its
    own defaults for the rest. The exception is C(enabled): the array requires
    it on create, so it defaults to C(true) here to match the documented
    behaviour.
    """
    kwargs = {}
    kwargs["enabled"] = (
        module.params["enabled"] if module.params["enabled"] is not None else True
    )
    if module.params["appliance_certificate"]:
        kwargs["appliance_certificate"] = ReferenceWithType(
            name=module.params["appliance_certificate"]
        )
    if module.params["client_certificates_required"] is not None:
        kwargs["client_certificates_required"] = module.params[
            "client_certificates_required"
        ]
    if module.params["verify_client_certificate_trust"] is not None:
        kwargs["verify_client_certificate_trust"] = module.params[
            "verify_client_certificate_trust"
        ]
    if module.params["trusted_client_certificate_authority"]:
        kwargs["trusted_client_certificate_authority"] = ReferenceWithType(
            name=module.params["trusted_client_certificate_authority"]
        )
    if module.params["min_tls_version"]:
        kwargs["min_tls_version"] = module.params["min_tls_version"]
    if module.params["enabled_tls_ciphers"] is not None:
        kwargs["enabled_tls_ciphers"] = module.params["enabled_tls_ciphers"]
    if module.params["disabled_tls_ciphers"] is not None:
        kwargs["disabled_tls_ciphers"] = module.params["disabled_tls_ciphers"]
    enforced = _tls_enforced_for(module)
    if enforced is not None:
        kwargs["tls_enforced_for"] = enforced
    return kwargs


def create_policy(module, array):
    """Create a TLS policy and optionally attach it to file servers"""
    changed = True
    if not module.params["appliance_certificate"]:
        module.fail_json(
            msg="Creating TLS policy {0} requires appliance_certificate.".format(
                module.params["name"]
            )
        )
    if module.params["servers"]:
        _validate_attachable(module, array, module.params["servers"])
    if not module.check_mode:
        res = get_with_context(
            array,
            "post_policies_tls",
            MIN_API_VERSION_TLS_POLICY,
            module,
            names=[module.params["name"]],
            policy=PolicyTlsPost(**_build_post_kwargs(module)),
        )
        check_response(
            res,
            module,
            "Failed to create TLS policy {0}".format(module.params["name"]),
        )
        for server in module.params["servers"] or []:
            _attach_server(module, array, server)
    module.exit_json(changed=changed)


def update_policy(module, array, policy):
    """Update a TLS policy and reconcile its server attachments"""
    changed = False
    patch = {}

    if module.params["enabled"] is not None and module.params["enabled"] != getattr(
        policy, "enabled", None
    ):
        patch["enabled"] = module.params["enabled"]

    if module.params["min_tls_version"] and module.params["min_tls_version"] != getattr(
        policy, "min_tls_version", None
    ):
        patch["min_tls_version"] = module.params["min_tls_version"]

    if module.params["client_certificates_required"] is not None and module.params[
        "client_certificates_required"
    ] != getattr(policy, "client_certificates_required", None):
        patch["client_certificates_required"] = module.params[
            "client_certificates_required"
        ]

    if module.params["verify_client_certificate_trust"] is not None and module.params[
        "verify_client_certificate_trust"
    ] != getattr(policy, "verify_client_certificate_trust", None):
        patch["verify_client_certificate_trust"] = module.params[
            "verify_client_certificate_trust"
        ]

    if module.params["enabled_tls_ciphers"] is not None:
        current = list(getattr(policy, "enabled_tls_ciphers", None) or [])
        if sorted(module.params["enabled_tls_ciphers"]) != sorted(current):
            patch["enabled_tls_ciphers"] = module.params["enabled_tls_ciphers"]

    if module.params["disabled_tls_ciphers"] is not None:
        current = list(getattr(policy, "disabled_tls_ciphers", None) or [])
        if sorted(module.params["disabled_tls_ciphers"]) != sorted(current):
            patch["disabled_tls_ciphers"] = module.params["disabled_tls_ciphers"]

    enforced = _tls_enforced_for(module)
    if enforced is not None:
        current = [v.lower() for v in getattr(policy, "tls_enforced_for", None) or []]
        if sorted(enforced) != sorted(current):
            patch["tls_enforced_for"] = enforced

    if module.params["appliance_certificate"]:
        current = getattr(getattr(policy, "appliance_certificate", None), "name", None)
        if module.params["appliance_certificate"] != current:
            patch["appliance_certificate"] = ReferenceWithType(
                name=module.params["appliance_certificate"]
            )

    if module.params["trusted_client_certificate_authority"] is not None:
        current = (
            getattr(
                getattr(policy, "trusted_client_certificate_authority", None),
                "name",
                None,
            )
            or ""
        )
        if module.params["trusted_client_certificate_authority"] != current:
            patch["trusted_client_certificate_authority"] = ReferenceWithType(
                name=module.params["trusted_client_certificate_authority"]
            )

    if module.params["servers"] is not None:
        if _reconcile_servers(module, array):
            changed = True

    if patch:
        changed = True
        if not module.check_mode:
            res = get_with_context(
                array,
                "patch_policies_tls",
                MIN_API_VERSION_TLS_POLICY,
                module,
                names=[module.params["name"]],
                policy=PolicyTlsPatch(**patch),
            )
            check_response(
                res,
                module,
                "Failed to update TLS policy {0}".format(module.params["name"]),
            )

    module.exit_json(changed=changed)


def rename_policy(module, array):
    """Rename a TLS policy"""
    changed = True
    if _read_policy(module, array, module.params["rename"]):
        module.fail_json(
            msg="Target TLS policy {0} already exists".format(module.params["rename"])
        )
    if not module.check_mode:
        res = get_with_context(
            array,
            "patch_policies_tls",
            MIN_API_VERSION_TLS_POLICY,
            module,
            names=[module.params["name"]],
            policy=PolicyTlsPatch(name=module.params["rename"]),
        )
        check_response(
            res,
            module,
            "Failed to rename TLS policy {0} to {1}".format(
                module.params["name"], module.params["rename"]
            ),
        )
    module.exit_json(changed=changed)


def delete_policy(module, array):
    """Delete a TLS policy, refusing while it is still attached to a server"""
    changed = True
    attached = _attached_servers(module, array)
    if attached:
        module.fail_json(
            msg="Cannot delete TLS policy {0} while it is attached to file "
            "server(s): {1}. Detach it first, for example with servers: [].".format(
                module.params["name"], attached
            )
        )
    if not module.check_mode:
        res = get_with_context(
            array,
            "delete_policies_tls",
            MIN_API_VERSION_TLS_POLICY,
            module,
            names=[module.params["name"]],
        )
        check_response(
            res,
            module,
            "Failed to delete TLS policy {0}".format(module.params["name"]),
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
            appliance_certificate=dict(type="str"),
            min_tls_version=dict(type="str", choices=["default", "1.2", "1.3"]),
            enabled_tls_ciphers=dict(type="list", elements="str"),
            disabled_tls_ciphers=dict(type="list", elements="str"),
            tls_enforced_for=dict(type="list", elements="str"),
            client_certificates_required=dict(type="bool"),
            verify_client_certificate_trust=dict(type="bool"),
            trusted_client_certificate_authority=dict(type="str"),
            servers=dict(type="list", elements="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(
        argument_spec,
        required_if=[
            (
                "verify_client_certificate_trust",
                True,
                ["trusted_client_certificate_authority"],
            ),
        ],
        supports_check_mode=True,
    )

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    # Validate protocol values before touching the array
    _tls_enforced_for(module)

    array = get_array(module)
    check_api_version(array, MIN_API_VERSION_TLS_POLICY, module, "TLS policies")

    state = module.params["state"]
    policy = _read_policy(module, array, module.params["name"])

    if state == "present" and module.params["rename"]:
        if policy:
            rename_policy(module, array)
        elif _read_policy(module, array, module.params["rename"]):
            # Already renamed, so re-running the same task has nothing left to
            # do. Recreating the old name would be the opposite of what was
            # asked for.
            module.exit_json(changed=False)
        else:
            module.fail_json(
                msg="TLS policy {0} not found to rename".format(module.params["name"])
            )
    elif state == "present" and not policy:
        create_policy(module, array)
    elif state == "present":
        update_policy(module, array, policy)
    elif state == "absent" and policy:
        delete_policy(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
