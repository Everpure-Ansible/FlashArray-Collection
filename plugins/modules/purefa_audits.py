#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2024, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_audits
version_added: '1.29.0'
short_description: List FlashArray Audit Events
description:
- List audit events based on filters provided
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  start:
    description:
    - Only audit events logged at or after this date and time are returned.
    - Interpreted in the timezone given by I(timezone), or in the timezone
      resolved when I(timezone) is not provided.
    - If not provided epoch is assumed
    - Expected format "YYYY-MM-DD hh:mm:ss"
    type: str
  timezone:
    description:
    - The timezone in which I(start) is interpreted and in which the C(time)
      of each returned audit event is reported, for example C(America/New_York).
    - If not provided, the timezone configured on the FlashArray is used
      (Purity//FA 6.5.3 and later). On older Purity versions the local timezone
      of the host running the module is used instead, falling back to UTC.
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
- name: Show all audit events that started after the specified date/time and TZ
  purefa_audits:
    start: "2024-06-29 12:31:34"
    timezone: "America/New_York"
    fa_url: 10.10.10.2
    api_token: 89a9356f-c203-d263-8a89-c229486a13ba

- name: Show all audit events that have been logged by the array (to the internal limit of the array)
  purefa_audits:
    fa_url: 10.10.10.2
    api_token: 89a9356f-c203-d263-8a89-c229486a13ba
"""

RETURN = r"""
purefa_audits:
  description:
    - The audit events read from the array, keyed by audit record name.
    - A field the array did not record for an event is returned as C(none).
  returned: always
  type: dict
  contains:
    time:
      description:
        - When the command was run, as C(YYYY-MM-DD HH:MM:SS ZONE) in the
          timezone given by I(timezone) or the timezone resolved when
          I(timezone) is not provided.
      type: str
      sample: 2024-06-29 12:31:34 EDT
    arguments:
      description: The arguments provided to the command.
      type: str
      sample: --size 10G vol1
    user:
      description: The user who ran the command.
      type: str
      sample: pureuser
    command:
      description: The top level command, which by convention starts with C(pure).
      type: str
      sample: purevol
    subcommand:
      description:
        - The C(command) and C(subcommand) combination determines which
          action the user attempted to perform.
      type: str
      sample: create
    origin:
      description: The name of the array from which the command originated.
      type: str
      sample: arrayA
  sample:
    "1044":
      time: 2024-06-29 12:31:34 EDT
      arguments: --size 10G vol1
      user: pureuser
      command: purevol
      subcommand: create
      origin: arrayA
"""

HAS_PYTZ = True
try:
    import pytz
except ImportError:
    HAS_PYTZ = False

import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.common import (
    get_local_tz,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    get_with_context,
)

TZ_VERSION = "2.26"
CONTEXT_VERSION = "2.38"


def _to_timestamp(module, name, timezone):
    """Convert the date/time in parameter ``name`` to epoch milliseconds"""
    value = module.params[name] + " " + timezone
    try:
        return int(
            1000
            * datetime.datetime.timestamp(
                datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
            )
        )
    except ValueError:
        module.fail_json(
            msg="{0} value {1} is not a valid date/time. "
            'Expected format is "YYYY-MM-DD hh:mm:ss"'.format(name, module.params[name])
        )


def _get_filter_string(module, timezone):
    filter_string = ""
    if module.params["start"] and module.params["start"] != "0":
        start_timestamp = _to_timestamp(module, "start", timezone)
    else:
        start_timestamp = 0
    filter_string = "time>=" + str(start_timestamp)
    return filter_string


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            start=dict(type="str"),
            timezone=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PYTZ:
        module.fail_json(msg="pytz is required for this module")

    array = get_array(module)
    api_version = array.get_rest_version()
    if not module.params["timezone"] and LooseVersion(TZ_VERSION) <= LooseVersion(
        api_version
    ):
        res = get_with_context(array, "get_arrays", CONTEXT_VERSION, module)
        timezone = list(res.items)[0].time_zone
    elif not module.params["timezone"]:
        timezone = get_local_tz(module)
    elif module.params["timezone"] not in pytz.all_timezones_set:
        module.fail_json(
            msg="Timezone {0} is not valid".format(module.params["timezone"])
        )
    else:
        timezone = module.params["timezone"]
    tzoffset = datetime.datetime.now(pytz.timezone(timezone)).strftime("%z")
    filter_string = _get_filter_string(module, tzoffset)
    audit_log = {}
    kwargs = {}
    if filter_string:
        kwargs["filter"] = filter_string
    res = get_with_context(array, "get_audits", CONTEXT_VERSION, module, **kwargs)
    if res.status_code == 200:
        audits = list(res.items)
    else:
        module.fail_json(
            msg="Failed to get audit events. Error: {0}".format(res.errors[0].message)
        )
    for audit in audits:
        name = audit.name
        time = datetime.datetime.fromtimestamp(
            audit.time / 1000, tz=pytz.timezone(timezone)
        ).strftime("%Y-%m-%d %H:%M:%S %Z")
        # Audit records only carry the fields that apply to the event, and the
        # SDK models raise AttributeError for an absent field, so read each
        # one with a default.
        audit_log[name] = {
            "time": time,
            "arguments": getattr(audit, "arguments", None),
            "user": getattr(audit, "user", None),
            "command": getattr(audit, "command", None),
            "subcommand": getattr(audit, "subcommand", None),
            "origin": getattr(getattr(audit, "origin", None), "name", None),
        }
    module.exit_json(changed=False, purefa_audits=audit_log)


if __name__ == "__main__":
    main()
