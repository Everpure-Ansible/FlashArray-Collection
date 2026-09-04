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
module: purefa_volume_tags
version_added: '1.0.0'
short_description:  Manage volume tags on Everpure FlashArrays
description:
- Manage volume tags for volumes on Everpure FlashArray.
- Requires a minimum of Purity 6.0.0
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the volume.
    type: str
    required: true
  namespace:
    description:
    - The name of tag namespace
    default: default
    type: str
  copyable:
    description:
    - Define whether the volume tags are inherited on volume copies.
    default: true
    type: bool
  kvp:
    description:
    - List of key value pairs to assign to the volume.
    - Separate the key from the value using a colon (:) only.
    - All items in list will use I(namespace) and I(copyable) settings.
    - See examples for exact formatting requirements
    - With I(state=absent) and no I(tag), the keys of these pairs are the tags
      removed and their values are ignored.
    type: list
    elements: str
  tag:
    description:
    - List of tag keys to remove from the volume, for use with I(state=absent).
    - Takes precedence over the keys in I(kvp).
    type: list
    elements: str
    aliases: [ keys ]
    version_added: "1.38.0"
  state:
    description:
    - Define whether the volume tag(s) should exist or not.
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
    version_added: '1.38.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create new tags in namespace test for volume foo
  everpure.flasharray.purefa_volume_tags:
    name: foo
    namespace: test
    copyable: false
    kvp:
    - 'key1:value1'
    - 'key2:value2'
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Remove existing tags, by key, in namespace test for volume foo
  everpure.flasharray.purefa_volume_tags:
    name: foo
    namespace: test
    tag:
    - key1
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Update an existing tag in namespace test for volume foo
  everpure.flasharray.purefa_volume_tags:
    name: foo
    namespace: test
    kvp:
    - 'key1:value2'
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present
"""

RETURN = r"""
"""

try:
    from pypureclient.flasharray import TagBatch
except ImportError:
    HAS_PYPURECLIENT = False


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    delete_with_context,
    get_with_context,
    check_response,
)

CONTEXT_API_VERSION = "2.38"


def get_volume(module, array):
    """Return Volume or None"""
    res = get_with_context(
        array, "get_volumes", CONTEXT_API_VERSION, module, names=[module.params["name"]]
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_endpoint(module, array):
    """Return Endpoint or None"""
    res = get_with_context(
        array, "get_volumes", CONTEXT_API_VERSION, module, names=[module.params["name"]]
    )
    if res.status_code == 200 and getattr(
        list(res.items)[0].protocol_endpoint, "container_version", None
    ):
        return list(res.items)[0]
    return None


def create_tag(module, array):
    """Create Volume Tag"""
    changed = True
    if not module.check_mode:
        pairs = []
        for tag in module.params["kvp"]:
            pairs.append(
                (
                    tag.split(":")[0],
                    tag.split(":")[1],
                )
            )
        tags = [
            TagBatch(
                copyable=module.params["copyable"],
                namespace=module.params["namespace"],
                key=key,
                value=value,
            )
            for key, value in pairs
        ]
        res = get_with_context(
            array,
            "put_volumes_tags_batch",
            CONTEXT_API_VERSION,
            module,
            tag=tags,
            resource_names=[module.params["name"]],
        )
        check_response(
            res, module, f"Failed to add tag KVPs to volume {module.params['name']}"
        )

    module.exit_json(changed=changed)


def update_tags(module, array, current_tags):
    """Update tags"""
    changed = False
    current_pairs = []
    new_pairs = []
    for tag in current_tags:
        current_pairs.append((tag.key, tag.value))
    for new_tag in module.params["kvp"]:
        new_pairs.append(
            (
                new_tag.split(":")[0],
                new_tag.split(":")[1],
            )
        )
    add_pairs = list(set(new_pairs) - set(current_pairs))
    if add_pairs:
        changed = True
        if not module.check_mode:
            tags = [
                TagBatch(
                    copyable=module.params["copyable"],
                    namespace=module.params["namespace"],
                    key=key,
                    value=value,
                )
                for key, value in add_pairs
            ]
            res = get_with_context(
                array,
                "put_volumes_tags_batch",
                CONTEXT_API_VERSION,
                module,
                tag=tags,
                resource_names=[module.params["name"]],
            )
            check_response(
                res, module, f"Failed to add tag KVPs to volume {module.params['name']}"
            )
    module.exit_json(changed=changed)


def delete_tags(module, array, current_tags):
    """Delete Tags

    Removal works on keys. I(tag) names them directly; failing that the keys of
    I(kvp) are used and their values ignored, so the same list that created the
    tags can remove them.
    """
    if module.params["tag"]:
        requested = list(module.params["tag"])
    else:
        requested = [pair.split(":")[0] for pair in module.params["kvp"] or []]
    if not requested:
        module.fail_json(msg="tag or kvp is required to remove volume tags")
    held = {tag.key for tag in current_tags}
    doomed = sorted(set(requested) & held)
    changed = bool(doomed)
    if doomed and not module.check_mode:
        res = delete_with_context(
            array,
            "delete_volumes_tags",
            CONTEXT_API_VERSION,
            module,
            resource_names=[module.params["name"]],
            keys=doomed,
            namespaces=[module.params["namespace"]],
        )
        check_response(
            res,
            module,
            f"Failed to remove tags from volume {module.params['name']}",
        )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            copyable=dict(type="bool", default=True),
            namespace=dict(type="str", default="default"),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            kvp=dict(type="list", elements="str"),
            tag=dict(type="list", elements="str", aliases=["keys"]),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    state = module.params["state"]
    array = get_array(module)

    volume = get_volume(module, array)
    endpoint = get_endpoint(module, array)

    if not volume:
        module.fail_json(msg="Volume {0} does not exist.".format(module.params["name"]))
    if endpoint:
        module.fail_json(
            msg="Volume {0} is an endpoint. Tags not allowed.".format(
                module.params["name"]
            )
        )
    res = get_with_context(
        array,
        "get_volumes_tags",
        CONTEXT_API_VERSION,
        module,
        namespaces=[module.params["namespace"]],
        resource_names=[module.params["name"]],
    )
    current_tags = list(res.items)

    if state == "present" and not current_tags:
        create_tag(module, array)
    elif state == "present" and current_tags:
        update_tags(module, array, current_tags)
    elif state == "absent" and current_tags:
        delete_tags(module, array, current_tags)
    elif state == "absent":
        module.exit_json(changed=False)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
