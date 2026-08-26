#!/usr/bin/python
# -*- coding: utf-8 -*-

# 2018, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_smtp
version_added: '1.0.0'
author:
  - Everpure ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
short_description: Configure FlashArray SMTP settings
description:
- Set or erase configuration for the SMTP settings.
- If username/password are set this will always force a change as there is
  no way to see if the password is different from the current SMTP configuration.
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  state:
    description:
    - Set or delete SMTP configuration
    default: present
    type: str
    choices: [ absent, present ]
  password:
    description:
    - The SMTP password.
    type: str
  user:
    description:
    - The SMTP username.
    type: str
  relay_host:
    description:
    - IPv4 or IPv6 address or FQDN. A port number may be appended.
    type: str
  sender_domain:
    description:
    - Domain name.
    type: str
  sender:
    description:
    - The local-part of the email address used when sending alert email messages.
    type: str
    version_added: "1.33.0"
  subject_prefix:
    description:
    - Optional string added to the beginning of the subject when sending alert
      email messages.
    - HTML tags are not allowed.
    type: str
    version_added: "1.33.0"
  body_prefix:
    description:
    - Optional string added to the beginning of the email body when sending
      alert email messages.
    - HTML tags are not allowed.
    type: str
    version_added: "1.33.0"
  encryption_mode:
    description:
    - Enforces an encryption mode when sending alert email messages.
    - Use empty string to clear.
    type: str
    choices: [ 'starttls', '' ]
    default: starttls
    version_added: "1.33.0"
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Delete existing SMTP settings
  everpure.flasharray.purefa_smtp:
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
- name: Set SMTP settings
  everpure.flasharray.purefa_smtp:
    sender_domain: everpuredata.com
    password: account_password
    user: smtp_account
    sender: array_email
    body_prefix: "SMTP-Body"
    subject_prefix: "SMTP"
    relay_host: 10.2.56.78:2345
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import SmtpServer
except ImportError:
    HAS_PURESTORAGE = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_response,
)

SMTP_FIELDS = (
    "sender_domain",
    "relay_host",
    "user_name",
    "encryption_mode",
    "sender_username",
    "subject_prefix",
    "body_prefix",
)

# The settings written by ``state: absent``, and therefore the state in which
# there is nothing left to delete.
CLEARED_SMTP = {
    "sender_domain": "None",
    "relay_host": "",
    "user_name": "",
    "encryption_mode": "",
    "sender_username": "",
    "subject_prefix": "",
    "body_prefix": "",
}


def _get_current_smtp(array):
    """Return the current SMTP settings as a dict of strings.

    Any setting the array has not configured is reported as an empty string.
    The SDK models raise AttributeError for null fields, so every read needs
    a default, and that default has to be the same one used when building the
    desired settings - otherwise unset fields compare as None against "" and
    the module reports a change on every run.
    """
    # Currently only 1 SMTP server is configurable
    current_smtp = list(array.get_smtp_servers().items)[0]
    return {field: getattr(current_smtp, field, "") or "" for field in SMTP_FIELDS}


def delete_smtp(module, array):
    """Delete SMTP settings"""
    changed = _get_current_smtp(array) != CLEARED_SMTP
    if changed and not module.check_mode:
        res = array.patch_smtp_servers(
            smtp=SmtpServer(
                sender_domain=CLEARED_SMTP["sender_domain"],
                user_name=CLEARED_SMTP["user_name"],
                password="",
                relay_host=CLEARED_SMTP["relay_host"],
                encryption_mode=CLEARED_SMTP["encryption_mode"],
                sender_username=CLEARED_SMTP["sender_username"],
                subject_prefix=CLEARED_SMTP["subject_prefix"],
                body_prefix=CLEARED_SMTP["body_prefix"],
            )
        )
        check_response(res, module, "Delete SMTP settings failed")
    module.exit_json(changed=changed)


def create_smtp(module, array):
    """Set SMTP settings"""
    changed = False
    current_server = _get_current_smtp(array)
    new_server = dict(current_server)

    if module.params["sender_domain"]:
        new_server["sender_domain"] = module.params["sender_domain"]
    if module.params["relay_host"]:
        new_server["relay_host"] = module.params["relay_host"]
    if module.params["user"]:
        new_server["user_name"] = module.params["user"]
    if module.params["sender"]:
        new_server["sender_username"] = module.params["sender"]
    if module.params["body_prefix"]:
        new_server["body_prefix"] = module.params["body_prefix"]
    if module.params["subject_prefix"]:
        new_server["subject_prefix"] = module.params["subject_prefix"]
    # An empty string is a valid encryption_mode - it clears the setting - so
    # this parameter is checked against None rather than for truthiness.
    if module.params["encryption_mode"] is not None:
        new_server["encryption_mode"] = module.params["encryption_mode"]

    if new_server != current_server or module.params["password"]:
        changed = True
        if not module.check_mode:
            smtp_settings = {
                "sender_domain": new_server["sender_domain"],
                "relay_host": new_server["relay_host"],
                "encryption_mode": new_server["encryption_mode"],
                "sender_username": new_server["sender_username"],
                "subject_prefix": new_server["subject_prefix"],
                "body_prefix": new_server["body_prefix"],
            }
            if module.params["password"]:
                smtp_settings["user_name"] = module.params["user"]
                smtp_settings["password"] = module.params["password"]
            res = array.patch_smtp_servers(smtp=SmtpServer(**smtp_settings))
            check_response(res, module, "Failed to change SMTP server details")
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            sender_domain=dict(type="str"),
            password=dict(type="str", no_log=True),
            user=dict(type="str"),
            sender=dict(type="str"),
            subject_prefix=dict(type="str"),
            body_prefix=dict(type="str"),
            encryption_mode=dict(
                type="str", choices=["starttls", ""], default="starttls"
            ),
            relay_host=dict(type="str"),
        )
    )

    required_together = [["user", "password"]]
    module = AnsibleModule(
        argument_spec,
        required_together=required_together,
        supports_check_mode=True,
    )
    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    state = module.params["state"]
    array = get_array(module)

    if state == "absent":
        delete_smtp(module, array)
    elif state == "present":
        create_smtp(module, array)
    else:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
