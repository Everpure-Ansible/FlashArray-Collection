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
module: purefa_dns
version_added: '1.0.0'
short_description: Configure FlashArray DNS settings
description:
- Set or erase configuration for the DNS settings.
- Nameservers provided will overwrite any existing nameservers.
- From Purity//FA 6.3.3 DNS setting for FA-File can be configured separately
  to the management DNS settings
- A DNS configuration may also be created without any service. Such a
  configuration is not used by the array itself, but can be given to a file
  server with M(everpure.flasharray.purefa_server), which is how each file
  server on an array gets its own DNS settings.
- The array allows at most one configuration per service. Only the
  configuration named C(management) can carry the C(management) service.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the DNS configuration.
    - The management DNS configuration is always named C(management).
    default: management
    type: str
    version_added: 1.14.0
  state:
    description:
    - Set or delete directory service configuration
    default: present
    type: str
    choices: [ absent, present ]
  domain:
    description:
    - Domain suffix to be appended when perofrming DNS lookups.
    type: str
  nameservers:
    description:
    - List of up to 3 unique DNS server IP addresses. These can be
      IPv4 or IPv6 - No validation is done of the addresses is performed.
    type: list
    elements: str
  service:
    description:
    - Type of service the DNS will work with.
    - When omitted a new configuration is created without a service, for
      use by a file server. The service of an existing configuration is
      never changed.
    - The configuration named C(management) is always the management service,
      whether or not this is set.
    type: str
    version_added: 1.14.0
    choices: [ management, file ]
  source:
    description:
    - A virtual network interface (vif)
    type: str
    version_added: 1.14.0
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
    version_added: 1.40.0
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Delete existing management DNS settings
  everpure.flasharray.purefa_dns:
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Set managemnt DNS settings
  everpure.flasharray.purefa_dns:
    domain: everpuredata.com
    nameservers:
      - 8.8.8.8
      - 8.8.4.4
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Set file DNS settings
  everpure.flasharray.purefa_dns:
    domain: everpuredata.com
    nameservers:
      - 8.8.8.8
      - 8.8.4.4
    name: ad_dns
    service: file
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create a DNS configuration with no service, for a file server
  everpure.flasharray.purefa_dns:
    domain: lab.everpuredata.com
    nameservers:
      - 10.0.0.53
    name: filesvr2-dns
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Give a file server that DNS configuration
  everpure.flasharray.purefa_server:
    name: filesvr2
    dns: filesvr2-dns
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete file DNS settings
  everpure.flasharray.purefa_dns:
    state: absent
    name: ad_dns
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import DnsPost, DnsPatch, ReferenceNoId
except ImportError:
    HAS_PURESTORAGE = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    get_with_context,
    check_response,
)

MULTIPLE_DNS = "2.15"
CONTEXT_API_VERSION = "2.47"
MANAGEMENT = "management"


def remove(duplicate):
    final_list = []
    for num in duplicate:
        if num not in final_list:
            final_list.append(num)
    return final_list


def _get_dns_field(config, field):
    if isinstance(config, dict):
        return config.get(field)
    return getattr(config, field, None)


def _get_source(module, array):
    res = get_with_context(
        array,
        "get_network_interfaces",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["source"]],
    )
    return bool(res.status_code == 200)


def delete_dns(module, array):
    """Delete DNS settings"""
    changed = False
    current_dns = list(
        get_with_context(array, "get_dns", CONTEXT_API_VERSION, module).items
    )[0]
    if getattr(current_dns, "domain", None) in ["", None] and getattr(
        current_dns, "nameservers", None
    ) in [[""], None]:
        module.exit_json(changed=changed)
    else:
        changed = True
        if not module.check_mode:
            res = get_with_context(
                array,
                "delete_dns",
                CONTEXT_API_VERSION,
                module,
                names=[MANAGEMENT],
            )
            check_response(res, module, "Delete DNS settings")
    module.exit_json(changed=changed)


def create_dns(module, array):
    """Set DNS settings"""
    changed = False
    current_dns = list(
        get_with_context(array, "get_dns", CONTEXT_API_VERSION, module).items
    )[0]
    if _get_dns_field(current_dns, "domain") != module.params["domain"] or sorted(
        module.params["nameservers"]
    ) != sorted(_get_dns_field(current_dns, "nameservers") or []):
        changed = True
        if not module.check_mode:
            res = get_with_context(
                array,
                "patch_dns",
                CONTEXT_API_VERSION,
                module,
                names=[MANAGEMENT],
                dns=DnsPatch(
                    domain=module.params["domain"],
                    nameservers=module.params["nameservers"][0:3],
                ),
            )
            check_response(res, module, "Set DNS settings")
    module.exit_json(changed=changed)


def update_multi_dns(module, array):
    """Update a DNS configuration"""
    changed = False
    current_dns = list(
        get_with_context(
            array,
            "get_dns",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        ).items
    )[0]
    # A configuration can carry more than one service (the management one
    # also serves files until a file configuration exists), so the requested
    # service only has to be among them. It can never be changed in place.
    # (SDK models raise AttributeError for fields the array did not return,
    # hence the getattr defaults.)
    if module.params["service"] and module.params["service"] not in (
        getattr(current_dns, "services", None) or []
    ):
        module.fail_json(msg="Changing service type is not permitted")
    domain = current_dns.domain
    if module.params["domain"] and current_dns.domain != module.params["domain"]:
        domain = module.params["domain"]
        changed = True
    nameservers = current_dns.nameservers
    if module.params["nameservers"] and sorted(current_dns.nameservers or []) != sorted(
        module.params["nameservers"]
    ):
        nameservers = module.params["nameservers"]
        changed = True
    patch_kwargs = {"domain": domain, "nameservers": nameservers}
    if module.params["source"] is not None:
        current_source = (
            getattr(getattr(current_dns, "source", None), "name", None) or ""
        )
        if current_source != module.params["source"]:
            changed = True
        patch_kwargs["source"] = ReferenceNoId(name=module.params["source"])
    if changed and not module.check_mode:
        res = get_with_context(
            array,
            "patch_dns",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            dns=DnsPatch(**patch_kwargs),
        )
        check_response(res, module, f"Update to DNS service {module.params['name']}")
    module.exit_json(changed=changed)


def delete_multi_dns(module, array):
    """Delete a DNS configuration"""
    changed = True
    if not module.check_mode:
        if module.params["name"] == MANAGEMENT:
            # The management configuration cannot be deleted, only emptied
            res = get_with_context(
                array,
                "patch_dns",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                dns=DnsPatch(domain="", nameservers=[]),
            )
            check_response(res, module, "Management DNS configuration not deleted")
        else:
            res = get_with_context(
                array,
                "delete_dns",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
            )
            check_response(
                res,
                module,
                f"Failed to delete DNS configuration {module.params['name']}",
            )
    module.exit_json(changed=changed)


def create_multi_dns(module, array):
    """Create a DNS configuration"""
    changed = True
    if not module.check_mode:
        post_kwargs = {
            "domain": module.params["domain"],
            "nameservers": module.params["nameservers"],
        }
        # No service means a configuration for a file server to use. The
        # array enforces one configuration per service and reports a clear
        # error if a second one is attempted.
        if module.params["service"]:
            post_kwargs["services"] = [module.params["service"]]
        if module.params["source"]:
            post_kwargs["source"] = ReferenceNoId(name=module.params["source"].lower())
        res = get_with_context(
            array,
            "post_dns",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            dns=DnsPost(**post_kwargs),
        )
        check_response(
            res,
            module,
            f"Failed to create DNS configuration {module.params['name']}",
        )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            name=dict(type="str", default=MANAGEMENT),
            service=dict(type="str", choices=["management", "file"]),
            domain=dict(type="str"),
            source=dict(type="str"),
            nameservers=dict(type="list", elements="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    state = module.params["state"]
    array = get_array(module)
    api_version = array.get_rest_version()
    if module.params["context"] and LooseVersion(CONTEXT_API_VERSION) > LooseVersion(
        api_version
    ):
        module.fail_json(
            msg=f"`context` requires REST API version {CONTEXT_API_VERSION} or higher for DNS operations"
        )
    if module.params["nameservers"]:
        module.params["nameservers"] = remove(module.params["nameservers"])
        if (
            module.params["name"] == MANAGEMENT
            or module.params["service"] == MANAGEMENT
        ):
            module.params["nameservers"] = module.params["nameservers"][0:3]

    if LooseVersion(MULTIPLE_DNS) <= LooseVersion(api_version):
        configs = list(
            get_with_context(array, "get_dns", CONTEXT_API_VERSION, module).items
        )
        exists = False
        for config in configs:
            if config.name == module.params["name"]:
                exists = True
        # There is only ever one management configuration, and it is always
        # named management. Only redirect a create, never a delete, so a
        # wrong name can never empty the management configuration.
        if (
            state == "present"
            and module.params["service"] == MANAGEMENT
            and module.params["name"] != MANAGEMENT
            and not exists
        ):
            module.warn("Overriding configuration name to management")
            module.params["name"] = MANAGEMENT
            exists = any(config.name == MANAGEMENT for config in configs)
        if module.params["source"] and not _get_source(module, array):
            module.fail_json(
                msg="Specified VIF {0} does not exist.".format(module.params["source"])
            )
        if state == "present" and exists:
            update_multi_dns(module, array)
        elif state == "present" and not exists:
            create_multi_dns(module, array)
        elif exists and state == "absent":
            delete_multi_dns(module, array)
        else:
            module.exit_json(changed=False)
    else:
        if state == "absent":
            delete_dns(module, array)
        elif state == "present":
            if not module.params["domain"] or not module.params["nameservers"]:
                module.fail_json(
                    msg="`domain` and `nameservers` are required for DNS configuration"
                )
            create_dns(module, array)
        else:
            module.exit_json(changed=False)


if __name__ == "__main__":
    main()
