#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2019, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_offload
version_added: '1.0.0'
short_description: Create, modify and delete NFS, S3 or Azure offload targets
description:
- Create, modify and delete NFS, S3, Azure or GCP offload targets.
- You must have a correctly configured offload app installed and a correctly configured offload network for offload to work.
- Purity//FA 6.2.3 and higher support up to two offload targets per array, provided both are S3 or both are Azure targets.
  Earlier releases support a single offload target.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  state:
    description:
    - Define state of offload
    default: present
    choices: [ absent, present ]
    type: str
  name:
    description:
    - The name of the offload target
    required: true
    type: str
  protocol:
    description:
    - Define which protocol the offload engine uses
    - NFS is not a supported protocol from Purity//FA 6.6.0 and higher
    default: nfs
    choices: [ nfs, s3, azure, gcp ]
    type: str
  address:
    description:
    - The IP or FQDN address of the NFS server
    type: str
  share:
    description:
    - NFS export on the NFS server
    type: str
  options:
    description:
    - Additional mount options for the NFS share
    - Supported mount options include I(port), I(rsize),
      I(wsize), I(nfsvers), and I(tcp) or I(udp)
    required: false
    default: ""
    type: str
  access_key:
    description:
    - Access Key ID of the offload target
    type: str
  container:
    description:
    - Name of the blob container of the Azure target
    default: offload
    type: str
  bucket:
    description:
    - Name of the bucket for the S3 or GCP target
    type: str
  account:
    description:
    - Name of the Azure blob storage account
    type: str
  secret:
    description:
    - Secret Access Key for the offload target
    type: str
  initialize:
    description:
    - Define whether to initialize the offload bucket
    type: bool
    default: true
  placement:
    description:
    - AWS S3 placement strategy
    type: str
    choices: ['retention-based', 'aws-standard-class', 'aws-intelligent-tiering']
    default: retention-based
  profile:
    description:
    - The Offload target profile that will be selected for this target.
    - This option allows more granular configuration for the target on top
      of the protocol parameter
    type: str
    version_added: '1.21.0'
    choices: ['azure', 'gcp', 'nfs', 'nfs-flashblade', 's3-aws', 's3-flashblade', 's3-scality-ring', 's3-wasabi-pay-as-you-go', 's3-wasabi-rcs', 's3-other']
  uri:
    description:
    - The URI used to create a connection between the array and a non-AWS S3 offload target.
    - Storage placement strategies are not supported for non-AWS S3 offload targets.
    - Both the HTTP and HTTPS protocols are allowed.
    type: str
    version_added: '1.32.0'
  auth_region:
    description:
    - The region that will be used for initial authentication request.
    - This parameter is optional and should be used only when region autodetection fails.
    type: str
    version_added: '1.32.0'
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
- name: Create NFS offload target
  everpure.flasharray.purefa_offload:
    name: nfs-offload
    protocol: nfs
    address: 10.21.200.4
    share: "/offload_target"
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create S3 offload target
  everpure.flasharray.purefa_offload:
    name: s3-offload
    protocol: s3
    access_key: "3794fb12c6204e19195f"
    bucket: offload-bucket
    secret: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    placement: aws-standard-class
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create Azure offload target
  everpure.flasharray.purefa_offload:
    name: azure-offload
    protocol: azure
    secret: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    container: offload-container
    account: user1
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete offload target
  everpure.flasharray.purefa_offload:
    name: nfs-offload
    protocol: nfs
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""


HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        OffloadAzure,
        OffloadGoogleCloud,
        OffloadNfs,
        OffloadPost,
        OffloadS3,
    )
except ImportError:
    HAS_PURESTORAGE = False

import re

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
    check_response,
)

REGEX_TARGET_NAME = re.compile(r"^[a-zA-Z0-9\-]*$")
MULTIOFFLOAD_LIMIT = 1
# Purity//FA 6.2.3 (REST 2.11) and higher allow two cloud offload targets
# of the same type (two S3 buckets or two Azure containers) per array
MULTIOFFLOAD_LIMIT_SAME_TYPE = 2
MULTIOFFLOAD_API_VERSION = "2.11"
PROFILE_API_VERSION = "2.25"
NO_SNAP2NFS_VERSION = "2.27"
CONTEXT_VERSION = "2.38"


def get_target(module, array):
    """Return target or None"""
    res = get_with_context(
        array, "get_offloads", CONTEXT_VERSION, module, names=[module.params["name"]]
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def create_offload(module, array):
    """Create offload target"""
    changed = True
    if not module.check_mode:
        api_version = array.get_rest_version()
        profile_supported = LooseVersion(PROFILE_API_VERSION) <= LooseVersion(
            api_version
        )
        if module.params["protocol"] == "gcp":
            if profile_supported and module.params["profile"]:
                bucket = OffloadGoogleCloud(
                    access_key_id=module.params["access_key"],
                    bucket=module.params["bucket"],
                    secret_access_key=module.params["secret"],
                    profile=module.params["profile"],
                )
            else:
                bucket = OffloadGoogleCloud(
                    access_key_id=module.params["access_key"],
                    bucket=module.params["bucket"],
                    secret_access_key=module.params["secret"],
                )
            offload = OffloadPost(google_cloud=bucket)
        if module.params["protocol"] == "azure":
            if profile_supported and module.params["profile"]:
                bucket = OffloadAzure(
                    container_name=module.params["container"],
                    secret_access_key=module.params["secret"],
                    account_name=module.params["account"],
                    profile=module.params["profile"],
                )
            else:
                bucket = OffloadAzure(
                    container_name=module.params["container"],
                    secret_access_key=module.params["secret"],
                    account_name=module.params["account"],
                )
            offload = OffloadPost(azure=bucket)
        if module.params["protocol"] == "s3":
            if profile_supported and module.params["profile"]:
                if module.params["auth_region"]:
                    bucket = OffloadS3(
                        access_key_id=module.params["access_key"],
                        bucket=module.params["bucket"],
                        secret_access_key=module.params["secret"],
                        profile=module.params["profile"],
                        uri=module.params["uri"],
                        auth_region=module.params["auth_region"],
                    )
                else:
                    bucket = OffloadS3(
                        access_key_id=module.params["access_key"],
                        bucket=module.params["bucket"],
                        secret_access_key=module.params["secret"],
                        profile=module.params["profile"],
                        uri=module.params["uri"],
                    )
            else:
                bucket = OffloadS3(
                    access_key_id=module.params["access_key"],
                    bucket=module.params["bucket"],
                    secret_access_key=module.params["secret"],
                    uri=module.params["uri"],
                )
            offload = OffloadPost(s3=bucket)
        if module.params["protocol"] == "nfs":
            if profile_supported and module.params["profile"]:
                bucket = OffloadNfs(
                    mount_point=module.params["share"],
                    address=module.params["address"],
                    mount_options=module.params["options"],
                    profile=module.params["profile"],
                )
            else:
                bucket = OffloadNfs(
                    mount_point=module.params["share"],
                    address=module.params["address"],
                    mount_options=module.params["options"],
                )
            offload = OffloadPost(nfs=bucket)
        res = get_with_context(
            array,
            "post_offloads",
            CONTEXT_VERSION,
            module,
            offload=offload,
            initialize=module.params["initialize"],
            names=[module.params["name"]],
        )
        check_response(
            res,
            module,
            f"Failed to create {module.params['protocol'].upper()} offload "
            f"{module.params['name']}. Please perform diagnostic checks",
        )
    module.exit_json(changed=changed)


def update_offload(module, array):
    """Update offload target"""
    changed = False
    module.exit_json(changed=changed)


def delete_offload(module, array):
    """Delete offload target"""
    changed = True
    if not module.check_mode:
        res = get_with_context(
            array,
            "delete_offloads",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
        )
        check_response(res, module, f"Failed to delete offload {module.params['name']}")
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="present", choices=["present", "absent"]),
            protocol=dict(
                type="str", default="nfs", choices=["nfs", "s3", "azure", "gcp"]
            ),
            placement=dict(
                type="str",
                default="retention-based",
                choices=[
                    "retention-based",
                    "aws-standard-class",
                    "aws-intelligent-tiering",
                ],
            ),
            profile=dict(
                type="str",
                choices=[
                    "azure",
                    "gcp",
                    "nfs",
                    "nfs-flashblade",
                    "s3-aws",
                    "s3-flashblade",
                    "s3-scality-ring",
                    "s3-wasabi-pay-as-you-go",
                    "s3-wasabi-rcs",
                    "s3-other",
                ],
            ),
            name=dict(type="str", required=True),
            initialize=dict(default=True, type="bool"),
            access_key=dict(type="str", no_log=False),
            secret=dict(type="str", no_log=True),
            bucket=dict(type="str"),
            container=dict(type="str", default="offload"),
            account=dict(type="str"),
            share=dict(type="str"),
            address=dict(type="str"),
            options=dict(type="str", default=""),
            uri=dict(type="str"),
            auth_region=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    # Validate required parameters based on state and protocol
    if module.params["state"] == "present":
        protocol = module.params["protocol"]
        if protocol == "nfs" and not (
            module.params["address"] and module.params["share"]
        ):
            module.fail_json(
                msg="address and share are required when protocol=nfs and state=present"
            )
        elif protocol == "s3" and not (
            module.params["access_key"]
            and module.params["secret"]
            and module.params["bucket"]
        ):
            module.fail_json(
                msg="access_key, secret, and bucket are required when protocol=s3 and state=present"
            )
        elif protocol == "gcp" and not (
            module.params["access_key"]
            and module.params["secret"]
            and module.params["bucket"]
        ):
            module.fail_json(
                msg="access_key, secret, and bucket are required when protocol=gcp and state=present"
            )
        elif protocol == "azure" and not (
            module.params["account"] and module.params["secret"]
        ):
            module.fail_json(
                msg="account and secret are required when protocol=azure and state=present"
            )

    array = get_array(module)
    api_version = array.get_rest_version()

    if (
        LooseVersion(NO_SNAP2NFS_VERSION) <= LooseVersion(api_version)
        and module.params["protocol"] == "nfs"
    ):
        module.fail_json(
            msg="NFS offload target is not supported from Purity//FA 6.6.0 and higher"
        )
    if (
        (
            module.params["protocol"].lower() == "azure"
            and module.params["profile"] != "azure"
        )
        or (
            module.params["protocol"].lower() == "gcp"
            and module.params["profile"] != "gcp"
        )
        or (
            module.params["protocol"].lower() == "nfs"
            and module.params["profile"] not in ["nfs", "nfs-flashblade"]
        )
        or (
            module.params["protocol"].lower() == "s3"
            and module.params["profile"]
            not in [
                "s3-aws",
                "s3-flashblade",
                "s3-scality-ring",
                "s3-wasabi-pay-as-you-go",
                "s3-wasabi-rcs",
                "s3-other",
            ]
        )
    ):
        module.warn("Specified profile not valid, ignoring...")
        module.params["profile"] = None

    if (
        not re.match(r"^[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9]$", module.params["name"])
        or len(module.params["name"]) > 56
    ):
        module.fail_json(
            msg="Target name invalid. "
            "Target name must be between 1 and 56 characters (alphanumeric and -) in length "
            "and begin and end with a letter or number. The name must include at least one letter."
        )
    if module.params["protocol"] in ["s3", "gcp"]:
        if (
            not re.match(r"^[a-z0-9][a-z0-9.\-]*[a-z0-9]$", module.params["bucket"])
            or len(module.params["bucket"]) > 63
        ):
            module.fail_json(
                msg="Bucket name invalid. "
                "Bucket name must be between 3 and 63 characters "
                "(lowercase, alphanumeric, dash or period) in length "
                "and begin and end with a letter or number."
            )

    target = get_target(module, array)
    if module.params["state"] == "present" and not target:
        offloads = list(array.get_offloads().items)
        offload_limit = MULTIOFFLOAD_LIMIT
        if LooseVersion(MULTIOFFLOAD_API_VERSION) <= LooseVersion(
            api_version
        ) and module.params["protocol"] in ["s3", "azure"]:
            offload_limit = MULTIOFFLOAD_LIMIT_SAME_TYPE
        if len(offloads) >= offload_limit:
            module.fail_json(
                msg="Cannot add offload target {0}. "
                "Offload Target Limit of {1} would be exceeded.".format(
                    module.params["name"], offload_limit
                )
            )
        if offloads and offloads[0].protocol != module.params["protocol"]:
            module.fail_json(msg="Currently all offloads must be of the same type.")
        create_offload(module, array)
    elif module.params["state"] == "present" and target:
        update_offload(module, array)
    elif module.params["state"] == "absent" and target:
        delete_offload(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
