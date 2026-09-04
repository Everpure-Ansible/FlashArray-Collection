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
module: purefa_tags
version_added: '1.45.0'
short_description: Manage Everpure FlashArray resource tags
description:
- Add, change and remove key/value tags on Everpure FlashArray resources.
- One module covers every taggable resource type. Which type is being tagged is
  given by I(resource_type), and the resource itself by I(name).
- Volumes are not included. They have their own module,
  M(everpure.flasharray.purefa_volume_tags), which also exposes the volume-only
  behaviour of I(copyable).
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  resource_type:
    description:
    - The kind of resource to tag.
    - C(array) tags the array itself and takes no I(name).
    - Each type became taggable in a different Purity//FA release, so the
      module checks the REST version for the type requested rather than one
      version for all of them.
    type: str
    required: true
    choices:
    - array
    - host
    - host_group
    - pod
    - protection_group
    - protection_group_snapshot
    - realm
    - volume_group
    - volume_snapshot
    - workload
  name:
    description:
    - Name of the resource to tag.
    - Required for every I(resource_type) except C(array), which is the array
      the module is talking to.
    type: str
  namespace:
    description:
    - The tag namespace to work in.
    - Namespaces are independent - the same key can hold a different value in
      each, and a tag is only ever read, written or removed in the namespace
      named here.
    default: default
    type: str
  kvp:
    description:
    - List of key value pairs to set on the resource.
    - Separate the key from the value using a colon (:) only.
    - Required when I(state=present).
    - With I(state=absent) and no I(keys), the keys of these pairs are the tags
      removed, and their values are ignored.
    type: list
    elements: str
  keys:
    description:
    - List of tag keys to remove, for use with I(state=absent).
    - Takes precedence over the keys in I(kvp).
    type: list
    elements: str
  copyable:
    description:
    - Whether the tag is inherited by copies of the resource.
    - Only the volume family honours this. The array accepts it for the other
      resource types and silently stores C(true) regardless, so it is only
      compared, and only reported as a change, for C(volume_group) and
      C(volume_snapshot).
    - Omit it to let the array use its own default.
    type: bool
  state:
    description:
    - Define whether the tags should exist or not.
    default: present
    choices: [ absent, present ]
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
- The minimum Purity//FA REST version depends on I(resource_type)
  - C(volume_snapshot) from 2.2, C(array), C(host) and C(host_group) from 2.34,
  C(pod), C(protection_group) and C(volume_group) from 2.39, C(workload) from
  2.40, C(realm) from 2.41 and C(protection_group_snapshot) from 2.44.
- Tagging a resource that does not exist fails with the array's own message,
  which names the resource type.
- Cloud provider tags, which propagate to the cloud a Cloud Block Store
  instance runs in, are a separate namespace of their own and are not managed
  here.
"""

EXAMPLES = r"""
- name: Tag host foo
  everpure.flasharray.purefa_tags:
    resource_type: host
    name: foo
    kvp:
    - env:production
    - owner:infra
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Tag the array itself
  everpure.flasharray.purefa_tags:
    resource_type: array
    kvp:
    - site:london
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Tag a volume group so copies inherit the tag
  everpure.flasharray.purefa_tags:
    resource_type: volume_group
    name: bar
    kvp:
    - backup:nightly
    copyable: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Tag a protection group in its own namespace
  everpure.flasharray.purefa_tags:
    resource_type: protection_group
    name: pgroup1
    namespace: reporting
    kvp:
    - tier:gold
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Remove two tags from host foo
  everpure.flasharray.purefa_tags:
    resource_type: host
    name: foo
    keys:
    - env
    - owner
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import Tag, TagBatch
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
    put_with_context,
)

CONTEXT_VERSION = "2.38"

# Each resource type, the name it goes by in the API, and the REST version its
# tag endpoints arrived in. The versions differ widely, so the guardrail is per
# type rather than one floor for the module.
RESOURCES = {
    "array": ("arrays", "2.34"),
    "host": ("hosts", "2.34"),
    "host_group": ("host_groups", "2.34"),
    "pod": ("pods", "2.39"),
    "protection_group": ("protection_groups", "2.39"),
    "protection_group_snapshot": ("protection_group_snapshots", "2.44"),
    "realm": ("realms", "2.41"),
    "volume_group": ("volume_groups", "2.39"),
    "volume_snapshot": ("volume_snapshots", "2.2"),
    "workload": ("workloads", "2.40"),
}

# The array is a singleton, so its tag endpoints take no resource name, and the
# write is a plain put rather than the batch form every other type uses.
SINGLETON = "array"

# Only the volume family stores copyable as given. The others accept the field
# and report true whatever was sent, so comparing it there would make a play
# that sets copyable=false report a change on every run.
COPYABLE_TYPES = ("volume_group", "volume_snapshot")


def _api_name(module):
    """The API's name for the requested resource type"""
    return RESOURCES[module.params["resource_type"]][0]


def _resource_args(module):
    """The parameters that name the resource being tagged"""
    if module.params["resource_type"] == SINGLETON:
        return {}
    return {"resource_names": [module.params["name"]]}


def _compares_copyable(module):
    """Whether copyable is worth comparing for this resource type"""
    return (
        module.params["copyable"] is not None
        and module.params["resource_type"] in COPYABLE_TYPES
    )


def parse_kvp(module):
    """Return the requested tags as a list of (key, value)

    A pair is split on the first colon only, so a value may contain one.
    """
    pairs = []
    for item in module.params["kvp"] or []:
        if ":" not in item:
            module.fail_json(msg="kvp entry {0} is not in key:value form".format(item))
        key, value = item.split(":", 1)
        if not key:
            module.fail_json(msg="kvp entry {0} has an empty key".format(item))
        pairs.append((key, value))
    return pairs


def read_tags(module, array):
    """Return the resource's tags in the requested namespace

    The namespace is always sent - a read that leaves it out comes back with
    the default namespace only, which would make tags in any other namespace
    invisible.
    """
    res = get_with_context(
        array,
        "get_{0}_tags".format(_api_name(module)),
        CONTEXT_VERSION,
        module,
        namespaces=[module.params["namespace"]],
        **_resource_args(module)
    )
    if res.status_code != 200:
        check_response(
            res,
            module,
            "Failed to read tags for {0}".format(module.params["name"] or "the array"),
        )
    return list(res.items)


def _write_tags(module, array, pairs):
    """Write the given (key, value) pairs as tags"""
    fields = {"namespace": module.params["namespace"]}
    if module.params["copyable"] is not None:
        fields["copyable"] = module.params["copyable"]
    if module.params["resource_type"] == SINGLETON:
        method = "put_arrays_tags"
        tags = [Tag(key=key, value=value, **fields) for key, value in pairs]
    else:
        method = "put_{0}_tags_batch".format(_api_name(module))
        tags = [TagBatch(key=key, value=value, **fields) for key, value in pairs]
    res = put_with_context(
        array, method, CONTEXT_VERSION, module, tag=tags, **_resource_args(module)
    )
    check_response(
        res,
        module,
        "Failed to set tags on {0}".format(module.params["name"] or "the array"),
    )


def apply_tags(module, array, current):
    """Set the requested tags, writing only the ones that differ

    A put is accepted whether or not anything changes, so the difference has to
    be worked out here for the module to report honestly.
    """
    pairs = parse_kvp(module)
    if not pairs:
        module.fail_json(msg="kvp is required to set tags")
    held = {tag.key: tag for tag in current}
    wanted = []
    for key, value in pairs:
        tag = held.get(key)
        if tag is None or tag.value != value:
            wanted.append((key, value))
        elif _compares_copyable(module) and (
            getattr(tag, "copyable", None) != module.params["copyable"]
        ):
            wanted.append((key, value))
    if wanted and not module.check_mode:
        _write_tags(module, array, wanted)
    module.exit_json(changed=bool(wanted))


def remove_tags(module, array, current):
    """Remove the requested tags

    A delete of a key that is not there is accepted too, so again the work is
    in deciding what actually needs removing.
    """
    if module.params["keys"]:
        requested = list(module.params["keys"])
    else:
        requested = [key for key, _value in parse_kvp(module)]
    if not requested:
        module.fail_json(msg="keys or kvp is required to remove tags")
    held = {tag.key for tag in current}
    doomed = sorted(set(requested) & held)
    if doomed and not module.check_mode:
        res = delete_with_context(
            array,
            "delete_{0}_tags".format(_api_name(module)),
            CONTEXT_VERSION,
            module,
            keys=doomed,
            namespaces=[module.params["namespace"]],
            **_resource_args(module)
        )
        check_response(
            res,
            module,
            "Failed to remove tags from {0}".format(
                module.params["name"] or "the array"
            ),
        )
    module.exit_json(changed=bool(doomed))


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            resource_type=dict(type="str", required=True, choices=sorted(RESOURCES)),
            name=dict(type="str"),
            namespace=dict(type="str", default="default"),
            kvp=dict(type="list", elements="str"),
            keys=dict(type="list", elements="str", no_log=False),
            copyable=dict(type="bool"),
            context=dict(type="str", default=""),
        )
    )

    # Every type except the array is a named resource
    required_if = [
        ["resource_type", value, ["name"]] for value in RESOURCES if value != SINGLETON
    ]

    module = AnsibleModule(
        argument_spec, required_if=required_if, supports_check_mode=True
    )

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    resource_type = module.params["resource_type"]
    check_api_version(
        array,
        RESOURCES[resource_type][1],
        module,
        "Tagging a {0}".format(resource_type.replace("_", " ")),
    )

    current = read_tags(module, array)

    if module.params["state"] == "present":
        apply_tags(module, array, current)
    else:
        remove_tags(module, array, current)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
