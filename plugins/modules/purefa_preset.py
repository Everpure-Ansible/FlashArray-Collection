#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
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
module: purefa_preset
version_added: '1.46.0'
short_description: Manage Fusion fleet block workload presets
description:
- Create, replace, rename or delete Fusion fleet workload presets for block
  (FlashArray volume) workloads.
- A preset is the template that M(everpure.flasharray.purefa_workload) builds a
  workload from. It names a placement, the volumes to provision there, and
  optionally QoS limits, snapshot schedules, replication schedules, deploy-time
  parameters and tags.
- The preset is managed declaratively and as a whole. Every run compares the
  preset you describe with the preset on the fleet and, when they differ,
  replaces the fleet's copy with yours. See the notes for what that means for
  sections you leave out.
- Only block presets are supported. File presets (directories, exports, quotas),
  and the bucket and lifecycle sections of newer Purity releases, are not
  managed by this module, and it refuses to replace a preset that has them.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the preset.
    - Presets are fleet objects that the API names C(<fleet>:<preset>). Give the
      bare name. A leading C(<fleet>:) is accepted and removed.
    - Between 1 and 63 characters. Letters, numbers and C(-) only, beginning and
      ending with a letter or number, and not made up of digits alone.
    type: str
    required: true
  new_name:
    description:
    - New name for the preset, applied with a rename.
    - Only valid with I(state=present). The preset I(name) must exist, or
      already have been renamed to I(new_name) by an earlier run, and
      I(new_name) must not already be in use by another preset.
    - Any other change in the task is made first, under the old name, and the
      rename last. If the rename is then refused, the task fails and says that
      the content was replaced but the rename was not made.
    - Follows the same naming rules as I(name).
    type: str
  state:
    description:
    - Define whether the preset should exist or not.
    - C(present) creates the preset, or replaces it when it differs from the
      task.
    - C(absent) deletes the block preset. A preset that is not a block preset
      is refused. Workloads that were built from the preset
      keep working. They are not removed and the array does not stop the preset
      being deleted while they exist.
    type: str
    default: present
    choices: [ absent, present ]
  workload_type:
    description:
    - The kind of workload the preset configures.
    - Required when I(state=present).
    - The array accepts any text here without complaint, so the module checks
      it against the documented list.
    type: str
    choices:
    - Clarity
    - Epic
    - Exchange
    - File
    - MsSQL
    - MySQL
    - Oracle
    - PostgreSQL
    - SAP-Hana
    - SAP
    - VDI
    - VSI
    - Wfs
    - Zerto
    - Custom
  description:
    description:
    - A brief description of the workload the preset configures.
    - Up to 1024 characters.
    type: str
  placement:
    description:
    - Where the workload's volumes are deployed. A preset has exactly one
      placement and every volume uses it.
    - Required when I(state=present).
    type: dict
    suboptions:
      name:
        description:
        - Name of the placement configuration. It must be unique among all the
          configuration names in the preset, whatever their type.
        type: str
        default: default-placement
      storage_class:
        description:
        - The storage class the placement can be deployed to.
        - Give exactly one of I(name) or I(parameter). A parameter reference
          written as a template in I(name) is refused.
        - The array does not check that the storage class exists. A misspelt
          name is accepted when the preset is saved and fails only when a
          workload is created from it.
        type: dict
        required: true
        suboptions:
          name:
            description:
            - Name of the storage class, for example C(flasharray-x).
            type: str
          parameter:
            description:
            - Name of a I(parameters) entry of I(type=resource_reference) and
              I(resource_type=storage-classes), whose value is chosen when a
              workload is created.
            type: str
      qos:
        description:
        - Name of the entry in I(qos) to apply to the volumes in this placement.
          The limits are shared by all of the placement's volumes.
        type: str
      targets:
        description:
        - The fleet member the placement is deployed to.
        - At most one. When omitted the target is the fleet member that receives
          the workload request.
        - Give exactly one of I(name) or I(parameter) in each entry. A
          parameter reference written as a template in I(name) is refused.
        - Each entry must name a member that exists even when
          I(skip_verify_deployable) is true.
        - Requires REST API 2.54 or higher.
        type: list
        elements: dict
        suboptions:
          name:
            description:
            - Name of the fleet member.
            type: str
          parameter:
            description:
            - Name of a I(parameters) entry of I(type=resource_reference) and
              I(resource_type=remote-arrays), whose value is chosen when a
              workload is created.
            type: str
  volumes:
    description:
    - The volumes the preset provisions. Between 1 and 5 entries.
    - Required when I(state=present).
    - The total number of volumes, the sum of the I(count) values, can be at
      most 500.
    type: list
    elements: dict
    suboptions:
      name:
        description:
        - Name of the volume configuration. It must be unique among all the
          configuration names in the preset, whatever their type.
        type: str
        required: true
      count:
        description:
        - Number of volumes to provision.
        - A whole number, or a parameter reference. See the notes for how to
          write one.
        type: str
        default: '1'
      provisioned_size:
        description:
        - Virtual size of each volume in bytes. Must be a multiple of 512 and
          at most 4503599627370496 (4 PiB).
        - A whole number, or a parameter reference. See the notes for how to
          write one.
        type: str
        required: true
      placement:
        description:
        - Name of the placement configuration. Defaults to the one placement in
          I(placement), so it only needs setting to make the reference explicit.
        type: str
      snapshots:
        description:
        - Names of the entries in I(snapshots) to apply to these volumes, each
          at most once.
        type: list
        elements: str
      replications:
        description:
        - Names of the entries in I(replications) to apply to these volumes,
          each at most once.
        type: list
        elements: str
      naming_template:
        description:
        - Naming template for the volumes created from this configuration.
        - When omitted, a configuration that is already on the fleet keeps the
          template it has, and a new one gets the array's default. To change
          the template set it explicitly. To return to the default set it to
          the default pattern.
        - "The default pattern on Purity//FA 6.10.6 is
          {{functions.left(workload.name,
          25)}}-{{functions.left(workload.configuration.name,
          25)}}-{{functions.pad_left(workload.configuration.index, 4)}}."
        type: str
  qos:
    description:
    - QoS limit configurations. At most one entry.
    - Each must be used by I(placement.qos).
    type: list
    elements: dict
    suboptions:
      name:
        description:
        - Name of the QoS configuration. It must be unique among all the
          configuration names in the preset, whatever their type.
        type: str
        required: true
      iops_limit:
        description:
        - IOPS limit shared by all the volumes in the placement. Between 100 and
          100000000.
        - A whole number, or a parameter reference. See the notes for how to
          write one.
        type: str
      bandwidth_limit:
        description:
        - Bandwidth limit in bytes per second shared by all the volumes in the
          placement. From 1048576 (1 MiB/s) to 549755813888 (512 GiB/s).
        - A whole number, or a parameter reference. See the notes for how to
          write one.
        type: str
      naming_template:
        description:
        - Naming template for the QoS policy that is created.
        - When omitted, a configuration that is already on the fleet keeps the
          template it has, and a new one gets the array's default. To change
          the template set it explicitly. To return to the default set it to
          the default pattern.
        - "The default pattern on Purity//FA 6.10.6 is
          {{functions.left(workload.name,
          25)}}-{{functions.left(workload.configuration.name, 25)}}."
        type: str
  snapshots:
    description:
    - Snapshot schedule configurations. At most two entries.
    - Each must be used by at least one entry in I(volumes).
    type: list
    elements: dict
    suboptions:
      name:
        description:
        - Name of the snapshot configuration. It must be unique among all the
          configuration names in the preset, whatever their type.
        type: str
        required: true
      policy_action:
        description:
        - What a workload does about snapshot policies. With C(always_create)
          creating the workload fails if a policy of the same name exists. With
          C(create_or_reuse) an existing policy is reused.
        - The array defaults to C(create_or_reuse).
        type: str
        choices: [ always_create, create_or_reuse ]
        default: create_or_reuse
      rules:
        description:
        - The frequency and retention of the snapshots. One or two rules.
        - Intervals of all rules must be multiples of each other.
        - A rule has no time zone. The array refuses one on a FlashArray
          preset, so there is no option for it.
        type: list
        elements: dict
        required: true
        suboptions:
          every:
            description:
            - Interval between snapshots in milliseconds.
            - A whole number, or a parameter reference. See the notes for how to
              write one.
            type: str
            required: true
          keep_for:
            description:
            - How long snapshots are kept before being eradicated, in
              milliseconds. Must not be shorter than I(every).
            - A whole number, or a parameter reference. See the notes for how to
              write one.
            type: str
            required: true
          at:
            description:
            - Time of day at which to take the snapshot, in milliseconds since
              midnight.
            - Only valid when I(every) is a whole number of days, and only on
              the first rule.
            - A whole number, or a parameter reference. See the notes for how to
              write one.
            type: str
          suffix:
            description:
            - Snapshot suffix. Can be set on one rule only, the one with the
              largest I(keep_for).
            type: str
      naming_template:
        description:
        - Naming template for the snapshot policy that is created.
        - When omitted, a configuration that is already on the fleet keeps the
          template it has, and a new one gets the array's default. To change
          the template set it explicitly. To return to the default set it to
          the default pattern, which is the same as for I(qos).
        type: str
  replications:
    description:
    - Periodic replication (snapshot replication) configurations. At most two
      entries.
    - Each must be used by at least one entry in I(volumes).
    type: list
    elements: dict
    suboptions:
      name:
        description:
        - Name of the replication configuration. It must be unique among all the
          configuration names in the preset, whatever their type.
        type: str
        required: true
      target:
        description:
        - The remote array snapshots are replicated to. The array accepts
          any name here, including the array the volume is on, so check it.
        - Give exactly one of I(name) or I(parameter). A parameter reference
          written as a template in I(name) is refused.
        type: dict
        required: true
        suboptions:
          name:
            description:
            - Name of the remote array.
            type: str
          parameter:
            description:
            - Name of a I(parameters) entry of I(type=resource_reference) and
              I(resource_type=remote-arrays), whose value is chosen when a
              workload is created.
            type: str
      rules:
        description:
        - The frequency and retention of the replicated snapshots. One or two
          rules.
        - The same suboptions and rules as I(snapshots.rules).
        type: list
        elements: dict
        required: true
        suboptions:
          every:
            description:
            - Interval between snapshots in milliseconds.
            - A whole number, or a parameter reference. See the notes for how to
              write one.
            type: str
            required: true
          keep_for:
            description:
            - How long snapshots are kept before being eradicated, in
              milliseconds. Must not be shorter than I(every).
            - A whole number, or a parameter reference. See the notes for how to
              write one.
            type: str
            required: true
          at:
            description:
            - Time of day at which to take the snapshot, in milliseconds since
              midnight.
            - Only valid when I(every) is a whole number of days, and only on
              the first rule.
            - A whole number, or a parameter reference. See the notes for how to
              write one.
            type: str
          suffix:
            description:
            - Snapshot suffix. Can be set on one rule only, the one with the
              largest I(keep_for).
            type: str
      naming_template:
        description:
        - Naming template for the replication policy that is created.
        - When omitted, a configuration that is already on the fleet keeps the
          template it has, and a new one gets the array's default. To change
          the template set it explicitly. To return to the default set it to
          the default pattern, which is the same as for I(qos).
        type: str
  parameters:
    description:
    - Values the user is asked for when a workload is created from the preset.
      Fields that accept a parameter reference use them.
    - Every parameter must be used somewhere in the preset, and every reference
      must name a parameter defined here.
    type: list
    elements: dict
    suboptions:
      name:
        description:
        - Name of the parameter. Letters, numbers and C(_) only, unique among
          the parameters.
        type: str
        required: true
      type:
        description:
        - Type of value the parameter collects.
        type: str
        required: true
        choices: [ string, integer, boolean, resource_reference ]
      display_name:
        description:
        - Human-friendly name shown in the GUI. Up to 64 characters.
        type: str
      description:
        description:
        - Description of the parameter. Up to 1024 characters.
        type: str
      subtype:
        description:
        - Hint to the GUI about the kind of quantity the value is, which it
          uses to prompt for the value with suitable units. C(size) is for a
          number of bytes, such as I(volumes.provisioned_size), and prompts
          with size units. C(iops) and C(bandwidth) are for the two QoS
          limits, C(duration) for an interval in milliseconds such as
          I(every) and I(keep_for), and C(time) for a time of day in
          milliseconds since midnight, such as I(at).
        - Only valid for I(type=integer). The array refuses a subtype on any
          other type.
        - The choices are the five values Purity//FA 6.10.6 accepts. The
          array fails with an internal error for any other value, so a value
          outside the list is refused before any request is made.
        type: str
        choices: [ size, iops, bandwidth, time, duration ]
      default:
        description:
        - Value used when none is given.
        - For I(type=integer) a whole number. For I(type=boolean) C(true) or
          C(false). For I(type=resource_reference) the name of the resource,
          which must match I(resource_type).
        - Must be one of I(allowed_values) when those are set, and for an
          integer between I(minimum) and I(maximum).
        type: str
      allowed_values:
        description:
        - Values the user may choose from. At most 5.
        - Valid for I(type=string), up to 64 characters each, and
          I(type=integer).
        type: list
        elements: str
      minimum:
        description:
        - Smallest acceptable value, inclusive. Only valid for I(type=integer).
        type: int
      maximum:
        description:
        - Largest acceptable value, inclusive. Only valid for I(type=integer).
        type: int
      resource_type:
        description:
        - Kind of resource the parameter refers to.
        - Required for I(type=resource_reference) and not valid otherwise.
        - Use C(storage-classes) for I(placement.storage_class) and
          C(remote-arrays) for I(placement.targets) and
          I(replications.target).
        - The array fails with an internal error for any other value, so only
          these two are accepted.
        - The user may choose any resource of that kind. Purity//FA 6.10.6
          accepts exactly one allowed value for the parameter, naming only the
          resource type, and refuses a named resource in it, so there is no
          option to restrict the choice. A preset on the fleet whose parameter
          is restricted to named resources differs from the task and is
          replaced.
        type: str
        choices: [ storage-classes, remote-arrays ]
  tags:
    description:
    - Tags added to workloads built from the preset.
    - Keys must be unique within a namespace.
    type: list
    elements: dict
    suboptions:
      key:
        description:
        - Key of the tag. Up to 64 characters.
        type: str
        required: true
      value:
        description:
        - Value of the tag. Up to 256 characters, and not empty. The array fails
          with an internal error for a tag without a value.
        - May be a parameter reference. See the notes for how to write one.
        type: str
        required: true
      namespace:
        description:
        - Namespace of the tag. Namespaces that begin with C(pure) are reserved.
        type: str
        default: default
      copyable:
        description:
        - Whether the tag is copied when the volume it is on is copied.
        type: bool
        default: true
  skip_verify_deployable:
    description:
    - When true the array makes only the most basic syntax checks, instead of
      also asking each fleet member whether it could deploy a workload from the
      preset.
    - Useful for loading a preset that no member can deploy yet, so that it can
      be edited into shape.
    - This setting is an instruction for the request and is not stored in the
      preset. It is not part of the comparison made to decide whether the preset
      changed.
    type: bool
    default: false
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
notes:
- Requires Purity//FA REST API 2.51 or higher, 2.54 for I(placement.targets).
- Writing a preset needs a fleet-wide identity, that is a directory user, and an
  API token made for it. A token made for a local array user can read
  presets but every write fails with a 403 error, and the module says so.
- The preset is replaced as a whole. Anything you leave out of the task is empty
  after the run. That is how a section is removed, and it also means an edit made
  to the preset in the GUI that the task does not describe is lost the next
  time the task changes something. The one exception is a configuration's
  naming template, which is kept when the task leaves it out.
- The module decides whether anything changed by comparing the preset on the
  fleet, read back from the array, with the preset described by the task. The
  array spells numbers as text and fills in defaults, which are not counted as
  differences. A naming template the task leaves out is taken from the
  configuration of the same name and kind on the fleet, both for the
  comparison and for the request, so a replacement made for another reason does
  not reset it.
- Parameter references. Fields that accept one take a value such as
  C({{ parameters.volume_size }}), which the array fills in when a workload
  is created. Ansible would expand that text itself, so it has to be protected,
  either by writing the value with the C(!unsafe) tag in YAML or by wrapping it
  in C({% raw %}) and C({% endraw %}). See the examples.
- Most mistakes that the array would report one at a time, or not at all, are
  found before any request is made, and reported together. These are references to
  configurations that do not exist, configurations nothing uses, a name used by two
  configurations, parameters that are undefined or unused, and the limits.
  The array does not check I(placement.storage_class) or I(replications.target),
  so a wrong value is found only when a workload is created from the preset.
- The module cannot predict whether the array will accept the preset in check
  mode, only whether it would change. In particular it cannot tell whether
  I(placement.targets) or I(skip_verify_deployable) would be accepted.
- Supports C(check_mode) and C(--diff). The difference shown is between the
  preset on the fleet and the preset described by the task, both in the
  module's normalised form, not the exact request.
- Preset names are scoped to the fleet. The module always reads and writes
  through the fleet, wherever the connection is made.
seealso:
- module: everpure.flasharray.purefa_workload
- module: everpure.flasharray.purefa_info
"""

EXAMPLES = r"""
- name: Create a preset with one placement and one volume
  everpure.flasharray.purefa_preset:
    name: app-small
    workload_type: Custom
    description: One 1 GiB volume
    placement:
      storage_class:
        name: flasharray-x
    volumes:
      - name: data
        provisioned_size: '1073741824'
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create a preset with QoS, a snapshot schedule and a replication schedule
  everpure.flasharray.purefa_preset:
    name: app-protected
    workload_type: PostgreSQL
    placement:
      name: pg-placement
      qos: pg-qos
      storage_class:
        name: flasharray-x
    qos:
      - name: pg-qos
        iops_limit: '50000'
        bandwidth_limit: '1073741824'
    snapshots:
      - name: hourly
        rules:
          - every: '3600000'
            keep_for: '86400000'
    replications:
      - name: offsite
        target:
          name: arrayB
        rules:
          - every: '86400000'
            keep_for: '604800000'
            at: '7200000'
    volumes:
      - name: data
        count: '2'
        provisioned_size: '107374182400'
        snapshots: [hourly]
        replications: [offsite]
    tags:
      - key: app
        value: postgres
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create a preset that asks for the size, the storage class and a tag at deploy time
  everpure.flasharray.purefa_preset:
    name: app-flexible
    workload_type: Custom
    parameters:
      - name: vol_size
        type: integer
        subtype: size
        default: '1073741824'
        minimum: 1073741824
        maximum: 1099511627776
      - name: tier
        type: resource_reference
        resource_type: storage-classes
        default: flasharray-x
      - name: env
        type: string
        default: dev
        allowed_values: [dev, test, prod]
    placement:
      storage_class:
        parameter: tier
    volumes:
      - name: data
        # A parameter reference has to be protected from Ansible's own templating.
        provisioned_size: !unsafe '{{ parameters.vol_size }}'
    tags:
      - key: environment
        # The same protection written as a raw block.
        value: "{% raw %}{{ parameters.env }}{% endraw %}"
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Remove the snapshot schedule by leaving it out, because the whole preset is replaced
  everpure.flasharray.purefa_preset:
    name: app-protected
    workload_type: PostgreSQL
    placement:
      name: pg-placement
      qos: pg-qos
      storage_class:
        name: flasharray-x
    qos:
      - name: pg-qos
        iops_limit: '50000'
    volumes:
      - name: data
        provisioned_size: '107374182400'
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename a preset and show what would change
  everpure.flasharray.purefa_preset:
    name: app-small
    new_name: app-tiny
    workload_type: Custom
    placement:
      storage_class:
        name: flasharray-x
    volumes:
      - name: data
        provisioned_size: '1073741824'
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  check_mode: true
  diff: true

- name: Load a preset that no fleet member can deploy yet
  everpure.flasharray.purefa_preset:
    name: app-draft
    workload_type: Custom
    skip_verify_deployable: true
    placement:
      storage_class:
        name: flasharray-x
    volumes:
      - name: data
        provisioned_size: '1073741824'
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete a preset
  everpure.flasharray.purefa_preset:
    name: app-small
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
preset:
    description: Describes the preset after the task.
    type: dict
    returned: success
    contains:
        name:
            description: Name of the preset. This is the new name after a
                rename. It is the name that was asked for after a delete,
                or in check mode when the preset does not exist yet.
            type: str
            sample: 'app-small'
        revision:
            description: Revision counter the array keeps for the preset. It is
                null after a delete, and in check mode where the preset does
                not exist yet. The counter is increased by the array and
                is not a reliable sign of a change. Use I(changed).
            type: int
            sample: 3
        changed_sections:
            description: The top-level sections of the preset that the run
                changed, or in check mode would change. Empty when nothing
                changed. A create or delete lists every section that was set or
                unset.
            type: list
            elements: str
            sample: ['volume_configurations', 'workload_tags']
diff:
    description: The preset before and after, as text, in the module's normalised
        form. A naming template the task leaves out is shown on both sides as
        it is on the fleet. On a rename the old and new names are part
        of the text, so the change shows even when nothing else differs.
    type: dict
    returned: when running with C(--diff)
"""

import copy
import json
import re
from typing import NamedTuple

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        PresetWorkload,
        PresetWorkloadPatch,
        PresetWorkloadPost,
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
)

# 2.51 brought policy_action, naming_patterns, rule suffixes and
# skip_verify_deployable, all of which every request may carry
MIN_REQUIRED_API_VERSION = "2.51"
TARGETS_API_VERSION = "2.54"
MIN_SDK_VERSION = "1.88.0"

WORKLOAD_TYPES = [
    "Clarity",
    "Epic",
    "Exchange",
    "File",
    "MsSQL",
    "MySQL",
    "Oracle",
    "PostgreSQL",
    "SAP-Hana",
    "SAP",
    "VDI",
    "VSI",
    "Wfs",
    "Zerto",
    "Custom",
]
PARAMETER_TYPES = ["string", "integer", "boolean", "resource_reference"]
REFERENCE_TYPES = ["storage-classes", "remote-arrays"]
# The subtypes Purity//FA 6.10.6 accepts on an integer parameter. Any other
# value is a server error, and any subtype on another type is refused
SUBTYPES = ["size", "iops", "bandwidth", "time", "duration"]
POLICY_ACTIONS = ["always_create", "create_or_reuse"]

# Limits found by trying them on a fleet. The SDK documents 5 for QoS
# configurations, but the array accepts one.
MAX_VOLUMES = 5
MAX_TOTAL_VOLUME_COUNT = 500
MAX_QOS = 1
MAX_RULES = 2
# The SDK models hold at most two snapshot and two replication configurations
# and refuse a third before any request is made.
MAX_SNAPSHOT_CONFIGS = 2
MAX_REPLICATION_CONFIGS = 2
MAX_ALLOWED_VALUES = 5
MAX_PROVISIONED_SIZE = 4503599627370496
MIN_IOPS = 100
MAX_IOPS = 100000000
MIN_BANDWIDTH = 1048576
MAX_BANDWIDTH = 512 * 1024**3
DEFAULT_COUNT = "1"
MAX_DESCRIPTION = 1024
MAX_PARAMETER_DISPLAY_NAME = 64
MAX_STRING_VALUE = 64
MAX_TAG_KEY = 64
MAX_TAG_VALUE = 256
MS_PER_DAY = 86400000

# The array answers 400 for every mistake, "does not exist" included, so a
# missing preset is told from the others by the text.
NOT_FOUND_STATUSES = frozenset({400, 404})
NOT_FOUND_TEXT = "does not exist"

PRESET_NAME_RE = re.compile(r"[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
PARAMETER_NAME_RE = re.compile(r"[A-Za-z0-9_]+")
WHOLE_NUMBER_RE = re.compile(r"[0-9]+")
PARAMETER_USE_RE = re.compile(r"\{\{\s*parameters\.([A-Za-z0-9_]+)")
PARAMETER_NAME_FIELD_RE = re.compile(r"\{\{\s*parameters\.([A-Za-z0-9_]+)\.name\s*\}\}")
TEMPLATE_HINT = "a whole number or a parameter reference like '{{ parameters.name }}'"

# The preset sections this module owns. Anything else on a preset (file
# directories, exports, quotas, buckets, lifecycle) makes it not a block preset.
COMPARED_SECTIONS = (
    "description",
    "parameters",
    "periodic_replication_configurations",
    "placement_configurations",
    "qos_configurations",
    "snapshot_configurations",
    "volume_configurations",
    "workload_tags",
    "workload_type",
)
NON_BLOCK_SECTIONS = (
    "directory_configurations",
    "export_configurations",
    "quota_configurations",
    "bucket_configurations",
    "lifecycle_configurations",
)
# Sections that hold configurations referred to by name
CONFIG_SECTIONS = (
    "placement_configurations",
    "volume_configurations",
    "qos_configurations",
    "snapshot_configurations",
    "periodic_replication_configurations",
)
# Fields the API types as text but which hold numbers
TEXT_NUMBER_KEYS = frozenset(
    {
        "count",
        "provisioned_size",
        "bandwidth_limit",
        "iops_limit",
        "at",
        "every",
        "keep_for",
    }
)


# ---------------------------------------------------------------------------
# Validation. Everything here is a pure function of the task parameters, so it
# runs before any request is made.
# ---------------------------------------------------------------------------


def _uses(value):
    """Names of the parameters a text value refers to"""
    if not isinstance(value, str):
        return set()
    return set(PARAMETER_USE_RE.findall(value))


def _number(errors, where, value, low=None, high=None, multiple_of=None):
    """Check a text number, returning it as an int, or None when it is not known

    A parameter reference passes, because its value is only known when a workload
    is created, and so does a missing value.
    """
    if value is None:
        return None
    text = str(value).strip()
    if _uses(text):
        return None
    if not WHOLE_NUMBER_RE.fullmatch(text):
        errors.append("%s must be %s, not '%s'" % (where, TEMPLATE_HINT, value))
        return None
    number = int(text)
    if low is not None and number < low:
        errors.append("%s must be at least %d, not %d" % (where, low, number))
    if high is not None and number > high:
        errors.append("%s must be at most %d, not %d" % (where, high, number))
    if multiple_of and number % multiple_of:
        errors.append(
            "%s must be a multiple of %d, not %d" % (where, multiple_of, number)
        )
    return number


def _check_reference(errors, where, ref):
    """Exactly one of name and parameter, and the name is a name, not a template"""
    ref = ref or {}
    name = ref.get("name")
    if bool(name) == bool(ref.get("parameter")):
        errors.append("%s needs exactly one of name and parameter" % where)
    if name and "{{" in str(name):
        errors.append(
            "%s name '%s' is a parameter reference. Give the parameter's name "
            "with parameter instead of name" % (where, name)
        )


def _volume_count(volume):
    """The count of a volume configuration, one when the task gives none"""
    count = volume.get("count")
    return DEFAULT_COUNT if count is None else count


def _check_rules(errors, where, rules):
    if not rules:
        errors.append("%s needs at least one rule" % where)
        return
    if len(rules) > MAX_RULES:
        errors.append(
            "%s has %d rules, at most %d are allowed" % (where, len(rules), MAX_RULES)
        )
    intervals = []
    keeps = []
    suffixed = []
    suffixes = 0
    for index, rule in enumerate(rules):
        label = "%s rule %d" % (where, index + 1)
        every = _number(errors, label + " every", rule.get("every"), low=1)
        keep_for = _number(errors, label + " keep_for", rule.get("keep_for"), low=1)
        at = _number(errors, label + " at", rule.get("at"), low=0)
        if every is not None and keep_for is not None and keep_for < every:
            errors.append(
                "%s keep_for (%d) must not be shorter than every (%d)"
                % (label, keep_for, every)
            )
        if rule.get("at") is not None:
            if index:
                errors.append("%s at can only be set on the first rule" % label)
            if every is not None and every % MS_PER_DAY:
                errors.append(
                    "%s at can only be set when every is a whole number of days" % label
                )
            if at is not None and at >= MS_PER_DAY:
                errors.append(
                    "%s at must be less than %d (one day)" % (label, MS_PER_DAY)
                )
        if rule.get("suffix"):
            suffixes += 1
            suffixed.append(keep_for)
        intervals.append(every)
        keeps.append(keep_for)
    if suffixes > 1:
        errors.append("%s sets a suffix on more than one rule" % where)
    elif suffixes == 1 and None not in keeps and suffixed[0] < max(keeps):
        errors.append(
            "%s can only set a suffix on the rule with the largest keep_for" % where
        )
    known = [i for i in intervals if i]
    for first in known:
        for second in known:
            if first < second and second % first:
                errors.append(
                    "%s intervals %d and %d are not multiples of each other"
                    % (where, first, second)
                )


def _parse_bool(text):
    value = str(text).strip().lower()
    if value in ("true", "yes", "on", "1"):
        return True
    if value in ("false", "no", "off", "0"):
        return False
    return None


def _check_parameter(errors, where, param):
    """Check one parameter against the rules for its type"""
    ptype = param.get("type")
    for field, text in (
        ("display_name", param.get("display_name")),
        ("description", param.get("description")),
    ):
        limit = (
            MAX_PARAMETER_DISPLAY_NAME if field == "display_name" else MAX_DESCRIPTION
        )
        if text and len(text) > limit:
            errors.append("%s %s is longer than %d characters" % (where, field, limit))
    allowed = param.get("allowed_values")
    default = param.get("default")
    minimum = param.get("minimum")
    maximum = param.get("maximum")
    rtype = param.get("resource_type")
    # One constraint block, and it has to be the one for the type. The subtype
    # is a hint about the unit of a number, so only an integer takes one
    misplaced = {
        "string": ("minimum", "maximum", "resource_type", "subtype"),
        "integer": ("resource_type",),
        "boolean": ("allowed_values", "minimum", "maximum", "resource_type", "subtype"),
        "resource_reference": ("allowed_values", "minimum", "maximum", "subtype"),
    }.get(ptype, ())
    for field in misplaced:
        value = param.get(field)
        if value is not None and value != []:
            errors.append(
                "%s option %s is not valid for type %s" % (where, field, ptype)
            )
    if ptype == "resource_reference":
        if not rtype:
            errors.append("%s needs resource_type for type resource_reference" % where)
        return
    if allowed and len(allowed) > MAX_ALLOWED_VALUES:
        errors.append(
            "%s has %d allowed_values, at most %d are allowed"
            % (where, len(allowed), MAX_ALLOWED_VALUES)
        )
    if ptype == "string":
        for value in list(allowed or []) + ([default] if default else []):
            if len(value) > MAX_STRING_VALUE:
                errors.append(
                    "%s value '%s' is longer than %d characters"
                    % (where, value, MAX_STRING_VALUE)
                )
        if default and allowed and default not in allowed:
            errors.append(
                "%s default '%s' is not one of allowed_values" % (where, default)
            )
    elif ptype == "boolean":
        if default is not None and _parse_bool(default) is None:
            errors.append(
                "%s default must be true or false, not '%s'" % (where, default)
            )
    elif ptype == "integer":
        numbers = []
        for value in allowed or []:
            if not re.fullmatch(r"-?[0-9]+", str(value).strip()):
                errors.append(
                    "%s allowed value '%s' is not a whole number" % (where, value)
                )
            else:
                numbers.append(int(value))
        number = None
        if default is not None:
            if not re.fullmatch(r"-?[0-9]+", str(default).strip()):
                errors.append(
                    "%s default '%s' is not a whole number" % (where, default)
                )
            else:
                number = int(default)
        if minimum is not None and maximum is not None and minimum > maximum:
            errors.append(
                "%s minimum (%d) is greater than maximum (%d)"
                % (where, minimum, maximum)
            )
        if number is not None:
            if allowed and number not in numbers:
                errors.append(
                    "%s default %d is not one of allowed_values" % (where, number)
                )
            if minimum is not None and number < minimum:
                errors.append(
                    "%s default %d is below minimum %d" % (where, number, minimum)
                )
            if maximum is not None and number > maximum:
                errors.append(
                    "%s default %d is above maximum %d" % (where, number, maximum)
                )


def _walk_strings(node, skip=("name",)):
    """Every text value under node, apart from values held under skipped keys"""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            if key in skip:
                continue
            yield from _walk_strings(value, skip)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _walk_strings(value, skip)


def validate_preset(params):
    """Check the task as a preset, returning every problem found

    The array reports its own complaints one at a time, sometimes twice, and for a
    few inputs not at all or with a server error. Finding them first gives one
    complete message and keeps the array out of it.
    """
    errors = []
    placement = params.get("placement")
    volumes = params.get("volumes") or []
    qos = params.get("qos") or []
    snapshots = params.get("snapshots") or []
    replications = params.get("replications") or []
    parameters = params.get("parameters") or []
    tags = params.get("tags") or []

    if not params.get("workload_type"):
        errors.append("workload_type is required")
    elif params["workload_type"] not in WORKLOAD_TYPES:
        errors.append(
            "workload_type '%s' is not one of %s"
            % (params["workload_type"], ", ".join(WORKLOAD_TYPES))
        )
    if params.get("description") and len(params["description"]) > MAX_DESCRIPTION:
        errors.append("description is longer than %d characters" % MAX_DESCRIPTION)

    # A block preset is a placement and the volumes that go in it. Nothing else
    # in this module would make a preset the array accepts.
    if not placement:
        errors.append("a block preset needs a placement")
    if not volumes:
        errors.append("a block preset needs at least one entry in volumes")
    if len(volumes) > MAX_VOLUMES:
        errors.append(
            "volumes has %d entries, at most %d are allowed"
            % (len(volumes), MAX_VOLUMES)
        )
    if len(qos) > MAX_QOS:
        errors.append("qos has %d entries, at most %d is allowed" % (len(qos), MAX_QOS))
    if len(snapshots) > MAX_SNAPSHOT_CONFIGS:
        errors.append(
            "snapshots has %d entries, at most %d are allowed"
            % (len(snapshots), MAX_SNAPSHOT_CONFIGS)
        )
    if len(replications) > MAX_REPLICATION_CONFIGS:
        errors.append(
            "replications has %d entries, at most %d are allowed"
            % (len(replications), MAX_REPLICATION_CONFIGS)
        )

    # Configuration names are shared by every kind of configuration
    names = []
    placement_name = None
    if placement:
        placement_name = placement.get("name") or "default-placement"
        names.append(("placement", placement_name))
    for kind, items in (
        ("volume", volumes),
        ("qos", qos),
        ("snapshot", snapshots),
        ("replication", replications),
    ):
        for item in items:
            names.append((kind, item.get("name")))
    seen = {}
    for kind, name in names:
        if not name or not str(name).strip():
            errors.append("a %s configuration has an empty name" % kind)
            continue
        if name in seen:
            errors.append(
                "configuration name '%s' is used by a %s and a %s configuration, "
                "names must be unique across all kinds" % (name, seen[name], kind)
            )
        seen.setdefault(name, kind)

    # Parameters
    defined = {}
    for param in parameters:
        pname = param.get("name") or ""
        where = "parameter '%s'" % pname
        if not PARAMETER_NAME_RE.fullmatch(pname):
            errors.append(
                "%s: parameter names may only contain letters, numbers and _" % where
            )
        if pname in defined:
            errors.append("%s is defined more than once" % where)
        defined[pname] = param
        _check_parameter(errors, where, param)

    # Placement
    if placement:
        storage_class = placement.get("storage_class")
        if not storage_class:
            errors.append("placement needs a storage_class")
        else:
            _check_reference(errors, "placement storage_class", storage_class)
        targets = placement.get("targets") or []
        if len(targets) > 1:
            errors.append(
                "placement targets has %d entries, at most 1 is allowed" % len(targets)
            )
        for target in targets:
            _check_reference(errors, "placement target", target)
        qos_name = placement.get("qos")
        if qos_name and qos_name not in [q.get("name") for q in qos]:
            errors.append(
                "placement qos refers to '%s', which is not defined in qos" % qos_name
            )

    # Volumes
    total = 0
    countable = True
    snapshot_names = [s.get("name") for s in snapshots]
    replication_names = [r.get("name") for r in replications]
    used_snapshots = set()
    used_replications = set()
    for volume in volumes:
        where = "volume '%s'" % volume.get("name")
        count = _number(errors, where + " count", _volume_count(volume), low=1)
        if count is None:
            countable = False
        else:
            total += count
        _number(
            errors,
            where + " provisioned_size",
            volume.get("provisioned_size"),
            low=512,
            high=MAX_PROVISIONED_SIZE,
            multiple_of=512,
        )
        vplace = volume.get("placement")
        if vplace and vplace != placement_name:
            errors.append(
                "%s refers to placement '%s', which is not defined. The placement "
                "is '%s'" % (where, vplace, placement_name)
            )
        for kind, listed, defined_names, used in (
            ("snapshot", volume.get("snapshots") or [], snapshot_names, used_snapshots),
            (
                "replication",
                volume.get("replications") or [],
                replication_names,
                used_replications,
            ),
        ):
            for cname in listed:
                if cname not in defined_names:
                    errors.append(
                        "%s refers to %s configuration '%s', which is not defined "
                        "in %ss" % (where, kind, cname, kind)
                    )
                used.add(cname)
            for cname in sorted(set(listed)):
                if listed.count(cname) > 1:
                    errors.append(
                        "%s lists %s configuration '%s' more than once"
                        % (where, kind, cname)
                    )
    if countable and total > MAX_TOTAL_VOLUME_COUNT:
        errors.append(
            "the volume counts add up to %d, at most %d are allowed"
            % (total, MAX_TOTAL_VOLUME_COUNT)
        )

    # QoS
    for item in qos:
        where = "qos '%s'" % item.get("name")
        _number(
            errors, where + " iops_limit", item.get("iops_limit"), MIN_IOPS, MAX_IOPS
        )
        _number(
            errors,
            where + " bandwidth_limit",
            item.get("bandwidth_limit"),
            MIN_BANDWIDTH,
            MAX_BANDWIDTH,
        )
        if placement and item.get("name") != placement.get("qos"):
            errors.append(
                "qos '%s' is not used. Set placement qos to use it, or remove it"
                % item.get("name")
            )

    # Snapshot and replication schedules
    for item in snapshots:
        where = "snapshot '%s'" % item.get("name")
        _check_rules(errors, where, item.get("rules"))
        if item.get("name") not in used_snapshots:
            errors.append(
                "snapshot '%s' is not used. Add it to a volume's snapshots, or "
                "remove it" % item.get("name")
            )
    for item in replications:
        where = "replication '%s'" % item.get("name")
        _check_reference(errors, where + " target", item.get("target"))
        _check_rules(errors, where, item.get("rules"))
        if item.get("name") not in used_replications:
            errors.append(
                "replication '%s' is not used. Add it to a volume's "
                "replications, or remove it" % item.get("name")
            )

    # Tags
    seen_tags = set()
    for tag in tags:
        key = tag.get("key") or ""
        where = "tag '%s'" % key
        if not key:
            errors.append("a tag has an empty key")
        if len(key) > MAX_TAG_KEY:
            errors.append("%s key is longer than %d characters" % (where, MAX_TAG_KEY))
        value = tag.get("value")
        if value is None or str(value) == "":
            errors.append("%s needs a value" % where)
        elif len(str(value)) > MAX_TAG_VALUE:
            errors.append(
                "%s value is longer than %d characters" % (where, MAX_TAG_VALUE)
            )
        identity = (tag.get("namespace") or "default", key)
        if identity in seen_tags:
            errors.append(
                "tag key '%s' is set more than once in namespace '%s'"
                % (key, identity[0])
            )
        seen_tags.add(identity)

    # Parameter use. Every reference has to be to a defined parameter and every
    # parameter has to be referred to. Reference-type parameters are used through
    # the parameter option, which also fixes the kind of resource they must be.
    used = set()
    for section in (placement, volumes, qos, snapshots, replications, tags):
        for text in _walk_strings(section):
            used |= _uses(text)
    reference_uses = []
    if placement:
        reference_uses.append(
            (
                "placement storage_class",
                placement.get("storage_class"),
                "storage-classes",
            )
        )
        for target in placement.get("targets") or []:
            reference_uses.append(("placement target", target, "remote-arrays"))
    for item in replications:
        reference_uses.append(
            (
                "replication '%s' target" % item.get("name"),
                item.get("target"),
                "remote-arrays",
            )
        )
    for where, ref, rtype in reference_uses:
        pname = (ref or {}).get("parameter")
        if not pname:
            continue
        used.add(pname)
        param = defined.get(pname)
        if param is None:
            continue
        if param.get("type") != "resource_reference":
            errors.append(
                "%s uses parameter '%s', which is of type %s, not resource_reference"
                % (where, pname, param.get("type"))
            )
        elif param.get("resource_type") != rtype:
            errors.append(
                "%s needs a parameter with resource_type %s, but '%s' has %s"
                % (where, rtype, pname, param.get("resource_type"))
            )
    for pname in sorted(used - set(defined)):
        errors.append("parameter '%s' is used but not defined in parameters" % pname)
    for pname in defined:
        if pname and pname not in used:
            errors.append(
                "parameter '%s' is not used. Refer to it as {{ parameters.%s }} or "
                "remove it" % (pname, pname)
            )
    return errors


# ---------------------------------------------------------------------------
# Building the request body and normalising it for comparison
# ---------------------------------------------------------------------------


def _prune(value):
    """Drop None, empty text, empty lists and empty dicts, at any depth

    False and 0 are values and stay.
    """
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            item = _prune(item)
            if item is None or item == "" or item == [] or item == {}:
                continue
            out[key] = item
        return out
    if isinstance(value, (list, tuple)):
        return [_prune(item) for item in value]
    return value


def _naming(template):
    return [{"template": template}] if template else None


def _reference(spec, resource_type):
    """The API's reference for a name, or for a parameter the user fills in"""
    if spec.get("parameter"):
        pname = spec["parameter"]
        return {
            "id": "{{ parameters.%s.id }}" % pname,
            "name": "{{ parameters.%s.name }}" % pname,
            "resource_type": "{{ parameters.%s.resource_type }}" % pname,
        }
    return {"name": spec.get("name"), "resource_type": resource_type}


def _rules(rules):
    return [
        {
            "every": rule.get("every"),
            "keep_for": rule.get("keep_for"),
            "at": rule.get("at"),
            "suffix": rule.get("suffix"),
        }
        for rule in rules or []
    ]


def _constraints(param):
    """The constraint block for a parameter, which is the one for its type"""
    ptype = param.get("type")
    default = param.get("default")
    allowed = param.get("allowed_values")
    if ptype == "string":
        block = {"allowed_values": allowed, "default": default}
    elif ptype == "integer":
        block = {
            "allowed_values": [int(v) for v in allowed] if allowed else None,
            "default": int(default) if default is not None else None,
            "minimum": param.get("minimum"),
            "maximum": param.get("maximum"),
        }
    elif ptype == "boolean":
        block = {"default": _parse_bool(default) if default is not None else None}
    else:
        rtype = param.get("resource_type")
        block = {"allowed_values": [{"resource_type": rtype}]}
        if default:
            block["default"] = {"name": default, "resource_type": rtype}
        return {"resource_reference": block}
    block = _prune(block)
    return {ptype: block} if block else None


def build_body(params):
    """The API's description of the preset, built only from the task

    Sections the task leaves out are not sent, which the array reads as empty.
    The name, id, context and revision are never in the body. A name in a
    replacement body renames the preset.
    """
    placement = params["placement"]
    placement_name = placement.get("name") or "default-placement"
    placement_config = {
        "name": placement_name,
        "storage_class": _reference(placement["storage_class"], "storage-classes"),
        "qos_configurations": [placement["qos"]] if placement.get("qos") else None,
        "targets": [
            _reference(t, "remote-arrays") for t in placement.get("targets") or []
        ],
    }
    body = {
        "workload_type": params.get("workload_type"),
        "description": params.get("description"),
        "placement_configurations": [placement_config],
        "volume_configurations": [
            {
                "name": v["name"],
                "count": str(_volume_count(v)),
                "provisioned_size": str(v["provisioned_size"]),
                "placement_configurations": [v.get("placement") or placement_name],
                "snapshot_configurations": v.get("snapshots"),
                "periodic_replication_configurations": v.get("replications"),
                "naming_patterns": _naming(v.get("naming_template")),
            }
            for v in params.get("volumes") or []
        ],
        "qos_configurations": [
            {
                "name": q["name"],
                "iops_limit": q.get("iops_limit"),
                "bandwidth_limit": q.get("bandwidth_limit"),
                "naming_patterns": _naming(q.get("naming_template")),
            }
            for q in params.get("qos") or []
        ],
        "snapshot_configurations": [
            {
                "name": s["name"],
                "policy_action": s.get("policy_action"),
                "rules": _rules(s.get("rules")),
                "naming_patterns": _naming(s.get("naming_template")),
            }
            for s in params.get("snapshots") or []
        ],
        "periodic_replication_configurations": [
            {
                "name": r["name"],
                "remote_targets": [_reference(r["target"], "remote-arrays")],
                "rules": _rules(r.get("rules")),
                "naming_patterns": _naming(r.get("naming_template")),
            }
            for r in params.get("replications") or []
        ],
        "parameters": [
            {
                "name": p["name"],
                "type": p["type"],
                "constraints": _constraints(p),
                "metadata": {
                    "display_name": p.get("display_name"),
                    "description": p.get("description"),
                    "subtype": p.get("subtype"),
                },
            }
            for p in params.get("parameters") or []
        ],
        "workload_tags": [
            {
                "key": t["key"],
                "value": str(t["value"]),
                "namespace": t.get("namespace") or "default",
                "copyable": "true" if t.get("copyable", True) else "false",
            }
            for t in params.get("tags") or []
        ],
    }
    return _prune(_stringify_numbers(body))


def _canonical_reference(ref):
    """A reference as the name it holds, or the parameter that fills it in

    The array stores the three fields of a parameter reference separately, so
    they are read back as the same single parameter that was written.
    """
    name = (ref or {}).get("name") or ""
    match = PARAMETER_NAME_FIELD_RE.fullmatch(name)
    if match:
        return {"parameter": match.group(1)}
    return {"name": name} if name else {}


def _canonical_resource_reference(constraint):
    """A resource reference constraint as its allowed values and default name

    Every allowed value is kept, by resource type and name, so that a parameter
    the fleet restricts to named resources, which this module cannot write, is
    not taken for the unrestricted one it can. Ids are the array's own.
    """
    out = {}
    allowed = []
    for entry in constraint.get("allowed_values") or []:
        entry = _prune(
            {"name": entry.get("name"), "resource_type": entry.get("resource_type")}
        )
        if entry:
            allowed.append(entry)
    if allowed:
        out["allowed_values"] = sorted(
            allowed, key=lambda e: (e.get("resource_type", ""), e.get("name", ""))
        )
    default = constraint.get("default") or {}
    if default.get("name"):
        out["default"] = default["name"]
    return out


def _stringify_numbers(value, key=None):
    if isinstance(value, dict):
        return {k: _stringify_numbers(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_stringify_numbers(v, key) for v in value]
    if key in TEXT_NUMBER_KEYS:
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, str) and WHOLE_NUMBER_RE.fullmatch(value.strip()):
            # Padding and leading zeros are not part of the number
            return str(int(value.strip()))
        if isinstance(value, str):
            return value.strip()
    return value


def normalise_preset(preset):
    """The part of a preset that is compared, in one canonical form

    Both the preset read from the array and the one built from the task go through
    here, so differences in how they are spelled, which the array chooses, do not
    count as changes. Things that mean the same are written the same way. Empty and
    missing are alike, numbers held as text are text, the three fields of a parameter
    reference are one parameter, and lists in which order carries no meaning are
    sorted. The array's defaults for tags and snapshot policy are filled in.
    """
    work = {
        key: copy.deepcopy(preset.get(key))
        for key in COMPARED_SECTIONS
        if preset.get(key) is not None
    }
    for config in work.get("placement_configurations") or []:
        if config.get("storage_class") is not None:
            config["storage_class"] = _canonical_reference(config["storage_class"])
        if config.get("targets") is not None:
            config["targets"] = [_canonical_reference(t) for t in config["targets"]]
    for config in work.get("periodic_replication_configurations") or []:
        if config.get("remote_targets") is not None:
            config["remote_targets"] = [
                _canonical_reference(t) for t in config["remote_targets"]
            ]
    for param in work.get("parameters") or []:
        constraint = (param.get("constraints") or {}).get("resource_reference")
        if constraint:
            param["constraints"]["resource_reference"] = _canonical_resource_reference(
                constraint
            )
    out = _prune(_stringify_numbers(work))

    for tag in out.get("workload_tags", []):
        if isinstance(tag.get("copyable"), bool):
            tag["copyable"] = "true" if tag["copyable"] else "false"
        tag.setdefault("copyable", "true")
        tag.setdefault("namespace", "default")
    for config in out.get("snapshot_configurations", []):
        config.setdefault("policy_action", "create_or_reuse")
    for section in CONFIG_SECTIONS + ("parameters",):
        if section in out:
            out[section].sort(key=lambda item: item.get("name") or "")
    for config in out.get("volume_configurations", []):
        for field in (
            "placement_configurations",
            "snapshot_configurations",
            "periodic_replication_configurations",
        ):
            if field in config:
                config[field] = sorted(config[field])
    if "workload_tags" in out:
        out["workload_tags"].sort(key=lambda t: (t["namespace"], t["key"]))
    return out


def carry_over_naming(body, existing):
    """The body with the fleet's naming templates where the task chose none

    A replacement sends the whole preset, and a configuration sent without a
    naming template gets the array's default, so a task that never mentions
    templates would reset a custom one every time it changed anything else.
    Instead, a configuration of the same name and kind that is already on the
    fleet lends its template to the body. The template then takes part in the
    comparison like any other field. A configuration the fleet does not have is
    sent without one, and gets the array's default.
    """
    if not existing:
        return body
    body = copy.deepcopy(body)
    for section in CONFIG_SECTIONS:
        stored = {
            config.get("name"): config.get("naming_patterns")
            for config in existing.get(section) or []
        }
        for config in body.get(section) or []:
            if "naming_patterns" in config:
                continue
            templates = [
                {"template": pattern["template"]}
                for pattern in stored.get(config.get("name")) or []
                if isinstance(pattern, dict) and pattern.get("template")
            ]
            if templates:
                config["naming_patterns"] = templates
    return body


def changed_sections(before, after):
    return sorted(
        key for key in set(before) | set(after) if before.get(key) != after.get(key)
    )


def not_a_block_preset(preset):
    """Why a preset on the fleet is not a block preset, or None when it is"""
    features = preset.get("platform_features") or []
    if features and list(features) != ["fa_block"]:
        return "platform_features is %s" % ", ".join(features)
    for section in NON_BLOCK_SECTIONS:
        if preset.get(section):
            return "it has %s" % section
    return None


# ---------------------------------------------------------------------------
# Deciding what to do
# ---------------------------------------------------------------------------


class Decision(NamedTuple):
    """What a run does, as separate steps that can combine

    write is create or replace, or None for nothing to write. rename moves the
    preset to new_name, after the write, so that a refused write leaves the
    fleet as it was. target is the name the preset has by the end.
    """

    fail: str
    rename: bool
    write: str
    delete: bool
    target: str


def decide(state, name, new_name, found, found_new, differs):
    """Turn what exists and what the task says into the steps to take

    found is whether name exists on the fleet, found_new whether new_name does,
    and differs whether the preset that will be written to differs from the task.
    """
    if state == "absent":
        return Decision("", False, None, bool(found), name)
    if not new_name or new_name == name:
        if not found:
            return Decision("", False, "create", False, name)
        return Decision("", False, "replace" if differs else None, False, name)
    if found and found_new:
        return Decision(
            "Cannot rename preset %s to %s. Both already exist." % (name, new_name),
            False,
            None,
            False,
            name,
        )
    if found:
        return Decision("", True, "replace" if differs else None, False, new_name)
    if found_new:
        # An earlier run made the rename
        return Decision("", False, "replace" if differs else None, False, new_name)
    return Decision(
        "Cannot rename preset %s to %s. Neither exists." % (name, new_name),
        False,
        None,
        False,
        name,
    )


# ---------------------------------------------------------------------------
# Talking to the array
# ---------------------------------------------------------------------------


def _error_text(response):
    """Every distinct message in an error response, in order

    The array reports several mistakes in one response, some of them twice.
    """
    messages = []
    for error in getattr(response, "errors", None) or []:
        message = getattr(error, "message", None)
        if message and message not in messages:
            messages.append(str(message))
    return "; ".join(messages) or "Unknown error"


def _is_absent(response):
    if getattr(response, "status_code", None) not in NOT_FOUND_STATUSES:
        return False
    return NOT_FOUND_TEXT in _error_text(response).lower()


def _fail_response(module, response, operation, write=False, changed=False):
    """Fail with every message the array gave

    changed says whether an earlier step of the same run already altered the
    fleet, such as a replacement made before a rename that was then refused.
    """
    message = "%s failed. Error: %s" % (operation, _error_text(response))
    status = getattr(response, "status_code", None)
    if write and status == 403:
        message += (
            ". Writing a preset needs a fleet-wide (directory) identity. A "
            "token for a local array user can read presets but not change them"
        )
    module.fail_json(msg=message, status_code=status, changed=changed)


def _read_fleet_name(module, array):
    """The fleet the array belongs to, which every preset is named after"""
    res = array.get_fleets()
    if res.status_code != 200:
        _fail_response(module, res, "Reading the fleet")
    fleets = list(res.items)
    if not fleets:
        module.fail_json(
            msg="purefa_preset requires a Fusion fleet environment, but this "
            "array is not a member of a fleet."
        )
    return fleets[0].name


def _split_name(name):
    """A preset name as its fleet prefix, or None, and the bare name"""
    prefix, colon, bare = name.partition(":")
    if colon:
        return prefix, bare
    return None, name


def _check_name(module, option):
    """Fail when a name option breaks the naming rules

    This needs nothing from the array, so it runs before the array is reached.
    Whether a prefix is the fleet's name is checked in _clean_name, once the
    fleet is known.
    """
    name = module.params.get(option)
    if not name:
        return
    prefix, bare = _split_name(name)
    if prefix == "" or not PRESET_NAME_RE.fullmatch(bare) or bare.isdigit():
        module.fail_json(
            msg="Invalid preset %s '%s'. A name is 1 to 63 letters, numbers or -, "
            "beginning and ending with a letter or number, and not made up of "
            "digits alone." % (option, name)
        )


def _clean_name(module, fleet, option):
    """A preset name without the fleet prefix"""
    name = module.params.get(option)
    if not name:
        return name
    prefix, bare = _split_name(name)
    if prefix is not None and prefix != fleet:
        module.fail_json(
            msg="Invalid preset %s '%s'. The only prefix a preset name may carry "
            "is the name of the fleet, '%s:'." % (option, name, fleet)
        )
    return bare


def _as_dict(item):
    if isinstance(item, dict):
        return item
    return item.to_dict()


def _read_preset(module, array, fleet, name, changed=False):
    """The preset as a dict, or None when the fleet has none of that name"""
    res = array.get_presets_workload(names=[name], context_names=[fleet])
    if res.status_code == 200:
        items = list(res.items)
        return _as_dict(items[0]) if items else None
    if _is_absent(res):
        return None
    _fail_response(module, res, "Reading preset %s" % name, changed=changed)


def _model(module, model_class, body, operation):
    """The SDK's model of the body, or a clean failure when the SDK refuses it

    The models check the body before any request is made. The validator should
    have found everything they would, so this is the net under it. Nothing has
    been written when a model is built, so the failure is not a change.
    """
    try:
        return model_class(**body)
    except (TypeError, ValueError) as err:
        module.fail_json(
            msg="%s failed. The py-pure-client model rejected the preset: %s"
            % (operation, err),
            changed=False,
        )


def _create_preset(module, array, fleet, name, body):
    kwargs = {}
    if module.params["skip_verify_deployable"]:
        kwargs["skip_verify_deployable"] = True
    operation = "Creating preset %s" % name
    preset = _model(module, PresetWorkloadPost, body, operation)
    res = array.post_presets_workload(
        names=[name], preset=preset, context_names=[fleet], **kwargs
    )
    if res.status_code != 200:
        _fail_response(module, res, operation, write=True)


def _replace_preset(module, array, fleet, name, body):
    """Replace the preset under the name it has now

    This is the first write of a run, so a refusal leaves the fleet as it was.
    """
    kwargs = {}
    if module.params["skip_verify_deployable"]:
        kwargs["skip_verify_deployable"] = True
    operation = "Replacing preset %s" % name
    preset = _model(module, PresetWorkload, body, operation)
    res = array.put_presets_workload(
        names=[name], preset=preset, context_names=[fleet], **kwargs
    )
    if res.status_code != 200:
        _fail_response(module, res, operation, write=True)


def _rename_preset(module, array, fleet, name, new_name, replaced=False):
    """Rename the preset, the last write of a run

    replaced is whether the content was replaced first. A refused rename then
    fails as a change, saying what was done and what was not.
    """
    res = array.patch_presets_workload(
        names=[name],
        preset=PresetWorkloadPatch(name=new_name),
        context_names=[fleet],
    )
    if res.status_code != 200:
        operation = "Renaming preset %s to %s" % (name, new_name)
        if replaced:
            operation = (
                "The content of preset %s was replaced, but renaming it to %s"
                % (name, new_name)
            )
        _fail_response(module, res, operation, write=True, changed=replaced)


def _delete_preset(module, array, fleet, name):
    res = array.delete_presets_workload(names=[name], context_names=[fleet])
    if res.status_code != 200:
        _fail_response(module, res, "Deleting preset %s" % name, write=True)


def _check_rest_features(module, array):
    check_api_version(array, MIN_REQUIRED_API_VERSION, module, "Workload presets")
    placement = module.params.get("placement") or {}
    if placement.get("targets"):
        check_api_version(array, TARGETS_API_VERSION, module, "Placement targets")


def _text(preset):
    return json.dumps(preset, indent=2, sort_keys=True) + "\n"


def _diff_result(before, after, name, new_name, renamed=False):
    """The --diff output. A rename is shown by name, as nothing else need differ"""
    if renamed:
        before = dict(before, name=name)
        after = dict(after, name=new_name)
    return {
        "before": _text(before),
        "after": _text(after),
        "before_header": "preset %s" % name,
        "after_header": "preset %s" % new_name,
    }


def main():
    argument_spec = purefa_argument_spec()
    reference_spec = dict(
        type="dict",
        options=dict(name=dict(type="str"), parameter=dict(type="str")),
        mutually_exclusive=[["name", "parameter"]],
        required_one_of=[["name", "parameter"]],
    )
    rule_spec = dict(
        type="list",
        elements="dict",
        required=True,
        options=dict(
            every=dict(type="str", required=True),
            keep_for=dict(type="str", required=True),
            at=dict(type="str"),
            suffix=dict(type="str"),
        ),
    )
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            new_name=dict(type="str"),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            workload_type=dict(type="str", choices=WORKLOAD_TYPES),
            description=dict(type="str"),
            placement=dict(
                type="dict",
                options=dict(
                    name=dict(type="str", default="default-placement"),
                    storage_class=dict(
                        type="dict",
                        required=True,
                        options=dict(name=dict(type="str"), parameter=dict(type="str")),
                        mutually_exclusive=[["name", "parameter"]],
                        required_one_of=[["name", "parameter"]],
                    ),
                    qos=dict(type="str"),
                    targets=dict(
                        type="list",
                        elements="dict",
                        options=dict(name=dict(type="str"), parameter=dict(type="str")),
                        mutually_exclusive=[["name", "parameter"]],
                        required_one_of=[["name", "parameter"]],
                    ),
                ),
            ),
            volumes=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    count=dict(type="str", default="1"),
                    provisioned_size=dict(type="str", required=True),
                    placement=dict(type="str"),
                    snapshots=dict(type="list", elements="str"),
                    replications=dict(type="list", elements="str"),
                    naming_template=dict(type="str"),
                ),
            ),
            qos=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    iops_limit=dict(type="str"),
                    bandwidth_limit=dict(type="str"),
                    naming_template=dict(type="str"),
                ),
            ),
            snapshots=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    policy_action=dict(
                        type="str", default="create_or_reuse", choices=POLICY_ACTIONS
                    ),
                    rules=rule_spec,
                    naming_template=dict(type="str"),
                ),
            ),
            replications=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    target=dict(reference_spec, required=True),
                    rules=rule_spec,
                    naming_template=dict(type="str"),
                ),
            ),
            parameters=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    type=dict(type="str", required=True, choices=PARAMETER_TYPES),
                    display_name=dict(type="str"),
                    description=dict(type="str"),
                    subtype=dict(type="str", choices=SUBTYPES),
                    default=dict(type="str"),
                    allowed_values=dict(type="list", elements="str"),
                    minimum=dict(type="int"),
                    maximum=dict(type="int"),
                    resource_type=dict(type="str", choices=REFERENCE_TYPES),
                ),
            ),
            tags=dict(
                type="list",
                elements="dict",
                options=dict(
                    key=dict(type="str", required=True, no_log=False),
                    value=dict(type="str", required=True),
                    namespace=dict(type="str", default="default"),
                    copyable=dict(type="bool", default=True),
                ),
            ),
            skip_verify_deployable=dict(type="bool", default=False),
        )
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=True,
        required_if=[["state", "present", ["workload_type"]]],
    )

    if not HAS_PURESTORAGE:
        module.fail_json(
            msg="py-pure-client sdk %s or later is required for this module"
            % MIN_SDK_VERSION
        )

    state = module.params["state"]
    desired_body = None
    if state == "present":
        errors = validate_preset(module.params)
        if errors:
            module.fail_json(
                msg="The preset is not valid. %s"
                % "; ".join("(%d) %s" % (n + 1, e) for n, e in enumerate(errors))
            )
        desired_body = build_body(module.params)
    elif module.params["new_name"]:
        module.fail_json(msg="new_name can only be used with state present")
    _check_name(module, "name")
    _check_name(module, "new_name")

    array = get_array(module)
    _check_rest_features(module, array)
    fleet = _read_fleet_name(module, array)
    name = _clean_name(module, fleet, "name")
    new_name = _clean_name(module, fleet, "new_name")

    existing = _read_preset(module, array, fleet, name)
    existing_new = None
    if new_name and new_name != name:
        existing_new = _read_preset(module, array, fleet, new_name)

    # What the preset will be compared with: the one being renamed, or the one that
    # an earlier run already renamed
    base = existing if existing is not None else existing_new
    before = {}
    after = {}
    differs = False
    if state == "present":
        if base is not None:
            reason = not_a_block_preset(base)
            if reason:
                module.fail_json(
                    msg="Preset %s is not a block preset (%s). purefa_preset "
                    "manages block presets only, and will not replace it."
                    % (name if existing is not None else new_name, reason)
                )
        # A naming template the task leaves out is the one the fleet has, so
        # the body and the comparison carry it
        desired_body = carry_over_naming(desired_body, base)
        after = normalise_preset(desired_body)
        if base is not None:
            before = normalise_preset(base)
            differs = before != after
    elif existing is not None:
        reason = not_a_block_preset(existing)
        if reason:
            module.fail_json(
                msg="Preset %s is not a block preset (%s). purefa_preset "
                "manages block presets only, and will not delete it." % (name, reason)
            )
        before = normalise_preset(existing)

    decision = decide(
        state, name, new_name, existing is not None, existing_new is not None, differs
    )
    if decision.fail:
        module.fail_json(msg=decision.fail)

    changed = bool(decision.rename or decision.write or decision.delete)
    sections = changed_sections(before, after) if changed else []
    if decision.rename:
        sections.insert(0, "name")

    if not module.check_mode:
        if decision.write == "create":
            _create_preset(module, array, fleet, decision.target, desired_body)
        elif decision.write == "replace":
            # Under the name the preset has now. The rename comes last, so a
            # refused replacement changes nothing
            _replace_preset(
                module,
                array,
                fleet,
                name if decision.rename else decision.target,
                desired_body,
            )
        elif decision.delete:
            _delete_preset(module, array, fleet, decision.target)
        if decision.rename:
            _rename_preset(
                module,
                array,
                fleet,
                name,
                new_name,
                replaced=decision.write == "replace",
            )

    # The revision is read after a write because a response to a write is
    # shaped differently from a read
    revision = None
    if state == "present":
        if changed and not module.check_mode:
            current = _read_preset(module, array, fleet, decision.target, changed=True)
            revision = (current or {}).get("revision")
        elif base is not None:
            revision = base.get("revision")

    result = dict(
        changed=changed,
        preset=dict(
            name=decision.target,
            revision=revision,
            changed_sections=sections,
        ),
    )
    if module._diff:
        result["diff"] = _diff_result(
            before, after, name, decision.target, decision.rename
        )
    module.exit_json(**result)


if __name__ == "__main__":
    main()
