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
module: purefa_apiclient
version_added: '1.5.0'
short_description: Manage FlashArray API Clients
description:
- Enable or disable FlashArray API Clients
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
notes:
- The array only allows the enabled state of an existing API client to be
  changed. I(public_key), I(issuer), I(role) and I(token_ttl) cannot be
  changed in place, so when a supplied value differs from the array the
  module warns and leaves the client as it is. Delete and recreate the
  client to apply a new value.
options:
  name:
    description:
    - Name of the API Client
    type: str
    required: true
  state:
    description:
    - Define whether the API client should exist or not.
    default: present
    choices: [ absent, present ]
    type: str
  role:
    description:
    - The maximum role allowed for ID Tokens issued by this API client
    type: str
    choices: [readonly, ops_admin, storage_admin, array_admin]
  issuer:
    description:
    - The name of the identity provider that will be issuing ID Tokens for this API client
    - If not specified, defaults to the API client name, I(name).
    type: str
  public_key:
    description:
    - The API clients PEM formatted (Base64 encoded) RSA public key.
    - Include the I(—–BEGIN PUBLIC KEY—–) and I(—–END PUBLIC KEY—–) lines
    type: str
  token_ttl:
    description:
    - Time To Live, in seconds, of the access tokens exchanged for this
      client's ID tokens. The array stores the value in milliseconds, so the
      module multiplies the value given here by 1000.
    - Range is 1 second to 1 day (86400 seconds).
    - If not specified when creating a client, defaults to 86400.
    type: int
  enabled:
    description:
    - State of the API Client Key
    type: bool
    default: true
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create API token ansible-token
  everpure.flasharray.purefa_apiclient:
    name: ansible-token
    issuer: "Everpure"
    token_ttl: 3000  # seconds, sent to the array as 3000000 milliseconds
    role: array_admin
    public_key: "{{lookup('file', 'public_pem_file') }}"
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Disable API CLient
  everpure.flasharray.purefa_apiclient:
    name: ansible-token
    enabled: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Enable API CLient
  everpure.flasharray.purefa_apiclient:
    name: ansible-token
    enabled: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete API Client
  everpure.flasharray.purefa_apiclient:
    state: absent
    name: ansible-token
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
    check_response,
)

MIN_REQUIRED_API_VERSION = "2.1"


def delete_client(module, array):
    changed = True
    if not module.check_mode:
        res = array.delete_api_clients(names=[module.params["name"]])
        check_response(
            res, module, f"Failed to delete API Client {module.params['name']}"
        )
    module.exit_json(changed=changed)


def update_client(module, array, client):
    """Update API Client

    The array only allows the enabled state of an existing API client to be
    changed (ApiClientPatch has no other field), so a supplied public_key,
    issuer, role or token_ttl that differs from the array is reported as a
    warning rather than silently ignored.
    """
    changed = False
    immutable = []
    if module.params["public_key"] is not None:
        # Compare ignoring whitespace so line wrapping or a trailing newline
        # from a file lookup does not count as a different key.
        current_key = "".join((getattr(client, "public_key", None) or "").split())
        if "".join(module.params["public_key"].split()) != current_key:
            immutable.append("public_key")
    if module.params["issuer"] is not None and module.params["issuer"] != getattr(
        client, "issuer", None
    ):
        immutable.append("issuer")
    if module.params["role"] is not None and module.params["role"] != getattr(
        client, "max_role", None
    ):
        immutable.append("role")
    if module.params["token_ttl"] is not None and module.params[
        "token_ttl"
    ] * 1000 != getattr(client, "access_token_ttl_in_ms", None):
        immutable.append("token_ttl")
    if immutable:
        module.warn(
            "API Client {0}: {1} cannot be changed on an existing client and "
            "will remain as currently set on the array. Delete and recreate "
            "the client to apply the new value(s).".format(
                module.params["name"], ", ".join(immutable)
            )
        )
    if client.enabled != module.params["enabled"]:
        changed = True
        if not module.check_mode:
            res = array.patch_api_clients(
                names=[module.params["name"]],
                api_clients=flasharray.ApiClientPatch(enabled=module.params["enabled"]),
            )
            check_response(
                res, module, f"Failed to update API Client {module.params['name']}"
            )
    module.exit_json(changed=changed)


def create_client(module, array):
    """Create API Client"""
    changed = True
    if module.params["token_ttl"] is None:
        module.params["token_ttl"] = 86400
    if not 1 <= module.params["token_ttl"] <= 86400:
        module.fail_json(msg="token_ttl parameter is out of range (1 to 86400)")
    else:
        token_ttl = module.params["token_ttl"] * 1000
    if not module.params["issuer"]:
        module.params["issuer"] = module.params["name"]
    client = flasharray.ApiClientPost(
        max_role=module.params["role"],
        issuer=module.params["issuer"],
        access_token_ttl_in_ms=token_ttl,
        public_key=module.params["public_key"],
    )
    if not module.check_mode:
        res = array.post_api_clients(names=[module.params["name"]], api_clients=client)
        check_response(
            res, module, f"Failed to create API Client {module.params['name']}"
        )
        if module.params["enabled"]:
            res = array.patch_api_clients(
                names=[module.params["name"]],
                api_clients=flasharray.ApiClientPatch(enabled=module.params["enabled"]),
            )
            if res.status_code != 200:
                array.delete_api_clients(names=[module.params["name"]])
                module.fail_json(
                    msg="Failed to create API Client {0}. Error: {1}".format(
                        module.params["name"], res.errors[0].message
                    )
                )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            enabled=dict(type="bool", default=True),
            name=dict(type="str", required=True),
            role=dict(
                type="str",
                choices=["readonly", "ops_admin", "storage_admin", "array_admin"],
            ),
            public_key=dict(type="str", no_log=True),
            token_ttl=dict(type="int", no_log=False),
            issuer=dict(type="str"),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    api_version = array.get_rest_version()

    if LooseVersion(MIN_REQUIRED_API_VERSION) > LooseVersion(api_version):
        module.fail_json(
            msg="FlashArray REST version not supported. "
            "Minimum version required: {0}".format(MIN_REQUIRED_API_VERSION)
        )
    state = module.params["state"]

    try:
        client = list(array.get_api_clients(names=[module.params["name"]]).items)[0]
        exists = True
    except Exception:
        exists = False

    if not exists and state == "present":
        create_client(module, array)
    elif exists and state == "present":
        update_client(module, array, client)
    elif exists and state == "absent":
        delete_client(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
