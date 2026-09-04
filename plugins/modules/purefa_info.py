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
module: purefa_info
version_added: '1.0.0'
short_description: Collect information from Everpure FlashArray
description:
  - Collect information from a Everpure Flasharray running the
    Purity//FA operating system. By default, the module will collect basic
    information including hosts, host groups, protection
    groups and volume counts. Additional information can be collected
    based on the configured set of arguments.
author:
  - Everpure ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  gather_subset:
    description:
      - When supplied, this argument will define the information to be collected.
        Possible values for this include all, minimum, config, performance,
        capacity, network, subnet, interfaces, hgroups, pgroups, hosts,
        admins, volumes, snapshots, pods, replication, vgroups, offload, apps,
        arrays, certs, kmip, clients, policies, dir_snaps, filesystems,
        alerts, virtual_machines, subscriptions, realms, fleet, presets,
        workloads and tgroups.
    type: list
    elements: str
    required: false
    default: minimum
extends_documentation_fragment:
  - everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: collect default set of information
  everpure.flasharray.purefa_info:
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: array_info
- name: show default information
  debug:
    msg: "{{ array_info['purefa_info']['default'] }}"

- name: collect configuration and capacity information
  everpure.flasharray.purefa_info:
    gather_subset:
      - config
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: array_info
- name: show configuration information
  debug:
    msg: "{{ array_info['purefa_info']['config'] }}"

- name: collect all information
  everpure.flasharray.purefa_info:
    gather_subset:
      - all
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
- name: show all information
  debug:
    msg: "{{ array_info['purefa_info'] }}"
"""

RETURN = r"""
purefa_info:
  description: Returns the information collected from the FlashArray
  returned: always
  type: dict
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)

from datetime import datetime
import time

SEC_TO_DAY = 86400000
ENCRYPTION_STATUS_API_VERSION = "2.6"
DIR_QUOTA_API_VERSION = "2.7"
SHARED_CAP_API_VERSION = "2.9"
PURE_OUI = "naa.624a9370"
SAFE_MODE_VERSION = "2.10"
PER_PG_VERSION = "2.13"
SAML2_VERSION = "2.11"
NFS_USER_MAP_VERSION = "2.15"
DEFAULT_PROT_API_VERSION = "2.16"
VM_VERSION = "2.14"
VLAN_VERSION = "2.17"
NEIGHBOR_API_VERSION = "2.22"
POD_QUOTA_VERSION = "2.23"
AUTODIR_API_VERSION = "2.24"
SUBS_API_VERSION = "2.26"
NSID_API_VERSION = "2.27"
NFS_SECURITY_VERSION = "2.29"
UPTIME_API_VERSION = "2.30"
TLS_CONNECTION_API_VERSION = "2.33"
PWD_POLICY_API_VERSION = "2.34"
RA_API_VERSION = "2.35"
DSROLE_POLICY_API_VERSION = "2.36"
CONTEXT_API_VERSION = "2.38"
QUOTA_API_VERSION = "2.42"
TAGS_API_VERSION = "2.39"
TGROUP_API_VERSION = "2.54"


def _is_cbs(array):
    """Is the selected array a Cloud Block Store"""
    model = list(array.get_hardware(filter="type='controller'").items)[0].model
    is_cbs = bool("CBS" in model)
    return is_cbs


def generate_default_dict(array):
    default_info = {}
    api_version = array.get_rest_version()
    default_info["api_versions"] = api_version
    if LooseVersion(VM_VERSION) <= LooseVersion(api_version):
        default_info["virtual_machines"] = len(
            getattr(array.get_virtual_machines(vm_type="vvol"), "items", [])
        )
        default_info["virtual_machine_snaps"] = len(
            getattr(array.get_virtual_machine_snapshots(vm_type="vvol"), "items", [])
        )
    default_info["snapshot_policies"] = len(
        getattr(array.get_policies_snapshot(), "items", []) or []
    )
    default_info["nfs_policies"] = len(
        getattr(array.get_policies_nfs(), "items", []) or []
    )
    default_info["smb_policies"] = len(
        getattr(array.get_policies_smb(), "items", []) or []
    )
    default_info["filesystems"] = len(
        getattr(array.get_file_systems(), "items", []) or []
    )
    default_info["directories"] = len(
        getattr(array.get_directories(), "items", []) or []
    )
    default_info["exports"] = len(
        getattr(array.get_directory_exports(), "items", []) or []
    )
    default_info["directory_snapshots"] = len(
        getattr(array.get_directory_snapshots(), "items", []) or []
    )
    if LooseVersion(DIR_QUOTA_API_VERSION) <= LooseVersion(api_version):
        default_info["quota_policies"] = len(
            getattr(array.get_policies_quota(), "items", []) or []
        )
    if LooseVersion(PWD_POLICY_API_VERSION) <= LooseVersion(api_version):
        default_info["password_policies"] = len(
            getattr(array.get_policies_password(), "items", []) or []
        )
    if LooseVersion(ENCRYPTION_STATUS_API_VERSION) <= LooseVersion(api_version):
        array_data = list(array.get_arrays().items)[0]
        encryption = array_data.encryption
        default_info["encryption_enabled"] = encryption.data_at_rest.enabled
        if default_info["encryption_enabled"]:
            default_info["encryption_algorithm"] = encryption.data_at_rest.algorithm
            default_info["encryption_module_version"] = encryption.module_version
        eradication = array_data.eradication_config
        if LooseVersion(SUBS_API_VERSION) <= LooseVersion(api_version):
            default_info["service_mode"] = list(array.get_subscriptions().items)[
                0
            ].service
            default_info["eradication_disabled_days_timer"] = int(
                eradication.disabled_delay / SEC_TO_DAY
            )
            default_info["eradication_enabled_days_timer"] = int(
                eradication.enabled_delay / SEC_TO_DAY
            )
        eradication_delay = getattr(eradication, "eradication_delay", None)
        if eradication_delay is not None:
            default_info["eradication_days_timer"] = int(eradication_delay / SEC_TO_DAY)
        if LooseVersion(SAFE_MODE_VERSION) <= LooseVersion(api_version):
            if eradication.manual_eradication == "all-enabled":
                default_info["safe_mode"] = "Disabled"
            else:
                default_info["safe_mode"] = "Enabled"
        if LooseVersion(UPTIME_API_VERSION) <= LooseVersion(api_version):
            default_info["controller_uptime"] = []
            controllers = list(
                array.get_controllers(filter="type='array_controller'").items
            )
            timenow = datetime.fromtimestamp(time.time())
            for controller in controllers:
                mode_since = getattr(controller, "mode_since", None)
                if mode_since is not None:
                    boottime = datetime.fromtimestamp(mode_since / 1000)
                    delta = timenow - boottime
                    uptime = str(delta)
                else:
                    uptime = "unknown"
                default_info["controller_uptime"].append(
                    {
                        "controller": controller.name,
                        "uptime": uptime,
                    }
                )
    default_info["volume_groups"] = len(list(array.get_volume_groups().items))
    default_info["connected_arrays"] = len(list(array.get_array_connections().items))
    default_info["pods"] = len(list(array.get_pods().items))
    default_info["connection_key"] = list(
        array.get_array_connections_connection_key().items
    )[0].connection_key
    if (
        LooseVersion(TLS_CONNECTION_API_VERSION) <= LooseVersion(api_version)
        and default_info["connected_arrays"] > 0
    ):
        default_info["connection_paths"] = []
        connection_paths = list(array.get_array_connections_path().items)
        for path in connection_paths:
            default_info["connection_paths"].append(
                {
                    path.name: {
                        "local_port": getattr(path, "local_port", None),
                        "local_address": getattr(path, "local_address", None),
                        "remote_port": getattr(path, "remote_port", None),
                        "remote_address": getattr(path, "remote_address", None),
                        "status": getattr(path, "status", None),
                        "transport": getattr(path, "replication_transport", None),
                        "encryption": getattr(path, "encryption", None),
                        "encryption_mode": getattr(path, "encryption_mode", None),
                    }
                }
            )
    default_info["array_model"] = list(array.get_controllers().items)[0].model
    default_info["array_name"] = list(array.get_arrays().items)[0].name
    default_info["purity_version"] = list(array.get_arrays().items)[0].version
    default_info["hosts"] = len(list(array.get_hosts().items))
    default_info["snapshots"] = len(list(array.get_volume_snapshots().items))
    default_info["volumes"] = len(list(array.get_volumes().items))
    default_info["protection_groups"] = len(list(array.get_protection_groups().items))
    default_info["hostgroups"] = len(list(array.get_host_groups().items))
    default_info["admins"] = len(list(array.get_admins().items))
    support_info = list(array.get_support().items)[0]
    default_info["remote_assist"] = support_info.remote_assist_status
    if LooseVersion(RA_API_VERSION) <= LooseVersion(api_version):
        default_info["remote_assist_detail"] = {
            "remote_assist_duration": str(
                int(support_info.remote_assist_duration / 3600000)
            )
            + " hours",
        }
        if support_info.remote_assist_expires != 0:
            default_info["remote_assist_detail"]["remote_assist_expires"] = (
                time.strftime(
                    "%Y-%m-%d %H:%M:%S %Z",
                    time.gmtime(support_info.remote_assist_expires / 1000),
                )
            )
        else:
            default_info["remote_assist_detail"]["remote_assist_expires"] = None
        if support_info.remote_assist_opened != 0:
            default_info["remote_assist_detail"]["remote_assist_opened"] = (
                time.strftime(
                    "%Y-%m-%d %H:%M:%S %Z",
                    time.gmtime(support_info.remote_assist_opened / 1000),
                )
            )
        else:
            default_info["remote_assist_detail"]["remote_assist_opened"] = None

    maint_info = list(array.get_maintenance_windows().items)
    if maint_info:
        default_info["maintenance_window"] = [
            {
                "name": maint_info[0].name,
                "created": time.strftime(
                    "%a, %d %b %Y %H:%M:%S %Z",
                    time.localtime(maint_info[0].created / 1000),
                ),
                "expires": time.strftime(
                    "%a, %d %b %Y %H:%M:%S %Z",
                    time.localtime(maint_info[0].expires / 1000),
                ),
            }
        ]
    else:
        default_info["maintenance_window"] = []
    if LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version):
        res = array.get_fleets()
        if res.status_code == 200:
            if len(res.items) > 0:
                default_info["fleet"] = getattr(list(res.items)[0], "name", None)
    else:
        default_info["fleet"] = "Fusion not supported"
    return default_info


def generate_perf_dict(array):
    perf_data = list(array.get_arrays_performance().items)[0]
    perf_info = {
        "bytes_per_mirrored_write": perf_data.bytes_per_mirrored_write,
        "bytes_per_op": perf_data.bytes_per_op,
        "bytes_per_read": perf_data.bytes_per_read,
        "bytes_per_write": perf_data.bytes_per_write,
        "local_queue_usec_per_op": perf_data.bytes_per_write,
        "mirrored_write_bytes_per_sec": perf_data.mirrored_write_bytes_per_sec,
        "mirrored_writes_per_sec": perf_data.mirrored_writes_per_sec,
        "others_per_sec": perf_data.others_per_sec,
        "qos_rate_limit_usec_per_mirrored_write_op": perf_data.qos_rate_limit_usec_per_mirrored_write_op,
        "qos_rate_limit_usec_per_read_op": perf_data.qos_rate_limit_usec_per_read_op,
        "qos_rate_limit_usec_per_write_op": perf_data.qos_rate_limit_usec_per_write_op,
        "queue_usec_per_mirrored_write_op": perf_data.queue_usec_per_mirrored_write_op,
        "queue_usec_per_read_op": perf_data.queue_usec_per_read_op,
        "queue_usec_per_write_op": perf_data.queue_usec_per_write_op,
        "read_bytes_per_sec": perf_data.read_bytes_per_sec,
        "reads_per_sec": perf_data.reads_per_sec,
        "san_usec_per_mirrored_write_op": perf_data.san_usec_per_mirrored_write_op,
        "san_usec_per_read_op": perf_data.san_usec_per_read_op,
        "san_usec_per_write_op": perf_data.san_usec_per_write_op,
        "service_usec_per_mirrored_write_op": perf_data.service_usec_per_mirrored_write_op,
        "service_usec_per_read_op": perf_data.service_usec_per_read_op,
        "service_usec_per_write_op": perf_data.service_usec_per_write_op,
        "usec_per_mirrored_write_op": perf_data.usec_per_mirrored_write_op,
        "usec_per_other_op": perf_data.usec_per_other_op,
        "usec_per_read_op": perf_data.usec_per_read_op,
        "usec_per_write_op": perf_data.usec_per_write_op,
        "write_bytes_per_sec": perf_data.write_bytes_per_sec,
        "writes_per_sec": perf_data.writes_per_sec,
        # These are legacy values. Return 0 for backwards compatibility
        "input_per_sec": 0,
        "output_per_sec": 0,
        "queue_depth": 0,
    }
    return perf_info


def generate_config_dict(module, array):
    config_info = {}
    api_version = array.get_rest_version()
    array_info = list(array.get_arrays().items)[0]
    config_info["console_lock"] = ("disabled", "enabled")[
        array_info.console_lock_enabled
    ]
    alert_info = list(array.get_alert_watchers().items)
    config_info["smtp"] = []
    for watcher in alert_info:
        config_info["smtp"].append({"name": watcher.name, "enabled": watcher.enabled})
    snmp_info = list(array.get_snmp_managers().items)
    config_info["snmp"] = []
    snmp_agent = list(array.get_snmp_agents().items)[0]
    config_info["snmp"].append(
        {
            "name": snmp_agent.name,
            "host": "localhost",
            "version": snmp_agent.version,
            "user": getattr(snmp_agent.v3, "user", None),
            "auth_password": getattr(snmp_agent.v3, "auth_password", None),
            "auth_protocol": getattr(snmp_agent.v3, "auth_protocol", None),
            "privacy_password": getattr(snmp_agent.v3, "privacy_password", None),
            "privacy_protocol": getattr(snmp_agent.v3, "privacy_protocol", None),
            "notification": getattr(snmp_agent, "notification", None),
            "community": getattr(snmp_agent.v2c, "community", None),
        }
    )
    for manager in snmp_info:
        config_info["snmp"].append(
            {
                "name": manager.name,
                "host": manager.host,
                "version": manager.version,
                "user": getattr(manager.v3, "user", None),
                "auth_password": getattr(manager.v3, "auth_password", None),
                "auth_protocol": getattr(manager.v3, "auth_protocol", None),
                "privacy_password": getattr(manager.v3, "privacy_password", None),
                "privacy_protocol": getattr(manager.v3, "privacy_protocol", None),
                "notification": manager.notification,
                "community": getattr(manager.v2c, "community", None),
            }
        )
    config_info["snmp_v3_engine_id"] = snmp_agent.engine_id
    smtp_info = list(array.get_smtp_servers().items)[0]
    config_info["smtp_servers"] = {
        "name": smtp_info.name,
        "password": getattr(smtp_info, "password", ""),
        "user_name": getattr(smtp_info, "user_name", ""),
        "encryption_mode": getattr(smtp_info, "encryption_mode", ""),
        "relay_host": getattr(smtp_info, "relay_host", ""),
        "sender_domain": getattr(smtp_info, "sender_domain", ""),
    }
    config_info["directory_service"] = {}
    services = list(array.get_directory_services().items)
    for service in services:
        service_type = service.name
        config_info["directory_service"][service_type] = {
            "base_dn": getattr(service, "base_dn", "None"),
            "bind_user": getattr(service, "bind_user", "None"),
            "enabled": service.enabled,
            "services": service.services,
            "uris": service.uris,
        }
    config_info["directory_service_roles"] = {}
    roles = list(array.get_directory_services_roles().items)
    for role in roles:
        role_name = role.role.name
        config_info["directory_service_roles"][role_name] = {
            "group": getattr(role, "group", None),
            "group_base": getattr(role, "group_base", None),
            "management_access_policies": None,
        }
        if LooseVersion(DSROLE_POLICY_API_VERSION) <= LooseVersion(api_version):
            config_info["directory_service_roles"][role_name][
                "management_access_policies"
            ] = getattr(role.management_access_policies[0], "name", None)
    smi_s = list(array.get_smi_s().items)[0]
    config_info["smi-s"] = {
        "slp_enabled": smi_s.slp_enabled,
        "wbem_https_enabled": smi_s.wbem_https_enabled,
    }
    # Add additional SMI-S section to help with formatting
    # issues caused by `-` in the dict name.
    config_info["smi_s"] = {
        "slp_enabled": smi_s.slp_enabled,
        "wbem_https_enabled": smi_s.wbem_https_enabled,
    }
    config_info["dns"] = {}
    dns_configs = list(array.get_dns().items)
    for config in dns_configs:
        config_info["dns"][config.services[0]] = {
            "nameservers": config.nameservers,
            "domain": config.domain,
        }
        config_info["dns"][config.services[0]]["source"] = getattr(
            config.source, "name", None
        )
    if LooseVersion(SAML2_VERSION) <= LooseVersion(api_version):
        config_info["saml2sso"] = {}
        saml2 = list(array.get_sso_saml2_idps().items)
        if saml2:
            config_info["saml2sso"] = {
                "enabled": saml2[0].enabled,
                "array_url": saml2[0].array_url,
                "name": saml2[0].name,
                "idp": {},
                "sp": {},
            }
            if hasattr(saml2[0], "idp"):
                config_info["saml2sso"]["idp"] = {
                    "url": getattr(saml2[0].idp, "url", None),
                    "encrypt_enabled": saml2[0].idp.encrypt_assertion_enabled,
                    "sign_enabled": saml2[0].idp.sign_request_enabled,
                    "metadata_url": saml2[0].idp.metadata_url,
                }
            if hasattr(saml2[0], "sp"):
                if hasattr(saml2[0].sp, "decryption_credential"):
                    decrypt = getattr(saml2[0].sp.decryption_credential, "name", None)
                else:
                    decrypt = None
                if hasattr(saml2[0].sp, "signing_credential"):
                    sign = getattr(saml2[0].sp.signing_credential, "name", None)
                else:
                    sign = None
                config_info["saml2sso"]["sp"] = {
                    "decrypt_cred": decrypt,
                    "sign_cred": sign,
                }
    config_info["active_directory"] = {}
    res = array.get_active_directory()
    if res.status_code != 200:
        module.warn("FA-Files is not enabled on this array")
    else:
        ad_accounts = list(res.items)
        for ad_account in ad_accounts:
            ad_name = ad_account.name
            config_info["active_directory"][ad_name] = {
                "computer_name": ad_account.computer_name,
                "domain": ad_account.domain,
                "directory_servers": getattr(ad_account, "directory_servers", None),
                "kerberos_servers": getattr(ad_account, "kerberos_servers", None),
                "service_principal_names": getattr(
                    ad_account, "service_principal_names", None
                ),
                "tls": getattr(ad_account, "tls", None),
            }
    if LooseVersion(DEFAULT_PROT_API_VERSION) <= LooseVersion(api_version):
        config_info["default_protections"] = {}
        default_prots = list(array.get_container_default_protections().items)
        for prot in default_prots:
            container = getattr(prot, "name", "-")
            config_info["default_protections"][container] = {
                "protections": [],
                "type": getattr(prot, "type", "array"),
            }
            for container_prot in prot.default_protections:
                config_info["default_protections"][container]["protections"].append(
                    {
                        "type": container_prot.type,
                        "name": container_prot.name,
                    }
                )
    if LooseVersion(SUBS_API_VERSION) <= LooseVersion(api_version):
        array_info = list(array.get_arrays().items)[0]
        config_info["ntp_keys"] = bool(getattr(array_info, "ntp_symmetric_key", None))
        config_info["timezone"] = array_info.time_zone
    config_info["directory_service"] = {}
    ds_info = list(array.get_directory_services().items)
    for dss in ds_info:
        config_info["directory_service"][dss.name] = {
            "base_dn": getattr(dss, "base_dn", None),
            "bind_user": getattr(dss, "bind_user", None),
            "check_peer": dss.check_peer,
            "enabled": dss.enabled,
            "services": getattr(dss, "services", None),
            "uri": getattr(dss, "uris", None),
        }
    config_info["directory_service_roles"] = {}
    roles = list(array.get_directory_services_roles().items)
    for role in roles:
        role_name = getattr(role, "name", None)
        if role_name:
            config_info["directory_service_roles"][role_name] = {
                "group": getattr(role, "group", None),
                "group_base": getattr(role, "group_base", None),
            }
    config_info["ntp"] = array_info.ntp_servers
    syslog_info = list(array.get_syslog_servers().items)
    config_info["syslog"] = {}
    for syslog in syslog_info:
        config_info["syslog"][syslog.name] = {
            "uri": getattr(syslog, "uri", None),
            "services": getattr(syslog, "services", None),
        }
    support_info = list(array.get_support().items)[0]
    config_info["phonehome"] = ("disabled", "enabled")[support_info.phonehome_enabled]
    config_info["proxy"] = support_info.proxy
    config_info["relayhost"] = getattr(smtp_info, "relay_host", "")
    config_info["senderdomain"] = getattr(smtp_info, "sender_domain", "")
    config_info["idle_timeout"] = array_info.idle_timeout
    config_info["scsi_timeout"] = array_info.scsi_timeout
    admin_info = list(array.get_admins_settings().items)[0]
    config_info["global_admin"] = {
        "lockout_duration": getattr(admin_info, "lockout_duration", None),
        "max_login_attempts": getattr(admin_info, "max_login_attempts", None),
        "min_password_length": getattr(admin_info, "min_password_length", None),
        "single_sign_on_enabled": getattr(admin_info, "single_sign_on_enabled", None),
        "active_management_enabled": None,
        "active_management_role": None,
    }
    if (
        config_info["global_admin"]["lockout_duration"]
        and config_info["global_admin"]["lockout_duration"] > 0
    ):
        config_info["global_admin"]["lockout_duration"] = int(
            config_info["global_admin"]["lockout_duration"] / 1000
        )
    return config_info


def generate_filesystems_dict(array, performance):
    files_info = {}
    filesystems = list(array.get_file_systems().items)
    for filesystem in filesystems:
        fs_name = filesystem.name
        files_info[fs_name] = {
            "destroyed": filesystem.destroyed,
            "directories": {},
        }
        directories = list(array.get_directories(file_system_names=[fs_name]).items)
        for directory in directories:
            d_name = directory.directory_name
            files_info[fs_name]["directories"][d_name] = {
                "path": directory.path,
                "data_reduction": getattr(directory.space, "data_reduction", None),
                "snapshots_space": getattr(directory.space, "snapshots", None),
                "thin_provisioning": getattr(
                    directory.space, "thin_provisioning", None
                ),
                "total_physical_space": getattr(
                    directory.space, "total_physical", None
                ),
                "total_provisioned_space": getattr(
                    directory.space, "total_provisioned", None
                ),
                "total_reduction": getattr(directory.space, "total_reduction", None),
                "total_used": getattr(directory.space, "total_used", None),
                "unique_space": getattr(directory.space, "unique", None),
                "virtual_space": getattr(directory.space, "virtual", None),
                "destroyed": directory.destroyed,
                "full_name": directory.name,
                "used_provisioned": getattr(directory.space, "used_provisioned", None),
                "exports": [],
                "policies": [],
                "limited_by": None,
                "performance": [],
            }
            if LooseVersion(QUOTA_API_VERSION) <= LooseVersion(
                array.get_rest_version()
            ):
                if hasattr(directory.limited_by, "member"):
                    files_info[fs_name]["directories"][d_name]["limited_by"] = getattr(
                        directory.limited_by.member, "name", None
                    )
            policies = list(
                array.get_directories_policies(
                    member_names=[
                        files_info[fs_name]["directories"][d_name]["full_name"]
                    ]
                ).items
            )
            for policy in policies:
                files_info[fs_name]["directories"][d_name]["policies"].append(
                    {
                        "enabled": policy.enabled,
                        "policy": {
                            "name": policy.policy.name,
                            "type": policy.policy.resource_type,
                        },
                    }
                )
            exports = list(
                array.get_directory_exports(
                    directory_names=[
                        files_info[fs_name]["directories"][d_name]["full_name"]
                    ]
                ).items
            )
            for export in exports:
                files_info[fs_name]["directories"][d_name]["exports"].append(
                    {
                        "enabled": export.enabled,
                        "export_name": export.export_name,
                        "policy": {
                            "name": export.policy.name,
                            "type": export.policy.resource_type,
                        },
                    }
                )
            if (
                performance
                and not files_info[fs_name]["directories"][d_name]["destroyed"]
            ):
                perf_stats = list(
                    array.get_directories_performance(
                        names=[files_info[fs_name]["directories"][d_name]["full_name"]]
                    ).items
                )[0]
                files_info[fs_name]["directories"][d_name]["performance"] = {
                    "bytes_per_op": perf_stats.bytes_per_op,
                    "bytes_per_read": perf_stats.bytes_per_read,
                    "bytes_per_write": perf_stats.bytes_per_write,
                    "others_per_sec": perf_stats.others_per_sec,
                    "read_bytes_per_sec": perf_stats.read_bytes_per_sec,
                    "reads_per_sec": perf_stats.reads_per_sec,
                    "usec_per_other_op": perf_stats.usec_per_other_op,
                    "usec_per_read_op": perf_stats.usec_per_read_op,
                    "usec_per_write_op": perf_stats.usec_per_write_op,
                    "write_bytes_per_sec": perf_stats.write_bytes_per_sec,
                    "writes_per_sec": perf_stats.writes_per_sec,
                }
    return files_info


def generate_pgsnaps_dict(array):
    pgsnaps_info = {}
    snapshots = list(array.get_protection_group_snapshots().items)
    for snapshot in snapshots:
        s_name = snapshot.name
        pgsnaps_info[s_name] = {
            "destroyed": snapshot.destroyed,
            "source": snapshot.source.name,
            "suffix": snapshot.suffix,
            "snapshot_space": getattr(snapshot.space, "snapshots", None),
            "used_provisioned": getattr(snapshot.space, "used_provisioned", None),
        }
        try:
            if pgsnaps_info[s_name]["destroyed"]:
                pgsnaps_info[s_name]["time_remaining"] = snapshot.time_remaining
        except AttributeError:
            pass
        try:
            pgsnaps_info[s_name][
                "manual_eradication"
            ] = snapshot.eradication_config.manual_eradication
        except AttributeError:
            pass
    return pgsnaps_info


def generate_dir_snaps_dict(array):
    dir_snaps_info = {}
    snapshots = list(array.get_directory_snapshots().items)
    for snapshot in snapshots:
        s_name = snapshot.name
        if hasattr(snapshot, "suffix"):
            suffix = snapshot.suffix
        else:
            suffix = snapshot.name.split(".")[-1]
        dir_snaps_info[s_name] = {
            "destroyed": snapshot.destroyed,
            "source": snapshot.source.name,
            "suffix": suffix,
            "client_name": snapshot.client_name,
            "snapshot_space": getattr(snapshot.space, "snapshots", None),
            "total_physical_space": getattr(snapshot.space, "total_physical", None),
            "unique_space": getattr(snapshot.space, "unique", None),
            "used_provisioned": getattr(snapshot.space, "used_provisioned", None),
        }
        if LooseVersion(SUBS_API_VERSION) <= LooseVersion(array.get_rest_version()):
            dir_snaps_info[s_name]["total_used"] = getattr(
                snapshot.space, "total_used", None
            )
        if hasattr(snapshot, "policy"):
            dir_snaps_info[s_name]["policy"] = getattr(snapshot.policy, "name", None)
        if dir_snaps_info[s_name]["destroyed"] or hasattr(snapshot, "time_remaining"):
            dir_snaps_info[s_name]["time_remaining"] = snapshot.time_remaining
    return dir_snaps_info


def generate_policies_dict(array, quota_available, autodir_available, nfs_user_mapping):
    policy_info = {}
    policies = list(array.get_policies().items)
    for policy in policies:
        p_name = policy.name
        policy_info[p_name] = {
            "type": policy.policy_type,
            "enabled": policy.enabled,
            "members": [],
            "rules": [],
        }
        members = list(array.get_directories_policies(policy_names=[p_name]).items)
        for member in members:
            m_name = member.member.name
            policy_info[p_name]["members"].append(m_name)
        if policy.policy_type == "smb":
            rules = list(
                array.get_policies_smb_client_rules(policy_names=[p_name]).items
            )
            for rule in rules:
                smb_rules_dict = {
                    "client": rule.client,
                    "smb_encryption_required": rule.smb_encryption_required,
                    "anonymous_access_allowed": rule.anonymous_access_allowed,
                }
                policy_info[p_name]["rules"].append(smb_rules_dict)
        if policy.policy_type == "nfs":
            if nfs_user_mapping:
                nfs_policy = list(array.get_policies_nfs(names=[p_name]).items)[0]
                policy_info[p_name][
                    "user_mapping_enabled"
                ] = nfs_policy.user_mapping_enabled
                if LooseVersion(SUBS_API_VERSION) <= LooseVersion(
                    array.get_rest_version()
                ):
                    policy_info[p_name]["nfs_version"] = getattr(
                        nfs_policy, "nfs_version", None
                    )
                if LooseVersion(NFS_SECURITY_VERSION) <= LooseVersion(
                    array.get_rest_version()
                ):
                    policy_info[p_name]["security"] = getattr(
                        nfs_policy, "security", None
                    )
            rules = list(
                array.get_policies_nfs_client_rules(policy_names=[p_name]).items
            )
            for rule in rules:
                nfs_rules_dict = {
                    "access": rule.access,
                    "permission": rule.permission,
                    "client": rule.client,
                }
                if LooseVersion(SUBS_API_VERSION) <= LooseVersion(
                    array.get_rest_version()
                ):
                    nfs_rules_dict["nfs_version"] = rule.nfs_version
                policy_info[p_name]["rules"].append(nfs_rules_dict)
        if policy.policy_type == "snapshot":
            suffix_enabled = bool(
                LooseVersion(array.get_rest_version())
                >= LooseVersion(SHARED_CAP_API_VERSION)
            )
            rules = list(array.get_policies_snapshot_rules(policy_names=[p_name]).items)
            for rule in rules:
                try:
                    snap_rules_dict = {
                        "at": str(int(rule.at / 3600000)).zfill(2) + ":00",
                        "client_name": rule.client_name,
                        "every": str(int(rule.every / 60000)) + " mins",
                        "keep_for": str(int(rule.keep_for / 60000)) + " mins",
                    }
                except AttributeError:
                    snap_rules_dict = {
                        "at": None,
                        "client_name": rule.client_name,
                        "every": str(int(rule.every / 60000)) + " mins",
                        "keep_for": str(int(rule.keep_for / 60000)) + " mins",
                    }
                if suffix_enabled:
                    try:
                        snap_rules_dict["suffix"] = rule.suffix
                    except AttributeError:
                        snap_rules_dict["suffix"] = ""
                policy_info[p_name]["rules"].append(snap_rules_dict)
        if policy.policy_type == "quota" and quota_available:
            rules = list(array.get_policies_quota_rules(policy_names=[p_name]).items)
            for rule in rules:
                quota_rules_dict = {
                    "enforced": rule.enforced,
                    "quota_limit": rule.quota_limit,
                    "notifications": rule.notifications,
                }
                policy_info[p_name]["rules"].append(quota_rules_dict)
        if policy.policy_type == "autodir" and autodir_available:
            pass  # there are currently no rules for autodir policies
        if policy.policy_type == "password":
            pwd_policy = list(array.get_policies_password(names=[p_name]).items)[0]
            policy_info[p_name] |= {
                "enabled": pwd_policy.enabled,
                "enforce_dictionary_check": pwd_policy.enforce_dictionary_check,
                "enforce_username_check": pwd_policy.enforce_username_check,
                "lockout_duration": getattr(pwd_policy, "lockout_duration", None),
                "password_history": getattr(pwd_policy, "password_history", None),
                "min_character_groups": pwd_policy.min_character_groups,
                "min_characters_per_group": pwd_policy.min_characters_per_group,
                "min_password_length": pwd_policy.min_password_length,
            }
    return policy_info


def generate_clients_dict(array):
    clients_info = {}
    clients = list(array.get_api_clients().items)
    for client in clients:
        clients_info[client.name] = {
            "name": client.name,
            "enabled": client.enabled,
            "client_id": client.id,
            "key_id": client.key_id,
            "issuer": getattr(client, "issuer", None),
            "max_role": getattr(client, "max_role", None),
            "access_token_ttl_ms": client.access_token_ttl_in_ms,
            "access_token_ttl_seconds": (
                client.access_token_ttl_in_ms / 1000
                if client.access_token_ttl_in_ms is not None
                else None
            ),
            # For backwards compatability
            "TTL(seconds)": (
                client.access_token_ttl_in_ms / 1000
                if client.access_token_ttl_in_ms is not None
                else None
            ),
            "public_key": getattr(client, "public_key", None),
            "access_policies": [
                {
                    "name": policy.name,
                }
                for policy in getattr(client, "access_policies", []) or []
            ],
        }
    return clients_info


def generate_admin_dict(array):
    admin_info = {}
    admins = list(array.get_admins().items)
    for admin in admins:
        admin_name = admin.name
        admin_info[admin_name] = {
            "public_key": admin.public_key,
            "local": admin.is_local,
            "role": admin.role.name,
            "locked": admin.locked,
            "lockout_remaining": getattr(admin, "lockout_remaining", None),
        }
        if hasattr(admin.api_token, "expires_at"):
            if admin.api_token.expires_at:
                admin_info[admin_name]["token_expires"] = datetime.fromtimestamp(
                    admin.api_token.expires_at / 1000
                ).strftime("%Y-%m-%d %H:%M:%S")
        else:
            admin_info[admin_name]["token_expires"] = None
        if hasattr(admin.api_token, "created_at"):
            if admin.api_token.created_at:
                admin_info[admin_name]["token_created"] = datetime.fromtimestamp(
                    admin.api_token.created_at / 1000
                ).strftime("%Y-%m-%d %H:%M:%S")
        else:
            admin_info[admin_name]["token_created"] = None
    return admin_info


def generate_subnet_dict(array):
    sub_info = {}
    subnets = list(array.get_subnets().items)
    for subnet in subnets:
        sub_name = subnet.name
        sub_info[sub_name] = {
            "enabled": subnet.enabled,
            "gateway": getattr(subnet, "gateway", None),
            "mtu": subnet.mtu,
            "vlan": getattr(subnet, "vlan", None),
            "prefix": subnet.prefix,
            "interfaces": [],
            "services": subnet.services,
        }
        if subnet.interfaces:
            for iface in subnet.interfaces:
                sub_info[sub_name]["interfaces"].append(iface.name)
    return sub_info


def generate_network_dict(array, performance):
    net_info = {}
    ports = list(array.get_network_interfaces().items)
    for port in ports:
        int_name = port.name
        if port.interface_type == "eth":
            net_info[int_name] = {
                "hwaddr": getattr(port.eth, "mac_address", None),
                "mac_address": getattr(port.eth, "mac_address", None),
                "mtu": getattr(port.eth, "mtu", None),
                "enabled": port.enabled,
                "speed": port.speed,
                "address": getattr(port.eth, "address", None),
                "subinterfaces": [],
                "slaves": [],
                "subnet": getattr(port.eth.subnet, "name", None),
                "services": port.services,
                "gateway": getattr(port.eth, "gateway", None),
                "netmask": getattr(port.eth, "netmask", None),
                "subtype": getattr(port.eth, "subtype", None),
                "vlan": getattr(port.eth, "vlan", None),
                "performance": [],
            }
            if port.eth.subinterfaces:
                for subi in port.eth.subinterfaces:
                    net_info[int_name]["subinterfaces"].append(subi.name)
                net_info[int_name]["slaves"] = net_info[int_name]["subinterfaces"]
        else:
            net_info[int_name] = {
                "port_name": port.fc.wwn,
                "services": port.services,
                "enabled": port.enabled,
                "performance": [],
            }
    if performance:
        perf_stats = list(array.get_network_interfaces_performance().items)
        for perf_stat in perf_stats:
            try:
                if perf_stat.interface_type == "fc":
                    net_info[perf_stat.name]["performance"] = {
                        "received_bytes_per_sec": getattr(
                            perf_stat.fc, "received_bytes_per_sec", 0
                        ),
                        "received_crc_errors_per_sec": getattr(
                            perf_stat.fc, "received_crc_errors_per_sec", 0
                        ),
                        "received_frames_per_sec": getattr(
                            perf_stat.fc, "received_frames_per_sec", 0
                        ),
                        "received_link_failures_per_sec": getattr(
                            perf_stat.fc,
                            "received_link_failures_per_sec",
                            0,
                        ),
                        "received_loss_of_signal_per_sec": getattr(
                            perf_stat.fc,
                            "received_loss_of_signal_per_sec",
                            0,
                        ),
                        "received_loss_of_sync_per_sec": getattr(
                            perf_stat.fc, "received_loss_of_sync_per_sec", 0
                        ),
                        "total_errors_per_sec": getattr(
                            perf_stat.fc, "total_errors_per_sec", 0
                        ),
                        "transmitted_bytes_per_sec": getattr(
                            perf_stat.fc, "transmitted_bytes_per_sec", 0
                        ),
                        "transmitted_frames_per_sec": getattr(
                            perf_stat.fc, "transmitted_frames_per_sec", 0
                        ),
                        "transmitted_invalid_words_per_sec": getattr(
                            perf_stat.fc,
                            "transmitted_invalid_words_per_sec",
                            0,
                        ),
                    }
                else:
                    net_info[perf_stat.name]["performance"] = {
                        "received_bytes_per_sec": getattr(
                            perf_stat.eth, "received_bytes_per_sec", 0
                        ),
                        "received_crc_errors_per_sec": getattr(
                            perf_stat.eth, "received_crc_errors_per_sec", 0
                        ),
                        "received_frame_errors_per_sec": getattr(
                            perf_stat.eth,
                            "received_frame_errors_per_sec",
                            0,
                        ),
                        "received_packets_per_sec": getattr(
                            perf_stat.eth, "received_packets_per_sec", 0
                        ),
                        "total_errors_per_sec": getattr(
                            perf_stat.eth, "total_errors_per_sec", 0
                        ),
                        "transmitted_bytes_per_sec": getattr(
                            perf_stat.eth, "transmitted_bytes_per_sec", 0
                        ),
                        "transmitted_dropped_errors_per_sec": getattr(
                            perf_stat.eth,
                            "transmitted_dropped_errors_per_sec",
                            0,
                        ),
                        "transmitted_packets_per_sec": getattr(
                            perf_stat.eth, "transmitted_packets_per_sec", 0
                        ),
                        "rdma_received_req_cqe_errors_per_sec": getattr(
                            perf_stat.eth,
                            "rdma_received_req_cqe_errors_per_sec",
                            0,
                        ),
                        "rdma_received_sequence_errors_per_sec": getattr(
                            perf_stat.eth,
                            "rdma_received_sequence_errors_per_sec",
                            0,
                        ),
                        "rdma_transmitted_local_ack_timeout_errors_per_sec": getattr(
                            perf_stat.eth,
                            "rdma_transmitted_local_ack_timeout_errors_per_sec",
                            0,
                        ),
                        "flow_control_received_congestion_packets_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_received_congestion_packets_per_sec",
                            0,
                        ),
                        "flow_control_received_discarded_packets_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_received_discarded_packets_per_sec",
                            0,
                        ),
                        "flow_control_received_lossless_bytes_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_received_lossless_bytes_per_sec",
                            0,
                        ),
                        "flow_control_received_pause_frames_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_received_pause_frames_per_sec",
                            0,
                        ),
                        "flow_control_transmitted_congestion_packets_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_transmitted_congestion_packets_per_sec",
                            0,
                        ),
                        "flow_control_transmitted_discarded_packets_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_transmitted_discarded_packets_per_sec",
                            0,
                        ),
                        "flow_control_transmitted_lossless_bytes_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_transmitted_lossless_bytes_per_sec",
                            0,
                        ),
                        "flow_control_transmitted_pause_frames_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_transmitted_pause_frames_per_sec",
                            0,
                        ),
                    }
            except KeyError:
                net_info[perf_stat.name] = {
                    "hwaddr": None,
                    "mtu": None,
                    "enabled": None,
                    "speed": None,
                    "address": None,
                    "slaves": None,
                    "services": None,
                    "gateway": None,
                    "netmask": None,
                    "subnet": None,
                    "performance": {
                        "received_bytes_per_sec": getattr(
                            perf_stat.eth, "received_bytes_per_sec", 0
                        ),
                        "received_crc_errors_per_sec": getattr(
                            perf_stat.eth, "received_crc_errors_per_sec", 0
                        ),
                        "received_frame_errors_per_sec": getattr(
                            perf_stat.eth,
                            "received_frame_errors_per_sec",
                            0,
                        ),
                        "received_packets_per_sec": getattr(
                            perf_stat.eth, "received_packets_per_sec", 0
                        ),
                        "total_errors_per_sec": getattr(
                            perf_stat.eth, "total_errors_per_sec", 0
                        ),
                        "transmitted_bytes_per_sec": getattr(
                            perf_stat.eth, "transmitted_bytes_per_sec", 0
                        ),
                        "transmitted_dropped_errors_per_sec": getattr(
                            perf_stat.eth,
                            "transmitted_dropped_errors_per_sec",
                            0,
                        ),
                        "transmitted_packets_per_sec": getattr(
                            perf_stat.eth, "transmitted_packets_per_sec", 0
                        ),
                        "rdma_received_req_cqe_errors_per_sec": getattr(
                            perf_stat.eth,
                            "rdma_received_req_cqe_errors_per_sec",
                            0,
                        ),
                        "rdma_received_sequence_errors_per_sec": getattr(
                            perf_stat.eth,
                            "rdma_received_sequence_errors_per_sec",
                            0,
                        ),
                        "rdma_transmitted_local_ack_timeout_errors_per_sec": getattr(
                            perf_stat.eth,
                            "rdma_transmitted_local_ack_timeout_errors_per_sec",
                            0,
                        ),
                        "flow_control_received_congestion_packets_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_received_congestion_packets_per_sec",
                            0,
                        ),
                        "flow_control_received_discarded_packets_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_received_discarded_packets_per_sec",
                            0,
                        ),
                        "flow_control_received_lossless_bytes_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_received_lossless_bytes_per_sec",
                            0,
                        ),
                        "flow_control_received_pause_frames_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_received_pause_frames_per_sec",
                            0,
                        ),
                        "flow_control_transmitted_congestion_packets_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_transmitted_congestion_packets_per_sec",
                            0,
                        ),
                        "flow_control_transmitted_discarded_packets_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_transmitted_discarded_packets_per_sec",
                            0,
                        ),
                        "flow_control_transmitted_lossless_bytes_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_transmitted_lossless_bytes_per_sec",
                            0,
                        ),
                        "flow_control_transmitted_pause_frames_per_sec": getattr(
                            perf_stat.eth,
                            "flow_control_transmitted_pause_frames_per_sec",
                            0,
                        ),
                    },
                }
    if LooseVersion(NEIGHBOR_API_VERSION) <= LooseVersion(array.get_rest_version()):
        neighbors = list(array.get_network_interfaces_neighbors().items)
        for neighbor in neighbors:
            int_name = neighbor.local_port.name
            try:
                net_info[int_name].update(
                    {
                        "neighbor": {
                            "initial_ttl_in_sec": neighbor.initial_ttl_in_sec,
                            "neighbor_port": {
                                "description": getattr(
                                    neighbor.neighbor_port, "description", None
                                ),
                                "name": getattr(
                                    neighbor.neighbor_chassis, "name", None
                                ),
                                "id": getattr(neighbor.neighbor_port.id, "value", None),
                            },
                            "neighbor_chassis": {
                                "addresses": getattr(
                                    neighbor.neighbor_chassis, "addresses", None
                                ),
                                "description": getattr(
                                    neighbor.neighbor_chassis, "description", None
                                ),
                                "name": getattr(
                                    neighbor.neighbor_chassis, "name", None
                                ),
                                "bridge": {
                                    "enabled": getattr(
                                        neighbor.neighbor_chassis.bridge,
                                        "enabled",
                                        False,
                                    ),
                                    "supported": getattr(
                                        neighbor.neighbor_chassis.bridge,
                                        "supported",
                                        False,
                                    ),
                                },
                                "repeater": {
                                    "enabled": getattr(
                                        neighbor.neighbor_chassis.repeater,
                                        "enabled",
                                        False,
                                    ),
                                    "supported": getattr(
                                        neighbor.neighbor_chassis.repeater,
                                        "supported",
                                        False,
                                    ),
                                },
                                "router": {
                                    "enabled": getattr(
                                        neighbor.neighbor_chassis.router,
                                        "enabled",
                                        False,
                                    ),
                                    "supported": getattr(
                                        neighbor.neighbor_chassis.router,
                                        "supported",
                                        False,
                                    ),
                                },
                                "station_only": {
                                    "enabled": getattr(
                                        neighbor.neighbor_chassis.station_only,
                                        "enabled",
                                        False,
                                    ),
                                    "supported": getattr(
                                        neighbor.neighbor_chassis.station_only,
                                        "supported",
                                        False,
                                    ),
                                },
                                "telephone": {
                                    "enabled": getattr(
                                        neighbor.neighbor_chassis.telephone,
                                        "enabled",
                                        False,
                                    ),
                                    "supported": getattr(
                                        neighbor.neighbor_chassis.telephone,
                                        "supported",
                                        False,
                                    ),
                                },
                                "wlan_access_point": {
                                    "enabled": getattr(
                                        neighbor.neighbor_chassis.wlan_access_point,
                                        "enabled",
                                        False,
                                    ),
                                    "supported": getattr(
                                        neighbor.neighbor_chassis.wlan_access_point,
                                        "supported",
                                        False,
                                    ),
                                },
                                "docsis_cable_device": {
                                    "enabled": getattr(
                                        neighbor.neighbor_chassis.docsis_cable_device,
                                        "enabled",
                                        False,
                                    ),
                                    "supported": getattr(
                                        neighbor.neighbor_chassis.docsis_cable_device,
                                        "supported",
                                        False,
                                    ),
                                },
                                "id": {
                                    "type": getattr(
                                        neighbor.neighbor_chassis.id,
                                        "type",
                                        None,
                                    ),
                                    "value": getattr(
                                        neighbor.neighbor_chassis.id,
                                        "value",
                                        None,
                                    ),
                                },
                            },
                        }
                    }
                )
            except KeyError:
                net_info[int_name] = {
                    "hwaddr": None,
                    "mtu": None,
                    "enabled": None,
                    "speed": None,
                    "address": None,
                    "slaves": None,
                    "services": None,
                    "gateway": None,
                    "netmask": None,
                    "subnet": None,
                    "neighbor": {
                        "initial_ttl_in_sec": neighbor.initial_ttl_in_sec,
                        "neighbor_port": {
                            "description": getattr(
                                neighbor.neighbor_port, "description", None
                            ),
                            "name": getattr(neighbor.neighbor_chassis, "name", None),
                            "id": getattr(neighbor.neighbor_port.id, "value", None),
                        },
                        "neighbor_chassis": {
                            "addresses": getattr(
                                neighbor.neighbor_chassis, "addresses", None
                            ),
                            "description": getattr(
                                neighbor.neighbor_chassis, "description", None
                            ),
                            "name": getattr(neighbor.neighbor_chassis, "name", None),
                            "bridge": {
                                "enabled": getattr(
                                    neighbor.neighbor_chassis.bridge,
                                    "enabled",
                                    False,
                                ),
                                "supported": getattr(
                                    neighbor.neighbor_chassis.bridge,
                                    "supported",
                                    False,
                                ),
                            },
                            "repeater": {
                                "enabled": getattr(
                                    neighbor.neighbor_chassis.repeater,
                                    "enabled",
                                    False,
                                ),
                                "supported": getattr(
                                    neighbor.neighbor_chassis.repeater,
                                    "supported",
                                    False,
                                ),
                            },
                            "router": {
                                "enabled": getattr(
                                    neighbor.neighbor_chassis.router,
                                    "enabled",
                                    False,
                                ),
                                "supported": getattr(
                                    neighbor.neighbor_chassis.router,
                                    "supported",
                                    False,
                                ),
                            },
                            "station_only": {
                                "enabled": getattr(
                                    neighbor.neighbor_chassis.station_only,
                                    "enabled",
                                    False,
                                ),
                                "supported": getattr(
                                    neighbor.neighbor_chassis.station_only,
                                    "supported",
                                    False,
                                ),
                            },
                            "telephone": {
                                "enabled": getattr(
                                    neighbor.neighbor_chassis.telephone,
                                    "enabled",
                                    False,
                                ),
                                "supported": getattr(
                                    neighbor.neighbor_chassis.telephone,
                                    "supported",
                                    False,
                                ),
                            },
                            "wlan_access_point": {
                                "enabled": getattr(
                                    neighbor.neighbor_chassis.wlan_access_point,
                                    "enabled",
                                    False,
                                ),
                                "supported": getattr(
                                    neighbor.neighbor_chassis.wlan_access_point,
                                    "supported",
                                    False,
                                ),
                            },
                            "docsis_cable_device": {
                                "enabled": getattr(
                                    neighbor.neighbor_chassis.docsis_cable_device,
                                    "enabled",
                                    False,
                                ),
                                "supported": getattr(
                                    neighbor.neighbor_chassis.docsis_cable_device,
                                    "supported",
                                    False,
                                ),
                            },
                            "id": {
                                "type": getattr(
                                    neighbor.neighbor_chassis.id,
                                    "type",
                                    None,
                                ),
                                "value": getattr(
                                    neighbor.neighbor_chassis.id,
                                    "value",
                                    None,
                                ),
                            },
                        },
                    },
                }

    return net_info


def generate_capacity_dict(array):
    capacity_info = {}
    total_capacity = list(array.get_arrays().items)[0].capacity
    capacity = list(array.get_arrays_space().items)[0]
    capacity_info["total_capacity"] = total_capacity
    capacity_info["parity"] = getattr(capacity, "parity", None)
    capacity_info["capacity_installed"] = getattr(capacity, "capacity_installed", None)
    if LooseVersion(SHARED_CAP_API_VERSION) <= LooseVersion(array.get_rest_version()):
        capacity_info["provisioned_space"] = getattr(
            capacity.space, "total_provisioned", 0
        )
        capacity_info["free_space"] = total_capacity - getattr(
            capacity.space, "total_physical", 0
        )
        capacity_info["data_reduction"] = getattr(capacity.space, "data_reduction", 0)
        capacity_info["system_space"] = getattr(capacity.space, "system", 0)
        capacity_info["volume_space"] = getattr(capacity.space, "unique", 0)
        capacity_info["shared_space"] = getattr(capacity.space, "shared", 0)
        capacity_info["snapshot_space"] = getattr(capacity.space, "snapshots", 0)
        capacity_info["thin_provisioning"] = getattr(
            capacity.space, "thin_provisioning", 0
        )
        capacity_info["total_reduction"] = getattr(capacity.space, "total_reduction", 0)
        capacity_info["replication"] = getattr(capacity.space, "replication", 0)
        capacity_info["shared_effective"] = getattr(
            capacity.space, "shared_effective", 0
        )
        capacity_info["snapshots_effective"] = getattr(
            capacity.space, "snapshots_effective", 0
        )
        capacity_info["unique_effective"] = getattr(
            capacity.space, "total_effective", 0
        )
        capacity_info["total_effective"] = getattr(capacity.space, "total_effective", 0)
        capacity_info["used_provisioned"] = getattr(
            capacity.space, "used_provisioned", 0
        )
        if LooseVersion(SUBS_API_VERSION) <= LooseVersion(array.get_rest_version()):
            capacity_info["total_used"] = getattr(capacity.space, "total_used", None)
    else:
        capacity_info["provisioned_space"] = capacity.space["total_provisioned"]
        capacity_info["free_space"] = total_capacity - capacity.space["total_physical"]
        capacity_info["data_reduction"] = capacity.space["data_reduction"]
        capacity_info["system_space"] = capacity.space["system"]
        capacity_info["volume_space"] = capacity.space["unique"]
        capacity_info["shared_space"] = capacity.space["shared"]
        capacity_info["snapshot_space"] = capacity.space["snapshots"]
        capacity_info["thin_provisioning"] = capacity.space["thin_provisioning"]
        capacity_info["total_reduction"] = capacity.space["total_reduction"]
        capacity_info["replication"] = capacity.space["replication"]
    if LooseVersion(NFS_SECURITY_VERSION) <= LooseVersion(
        array.get_rest_version()
    ) and _is_cbs(array):
        cloud = list(array.get_arrays_cloud_capacity().items)[0]
        capacity_info["cloud_capacity"] = {
            "current_capacity": cloud.current_capacity,
            "requested_capacity": cloud.requested_capacity,
            "status": cloud.status,
        }
    return capacity_info


def generate_snap_dict(array):
    snap_info = {}
    snaps = list(array.get_volume_snapshots(destroyed=False).items)
    for snap in snaps:
        snapshot = snap.name
        snap_info[snapshot] = {
            "size": getattr(snap.space, "total_provisioned", None),
            "source": getattr(snap.source, "name", None),
            "created_epoch": snap.created,
            "created": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(snap.created / 1000)
            ),
            "tags": [],
            "is_local": True,
            "remote": [],
        }
        if ":" in snapshot and "::" not in snapshot:
            snap_info[snapshot]["is_local"] = False
        snap_info[snapshot]["snapshot_space"] = getattr(snap.space, "snapshots", None)
        snap_info[snapshot]["used_provisioned"] = getattr(
            snap.space, "used_provisioned", None
        )
        snap_info[snapshot]["total_physical"] = getattr(
            snap.space, "total_physical", None
        )
        snap_info[snapshot]["total_provisioned"] = getattr(
            snap.space, "total_provisioned", None
        )
        snap_info[snapshot]["unique_space"] = getattr(snap.space, "unique", None)
        if LooseVersion(SHARED_CAP_API_VERSION) <= LooseVersion(
            array.get_rest_version()
        ):
            snap_info[snapshot]["snapshots_effective"] = getattr(
                snap.space, "snapshots_effective", None
            )
        if LooseVersion(SUBS_API_VERSION) <= LooseVersion(array.get_rest_version()):
            snap_info[snapshot]["total_used"] = getattr(snap.space, "total_used", None)
    offloads = list(array.get_offloads().items)
    for offload in offloads:
        offload_name = offload.name
        check_offload = array.get_remote_volume_snapshots(on=offload_name)
        if check_offload.status_code == 200:
            remote_snaps = list(
                array.get_remote_volume_snapshots(
                    on=offload_name, destroyed=False
                ).items
            )
            for remote_snap in remote_snaps:
                remote_snap_name = remote_snap.name.split(":")[1]
                remote_transfer = list(
                    array.get_remote_volume_snapshots_transfer(
                        on=offload_name, names=[remote_snap]
                    ).items
                )[0]
                remote_dict = {
                    "source": remote_snap.source.name,
                    "suffix": remote_snap.suffix,
                    "size": remote_snap.provisioned,
                    "data_transferred": remote_transfer.data_transferred,
                    "completed": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.gmtime(remote_transfer.completed / 1000),
                    )
                    + " UTC",
                    "physical_bytes_written": remote_transfer.physical_bytes_written,
                    "progress": remote_transfer.progress,
                    "created": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.gmtime(remote_snap.created / 1000),
                    )
                    + " UTC",
                }
                try:
                    snap_info[remote_snap_name]["remote"].append(remote_dict)
                except KeyError:
                    snap_info[remote_snap_name] = {"remote": []}
                    snap_info[remote_snap_name]["remote"].append(remote_dict)
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        snaps_tags = list(
            array.get_volume_snapshots_tags(resource_destroyed=False).items
        )
        for snap_tag in snaps_tags:
            snap_info[snap_tag.resource.name]["tags"].append(
                {
                    "key": snap_tag.key,
                    "value": snap_tag.value,
                    "copyable": snap_tag.copyable,
                    "namespace": snap_tag.namespace,
                }
            )
    return snap_info


def generate_del_snap_dict(array):
    snap_info = {}
    snaps = list(array.get_volume_snapshots(destroyed=True).items)
    for snap in snaps:
        snapshot = snap.name
        snap_info[snapshot] = {
            "size": getattr(snap.space, "total_provisioned", None),
            "source": getattr(snap.source, "name", None),
            "created_epoch": snap.created,
            "created": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(snap.created / 1000)
            ),
            "tags": [],
            "is_local": True,
            "remote": [],
            "time_remaining": getattr(snap, "time_remaining", None),
        }
        snap_info[snapshot]["snapshot_space"] = getattr(snap.space, "snapshots", None)
        snap_info[snapshot]["used_provisioned"] = getattr(
            snap.space, "used_provisioned", None
        )
        snap_info[snapshot]["total_physical"] = getattr(
            snap.space, "total_physical", None
        )
        snap_info[snapshot]["total_provisioned"] = getattr(
            snap.space, "total_provisioned", None
        )
        snap_info[snapshot]["unique_space"] = getattr(snap.space, "unique", None)
        if LooseVersion(SUBS_API_VERSION) <= LooseVersion(array.get_rest_version()):
            snap_info[snapshot]["total_used"] = getattr(snap.space, "total_used", None)
    offloads = list(array.get_offloads().items)
    for offload in offloads:
        offload_name = offload.name
        check_offload = array.get_remote_volume_snapshots(on=offload_name)
        if check_offload.status_code == 200:
            remote_snaps = list(
                array.get_remote_volume_snapshots(on=offload_name, destroyed=True).items
            )
            for remote_snap in remote_snaps:
                remote_snap_name = remote_snap.name.split(":")[1]
                remote_transfer = list(
                    array.get_remote_volume_snapshots_transfer(
                        on=offload_name, names=[remote_snap.name]
                    ).items
                )[0]
                remote_dict = {
                    "source": remote_snap.source.name,
                    "suffix": remote_snap.suffix,
                    "size": remote_snap.provisioned,
                    "data_transferred": remote_transfer.data_transferred,
                    "completed": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.gmtime(remote_transfer.completed / 1000),
                    )
                    + " UTC",
                    "physical_bytes_written": remote_transfer.physical_bytes_written,
                    "progress": remote_transfer.progress,
                    "created": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.gmtime(remote_snap.created / 1000),
                    )
                    + " UTC",
                }
                try:
                    snap_info[remote_snap_name]["remote"].append(remote_dict)
                except KeyError:
                    snap_info[remote_snap_name] = {"remote": []}
                    snap_info[remote_snap_name]["remote"].append(remote_dict)
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        snaps_tags = list(
            array.get_volume_snapshots_tags(resource_destroyed=True).items
        )
        for snap_tag in snaps_tags:
            snap_info[snap_tag.resource.name]["tags"].append(
                {
                    "key": snap_tag.key,
                    "value": snap_tag.value,
                    "copyable": snap_tag.copyable,
                    "namespace": snap_tag.namespace,
                }
            )
    return snap_info


def generate_del_vol_dict(array):
    volume_info = {}
    vols = list(array.get_volumes(destroyed=True).items)
    for vol in vols:
        volume = vol.name
        volume_info[volume] = {
            "protocol_endpoint": bool(vol.subtype == "protocol_endpoint"),
            "protocol_endpoint_version": getattr(
                getattr(vol, "protocol_endpoint", None),
                "container_version",
                None,
            ),
            "size": vol.provisioned,
            "source": getattr(vol.source, "name", None),
            "created_epoch": vol.created,
            "created": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(vol.created / 1000)
            ),
            "serial": vol.serial,
            "page83_naa": PURE_OUI + vol.serial,
            "nvme_nguid": "eui.00"
            + vol.serial[0:14].lower()
            + "24a937"
            + vol.serial[-10:].lower(),
            "time_remaining": vol.time_remaining,
            "tags": [],
            "promotion_status": vol.promotion_status,
            "requested_promotion_state": vol.requested_promotion_state,
            "bandwidth": getattr(vol.qos, "bandwidth_limit", None),
            "iops_limit": getattr(vol.qos, "iops_limit", None),
            "snapshots_space": getattr(vol.space, "snapshots", None),
            # Provide system as this matches the old naming convention
            "system": getattr(vol.space, "unique", None),
            "unique_space": getattr(vol.space, "unique", None),
            "virtual_space": getattr(vol.space, "virtual", None),
            "total_physical_space": getattr(vol.space, "total_physical", None),
            "data_reduction": getattr(vol.space, "data_reduction", None),
            "total_reduction": getattr(vol.space, "total_reduction", None),
            "total_provisioned": getattr(vol.space, "total_provisioned", None),
            "thin_provisioning": getattr(vol.space, "thin_provisioning", None),
            "host_encryption_key_status": vol.host_encryption_key_status,
            "subtype": vol.subtype,
        }
        if LooseVersion(SAFE_MODE_VERSION) <= LooseVersion(array.get_rest_version()):
            volume_info[volume]["subtype"] = vol.subtype
            volume_info[volume]["priority"] = vol.priority
            volume_info[volume]["priority_adjustment"] = (
                vol.priority_adjustment.priority_adjustment_operator
                + str(vol.priority_adjustment.priority_adjustment_value)
            )
        if LooseVersion(SHARED_CAP_API_VERSION) <= LooseVersion(
            array.get_rest_version()
        ):
            volume_info[volume]["snapshots_effective"] = getattr(
                vol.space, "snapshots_effective", None
            )
            volume_info[volume]["unique_effective"] = getattr(
                vol.space, "unique_effective", None
            )
            volume_info[volume]["total_effective"] = getattr(
                vol.space, "total_effective", None
            )
            volume_info[volume]["used_provisioned"] = getattr(
                vol.space, "used_provisioned", None
            )
        if LooseVersion(SUBS_API_VERSION) <= LooseVersion(array.get_rest_version()):
            volume_info[volume]["total_used"] = getattr(vol.space, "total_used", None)
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        volume_tags = list(array.get_volumes_tags(resource_destroyed=True).items)
        for volume_tag in volume_tags:
            volume_info[volume_tag.resource.name]["tags"].append(
                {
                    "key": volume_tag.key,
                    "value": volume_tag.value,
                    "copyable": volume_tag.copyable,
                    "namespace": volume_tag.namespace,
                }
            )
    return volume_info


def generate_vol_dict(array, performance):
    volume_info = {}
    vols = list(array.get_volumes(destroyed=False).items)
    for vol in vols:
        volume = vol.name
        volume_info[volume] = {
            "protocol_endpoint": bool(vol.subtype == "protocol_endpoint"),
            "protocol_endpoint_version": getattr(
                getattr(vol, "protocol_endpoint", None), "container_version", None
            ),
            "size": vol.provisioned,
            "source": getattr(vol.source, "name", None),
            "created_epoch": vol.created,
            "created": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(vol.created / 1000)
            ),
            "serial": vol.serial,
            "page83_naa": PURE_OUI + vol.serial,
            "nvme_nguid": "eui.00"
            + vol.serial[0:14].lower()
            + "24a937"
            + vol.serial[-10:].lower(),
            "tags": [],
            "promotion_status": vol.promotion_status,
            "requested_promotion_state": vol.requested_promotion_state,
            "hosts": [],
            "host_groups": [],
            "bandwidth": getattr(vol.qos, "bandwidth_limit", None),
            "iops_limit": getattr(vol.qos, "iops_limit", None),
            "snapshots_space": getattr(vol.space, "snapshots", None),
            # Provide system as this matches the old naming convention
            "system": getattr(vol.space, "unique", None),
            "unique_space": getattr(vol.space, "unique", None),
            "virtual_space": getattr(vol.space, "virtual", None),
            "total_physical_space": getattr(vol.space, "total_physical", None),
            "data_reduction": getattr(vol.space, "data_reduction", None),
            "total_reduction": getattr(vol.space, "total_reduction", None),
            "total_provisioned": getattr(vol.space, "total_provisioned", None),
            "thin_provisioning": getattr(vol.space, "thin_provisioning", None),
            "performance": [],
            "host_encryption_key_status": vol.host_encryption_key_status,
            "subtype": vol.subtype,
        }
        if LooseVersion(SHARED_CAP_API_VERSION) <= LooseVersion(
            array.get_rest_version()
        ):
            volume_info[volume]["snapshots_effective"] = getattr(
                vol.space, "snapshots_effective", None
            )
            volume_info[volume]["unique_effective"] = getattr(
                vol.space, "unique_effective", None
            )
            volume_info[volume]["total_effective"] = getattr(
                vol.space, "total_effective", None
            )
            volume_info[volume]["used_provisioned"] = getattr(
                vol.space, "used_provisioned", None
            )
        if LooseVersion(SUBS_API_VERSION) <= LooseVersion(array.get_rest_version()):
            volume_info[volume]["total_used"] = getattr(vol.space, "total_used", None)
        if LooseVersion(SAFE_MODE_VERSION) <= LooseVersion(array.get_rest_version()):
            volume_info[volume]["priority"] = vol.priority
            volume_info[volume]["priority_adjustment"] = (
                vol.priority_adjustment.priority_adjustment_operator
                + str(vol.priority_adjustment.priority_adjustment_value)
            )
        connections = list(array.get_connections(volume_names=[vol.name]).items)
        voldict = {}
        for connection in connections:
            voldict = {
                "host": getattr(connection.host, "name", None),
                "lun": getattr(connection, "lun", None),
            }
            if voldict["host"]:
                volume_info[volume]["hosts"].append(voldict)
        voldict = {}
        for connection in connections:
            voldict = {
                "host_group": getattr(connection.host_group, "name", None),
                "lun": getattr(connection, "lun", None),
            }
            if voldict["host_group"]:
                volume_info[volume]["host_groups"].append(voldict)
        volume_info[volume]["host_groups"] = [
            dict(t)
            for t in set(tuple(d.items()) for d in volume_info[volume]["host_groups"])
        ]
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        volume_tags = list(array.get_volumes_tags(resource_destroyed=False).items)
        for volume_tag in volume_tags:
            volume_info[volume_tag.resource.name]["tags"].append(
                {
                    "key": volume_tag.key,
                    "value": volume_tag.value,
                    "copyable": volume_tag.copyable,
                    "namespace": volume_tag.namespace,
                }
            )
    if performance:
        vols_performance = list(array.get_volumes_performance(destroyed=False).items)
        for perf in vols_performance:
            if perf.name in volume_info:
                volume_info[perf.name]["performance"] = {
                    "bytes_per_mirrored_write": perf.bytes_per_mirrored_write,
                    "bytes_per_op": perf.bytes_per_op,
                    "bytes_per_read": perf.bytes_per_read,
                    "bytes_per_write": perf.bytes_per_write,
                    "mirrored_write_bytes_per_sec": perf.mirrored_write_bytes_per_sec,
                    "mirrored_writes_per_sec": perf.mirrored_writes_per_sec,
                    "qos_rate_limit_usec_per_mirrored_write_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_read_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_write_op": perf.qos_rate_limit_usec_per_read_op,
                    "queue_usec_per_mirrored_write_op": perf.queue_usec_per_mirrored_write_op,
                    "queue_usec_per_read_op": perf.queue_usec_per_read_op,
                    "queue_usec_per_write_op": perf.queue_usec_per_write_op,
                    "read_bytes_per_sec": perf.read_bytes_per_sec,
                    "reads_per_sec": perf.reads_per_sec,
                    "san_usec_per_mirrored_write_op": perf.san_usec_per_mirrored_write_op,
                    "san_usec_per_read_op": perf.san_usec_per_read_op,
                    "san_usec_per_write_op": perf.san_usec_per_write_op,
                    "service_usec_per_mirrored_write_op": perf.service_usec_per_mirrored_write_op,
                    "service_usec_per_read_op": perf.service_usec_per_read_op,
                    "service_usec_per_write_op": perf.service_usec_per_write_op,
                    "usec_per_mirrored_write_op": perf.usec_per_mirrored_write_op,
                    "usec_per_read_op": perf.usec_per_read_op,
                    "usec_per_write_op": perf.usec_per_write_op,
                    "write_bytes_per_sec": perf.write_bytes_per_sec,
                    "writes_per_sec": perf.writes_per_sec,
                }
    return volume_info


def generate_host_dict(array, performance):
    host_info = {}
    hosts = list(array.get_hosts().items)
    hosts_balance = list(array.get_hosts_performance_balance().items)
    if performance:
        hosts_performance = list(array.get_hosts_performance().items)
    # Build a live login map (initiator identifier -> set of array target port
    # names) so each host WWN/IQN/NQN can report exactly where it is logged in.
    login_map = {}
    for login in list(array.get_ports_initiators().items):
        target_name = getattr(login.target, "name", None)
        if not target_name:
            continue
        initiator = login.initiator
        init_wwn = getattr(initiator, "wwn", None)
        for key in (
            init_wwn.replace(":", "").upper() if init_wwn else None,
            getattr(initiator, "iqn", None),
            getattr(initiator, "nqn", None),
        ):
            if key:
                login_map.setdefault(key, set()).add(target_name)
    for host in hosts:
        hostname = host.name
        host_info[hostname] = {
            "hgroup": getattr(host.host_group, "name", None),
            "nqn": getattr(host, "nqns", None),
            "iqn": getattr(host, "iqns", None),
            "wwn": getattr(host, "wwns", None),
            "personality": getattr(host, "personality", None),
            "host_user": getattr(host.chap, "host_user", None),
            "target_user": getattr(host.chap, "target_user", None),
            "target_port": [],
            "logged_in_ports": {},
            "volumes": [],
            "tags": [],
            "performance": [],
            "performance_balance": [],
            "preferred_array": [],
            "destroyed": getattr(host, "destroyed", None),
            "time_remaining": getattr(host, "time_remaining", None),
            "vlan": getattr(host, "vlan", None),
        }
        # Report which array target ports each host initiator is logged into.
        # An empty list means the identifier is not logged into any port, so
        # the WWN/IQN/NQN can be safely removed.
        logged_in = {}
        for wwn in getattr(host, "wwns", None) or []:
            logged_in[wwn] = sorted(login_map.get(wwn.replace(":", "").upper(), []))
        for iqn in getattr(host, "iqns", None) or []:
            logged_in[iqn] = sorted(login_map.get(iqn, []))
        for nqn in getattr(host, "nqns", None) or []:
            logged_in[nqn] = sorted(login_map.get(nqn, []))
        host_info[hostname]["logged_in_ports"] = logged_in
        host_connections = list(array.get_connections(host_names=[hostname]).items)
        for connection in host_connections:
            # LOCAL WORKAROUND - DO NOT COMMIT, see generate_workload_dict.
            # connection.host_group and connection.volume are both optional, so
            # reading through them unguarded raises rather than returning None.
            connection_dict = {
                "hostgroup": getattr(
                    getattr(connection, "host_group", None), "name", None
                ),
                "volume": getattr(getattr(connection, "volume", None), "name", None),
                "lun": getattr(connection, "lun", None),
                "nsid": getattr(connection, "nsid", None),
            }
            host_info[hostname]["volumes"].append(connection_dict)
        for pref_array in host.preferred_arrays:
            # preferred_arrays is a list of Reference objects, not a dict
            host_info[hostname]["preferred_array"].append(pref_array.name)

        if host.is_local:
            host_info[host.name]["port_connectivity"] = host.port_connectivity.details
            host_perf_balance = []
            for balance in hosts_balance:
                if host.name == balance.name:
                    host_balance = {
                        "fraction_relative_to_max": getattr(
                            balance,
                            "fraction_relative_to_max",
                            None,
                        ),
                        "op_count": getattr(balance, "op_count", 0),
                        "target": getattr(balance.target, "name", None),
                        "failed": bool(getattr(balance.target, "failover", 0)),
                    }
                    if host_balance["target"]:
                        host_perf_balance.append(host_balance)
                    host_info[hostname]["target_port"].append(
                        getattr(balance.target, "name", None)
                    )
            host_info[host.name]["performance_balance"].append(host_perf_balance)
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        host_tags = list(array.get_hosts_tags(resource_destroyed=False).items)
        for tag in host_tags:
            host_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    if performance:
        for perf in hosts_performance:
            if ":" not in perf.name:
                host_info[perf.name]["performance"] = {
                    "bytes_per_mirrored_write": perf.bytes_per_mirrored_write,
                    "bytes_per_op": perf.bytes_per_op,
                    "bytes_per_read": perf.bytes_per_read,
                    "bytes_per_write": perf.bytes_per_write,
                    "mirrored_write_bytes_per_sec": perf.mirrored_write_bytes_per_sec,
                    "mirrored_writes_per_sec": perf.mirrored_writes_per_sec,
                    "qos_rate_limit_usec_per_mirrored_write_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_read_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_write_op": perf.qos_rate_limit_usec_per_read_op,
                    "queue_usec_per_mirrored_write_op": perf.queue_usec_per_mirrored_write_op,
                    "queue_usec_per_read_op": perf.queue_usec_per_read_op,
                    "queue_usec_per_write_op": perf.queue_usec_per_write_op,
                    "read_bytes_per_sec": perf.read_bytes_per_sec,
                    "reads_per_sec": perf.reads_per_sec,
                    "san_usec_per_mirrored_write_op": perf.san_usec_per_mirrored_write_op,
                    "san_usec_per_read_op": perf.san_usec_per_read_op,
                    "san_usec_per_write_op": perf.san_usec_per_write_op,
                    "service_usec_per_mirrored_write_op": perf.service_usec_per_mirrored_write_op,
                    "service_usec_per_read_op": perf.service_usec_per_read_op,
                    "service_usec_per_write_op": perf.service_usec_per_write_op,
                    "usec_per_mirrored_write_op": perf.usec_per_mirrored_write_op,
                    "usec_per_read_op": perf.usec_per_read_op,
                    "usec_per_write_op": perf.usec_per_write_op,
                    "write_bytes_per_sec": perf.write_bytes_per_sec,
                    "writes_per_sec": perf.writes_per_sec,
                }
    return host_info


def generate_del_pgroups_dict(array):
    pgroups_info = {}
    api_version = array.get_rest_version()
    pgroups = list(array.get_protection_groups(destroyed=True).items)
    for pgroup in pgroups:
        protgroup = pgroup.name

        pgroups_info[protgroup] = {
            "hgroups": [],
            "hosts": [],
            "source": getattr(pgroup.source, "name", None),
            "targets": [],
            "volumes": [],
            "time_remaining": pgroup.time_remaining,
            "snap_frequency": pgroup.snapshot_schedule.frequency,
            "replicate_frequency": pgroup.replication_schedule.frequency,
            "snap_enabled": pgroup.snapshot_schedule.enabled,
            "replicate_enabled": pgroup.replication_schedule.enabled,
            "snap_at": getattr(pgroup.snapshot_schedule, "at", None),
            "replicate_at": getattr(pgroup.replication_schedule, "at", None),
            "replicate_blackout": {
                "start": getattr(pgroup.replication_schedule.blackout, "start", None),
                "end": getattr(pgroup.replication_schedule.blackout, "end", None),
            },
            "per_day": pgroup.source_retention.per_day,
            "target_per_day": pgroup.target_retention.per_day,
            "target_days": pgroup.target_retention.days,
            "days": pgroup.source_retention.days,
            "all_for": pgroup.source_retention.all_for_sec,
            "target_all_for": pgroup.target_retention.all_for_sec,
            "snaps": {},
            "snapshots": getattr(pgroup.space, "snapshots", None),
            "shared": getattr(pgroup.space, "shared", None),
            "data_reduction": getattr(pgroup.space, "data_reduction", None),
            "thin_provisioning": getattr(pgroup.space, "thin_provisioning", None),
            "total_physical": getattr(pgroup.space, "total_physical", None),
            "total_provisioned": getattr(pgroup.space, "total_provisioned", None),
            "total_reduction": getattr(pgroup.space, "total_reduction", None),
            "unique": getattr(pgroup.space, "unique", None),
            "virtual": getattr(pgroup.space, "virtual", None),
            "replication": getattr(pgroup.space, "replication", None),
            "used_provisioned": getattr(pgroup.space, "used_provisioned", None),
            "tags": [],
        }
        pgroup_transfers_res = array.get_protection_group_snapshots_transfer(
            names=[protgroup + ".*"]
        )
        if pgroup_transfers_res.status_code == 200:
            pgroup_transfers = list(pgroup_transfers_res.items)
            for pgroup_transfer in pgroup_transfers:
                snap = pgroup_transfer.name
                pgroups_info[protgroup]["snaps"][snap] = {
                    "time_remaining": None,  # Backwards compatibility
                    "created": None,  # Backwards compatibility
                    "started": getattr(pgroup_transfer, "started", None),
                    "completed": getattr(pgroup_transfer, "completed", None),
                    "physical_bytes_written": getattr(
                        pgroup_transfer,
                        "physical_bytes_written",
                        None,
                    ),
                    "data_transferred": getattr(
                        pgroup_transfer, "data_transferred", None
                    ),
                    "progress": getattr(pgroup_transfer, "progress", None),
                    "destroyed": pgroup_transfer.destroyed,
                }
        pgroup_volumes = list(
            array.get_protection_groups_volumes(group_names=[protgroup]).items
        )
        for pg_vol in pgroup_volumes:
            pgroups_info[protgroup]["volumes"].append(pg_vol.member.name)
        pgroup_hosts = list(
            array.get_protection_groups_hosts(group_names=[protgroup]).items
        )
        for pg_host in pgroup_hosts:
            pgroups_info[protgroup]["hosts"].append(pg_host.member.name)
        pgroup_hgs = list(
            array.get_protection_groups_host_groups(group_names=[protgroup]).items
        )
        for pg_hg in pgroup_hgs:
            pgroups_info[protgroup]["hgroups"].append(pg_hg.member.name)
        pgroup_targets = list(
            array.get_protection_groups_targets(group_names=[protgroup]).items
        )
        for pg_target in pgroup_targets:
            pgroups_info[protgroup]["targets"].append(pg_target.member.name)
        if LooseVersion(SHARED_CAP_API_VERSION) <= LooseVersion(api_version):
            pgroups_info[protgroup]["deleted_volumes"] = []
            volumes = list(
                array.get_protection_groups_volumes(group_names=[protgroup]).items
            )
            if volumes:
                for volume in volumes:
                    if volume.member.destroyed:
                        pgroups_info[protgroup]["deleted_volumes"].append(
                            volume.member.name
                        )
            else:
                pgroups_info[protgroup]["deleted_volumes"] = None
        if LooseVersion(PER_PG_VERSION) <= LooseVersion(api_version):
            res = array.get_protection_groups(names=[protgroup])
            if res.status_code == 200:
                pg_info = list(res.items)[0]
                pgroups_info[protgroup]["retention_lock"] = getattr(
                    pg_info, "retention_lock", None
                )
                pgroups_info[protgroup]["manual_eradication"] = getattr(
                    pg_info.eradication_config, "manual_eradication", None
                )
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        pgroup_tags = list(
            array.get_protection_groups_tags(resource_destroyed=True).items
        )
        for tag in pgroup_tags:
            pgroups_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    return pgroups_info


def generate_pgroups_dict(array):
    pgroups_info = {}
    api_version = array.get_rest_version()
    pgroups = list(array.get_protection_groups(destroyed=False).items)
    for pgroup in pgroups:
        protgroup = pgroup.name
        pgroups_info[protgroup] = {
            "hgroups": [],
            "hosts": [],
            "source": getattr(pgroup.source, "name", None),
            "targets": [],
            "volumes": [],
            "snap_frequency": pgroup.snapshot_schedule.frequency,
            "replicate_frequency": pgroup.replication_schedule.frequency,
            "snap_enabled": pgroup.snapshot_schedule.enabled,
            "replicate_enabled": pgroup.replication_schedule.enabled,
            "snap_at": getattr(pgroup.snapshot_schedule, "at", None),
            "replicate_at": getattr(pgroup.replication_schedule, "at", None),
            "replicate_blackout": {
                "start": getattr(pgroup.replication_schedule.blackout, "start", None),
                "end": getattr(pgroup.replication_schedule.blackout, "end", None),
            },
            "per_day": pgroup.source_retention.per_day,
            "target_per_day": pgroup.target_retention.per_day,
            "target_days": pgroup.target_retention.days,
            "days": pgroup.source_retention.days,
            "all_for": pgroup.source_retention.all_for_sec,
            "target_all_for": pgroup.target_retention.all_for_sec,
            "snaps": {},
            "snapshots": getattr(pgroup.space, "snapshots", None),
            "shared": getattr(pgroup.space, "shared", None),
            "data_reduction": getattr(pgroup.space, "data_reduction", None),
            "thin_provisioning": getattr(pgroup.space, "thin_provisioning", None),
            "total_physical": getattr(pgroup.space, "total_physical", None),
            "total_provisioned": getattr(pgroup.space, "total_provisioned", None),
            "total_reduction": getattr(pgroup.space, "total_reduction", None),
            "unique": getattr(pgroup.space, "unique", None),
            "virtual": getattr(pgroup.space, "virtual", None),
            "replication": getattr(pgroup.space, "replication", None),
            "used_provisioned": getattr(pgroup.space, "used_provisioned", None),
            "tags": [],
        }
        pgroup_transfers_res = array.get_protection_group_snapshots_transfer(
            names=[protgroup + ".*"]
        )
        if pgroup_transfers_res.status_code == 200:
            pgroup_transfers = list(pgroup_transfers_res.items)
            for pgroup_transfer in pgroup_transfers:
                snap = pgroup_transfer.name
                pgroups_info[protgroup]["snaps"][snap] = {
                    "time_remaining": None,  # Backwards compatibility
                    "created": None,  # Backwards compatibility
                    "started": getattr(pgroup_transfer, "started", None),
                    "completed": getattr(pgroup_transfer, "completed", None),
                    "physical_bytes_written": getattr(
                        pgroup_transfer,
                        "physical_bytes_written",
                        None,
                    ),
                    "data_transferred": getattr(
                        pgroup_transfer, "data_transferred", None
                    ),
                    "progress": getattr(pgroup_transfer, "progress", None),
                    "destroyed": pgroup_transfer.destroyed,
                }
        pgroup_volumes = list(
            array.get_protection_groups_volumes(group_names=[protgroup]).items
        )
        for pg_vol in pgroup_volumes:
            pgroups_info[protgroup]["volumes"].append(pg_vol.member.name)
        pgroup_hosts = list(
            array.get_protection_groups_hosts(group_names=[protgroup]).items
        )
        for pg_host in pgroup_hosts:
            pgroups_info[protgroup]["hosts"].append(pg_host.member.name)
        pgroup_hgs = list(
            array.get_protection_groups_host_groups(group_names=[protgroup]).items
        )
        for pg_hg in pgroup_hgs:
            pgroups_info[protgroup]["hgroups"].append(pg_hg.member.name)
        pgroup_targets = list(
            array.get_protection_groups_targets(group_names=[protgroup]).items
        )
        for pg_target in pgroup_targets:
            pgroups_info[protgroup]["targets"].append(pg_target.member.name)
        if LooseVersion(SHARED_CAP_API_VERSION) <= LooseVersion(api_version):
            pgroups_info[protgroup]["deleted_volumes"] = []
            volumes = list(
                array.get_protection_groups_volumes(group_names=[protgroup]).items
            )
            if volumes:
                for volume in volumes:
                    if volume.member.destroyed:
                        pgroups_info[protgroup]["deleted_volumes"].append(
                            volume.member.name
                        )
            else:
                pgroups_info[protgroup]["deleted_volumes"] = None
        if LooseVersion(PER_PG_VERSION) <= LooseVersion(api_version):
            res = array.get_protection_groups(names=[protgroup])
            if res.status_code == 200:
                pg_info = list(res.items)[0]
                pgroups_info[protgroup]["retention_lock"] = getattr(
                    pg_info, "retention_lock", None
                )
                pgroups_info[protgroup]["manual_eradication"] = getattr(
                    pg_info.eradication_config, "manual_eradication", None
                )
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        pgroup_tags = list(
            array.get_protection_groups_tags(resource_destroyed=False).items
        )
        for tag in pgroup_tags:
            pgroups_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    return pgroups_info


def generate_rl_dict(array):
    rl_info = {}
    lag = None
    rlinks = list(array.get_pod_replica_links().items)
    for rlink in rlinks:
        link_name = rlink.local_pod.name
        if hasattr(rlinks, "recovery_point"):
            since_epoch = rlink.recovery_point / 1000
            recovery_datatime = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(since_epoch)
            )
        else:
            recovery_datatime = None
        if hasattr(rlink, "lag"):
            lag = str(rlink.lag / 1000) + "s"
        rl_info[link_name] = {
            "status": rlink.status,
            "direction": rlink.direction,
            "lag": lag,
            "remote_pod_name": rlink.remote_pod.name,
            "remote_names": rlink.remotes[0].name,
            "recovery_point": recovery_datatime,
        }
    return rl_info


def generate_del_pods_dict(array):
    pods_info = {}
    pods = list(array.get_pods(destroyed=True).items)
    for pod in pods:
        name = pod.name
        pods_info[name] = {
            "arrays": [],
            "mediator": pod.mediator,
            "mediator_version": getattr(pod, "mediator_version", None),
            "time_remaining": pod.time_remaining,
            "link_source_count": pod.link_source_count,
            "link_target_count": pod.link_target_count,
            "promotion_status": pod.promotion_status,
            "requested_promotion_state": pod.requested_promotion_state,
            "failover_preference": [],
            "snapshots": getattr(pod.space, "snapshots", None),
            "shared": getattr(pod.space, "shared", None),
            "data_reduction": getattr(pod.space, "data_reduction", None),
            "thin_provisioning": getattr(pod.space, "thin_provisioning", None),
            "total_physical": getattr(pod.space, "total_physical", None),
            "total_provisioned": getattr(pod.space, "total_provisioned", None),
            "total_reduction": getattr(pod.space, "total_reduction", None),
            "unique": getattr(pod.space, "unique", None),
            "virtual": getattr(pod.space, "virtual", None),
            "replication": getattr(pod.space, "replication", None),
            "used_provisioned": getattr(pod.space, "used_provisioned", None),
            "quota_limit": getattr(pod, "quota_limit", None),
            "total_used": getattr(pod.space, "total_used", None),
            "tags": [],
        }
        for preferences in pod.failover_preferences:
            pods_info[name]["failover_preference"].append(
                {
                    "array_id": preferences.id,
                    "name": preferences.name,
                }
            )
        for pod_array in pod.arrays:
            frozen_datetime = None
            if hasattr(pod_array, "frozen_at"):
                frozen_time = pod_array.frozen_at / 1000
                frozen_datetime = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(frozen_time)
                )
            pods_info[name]["arrays"].append(
                {
                    "name": pod_array.member.name,
                    "type": pod_array.member.resource_type,
                    "pre_elected": getattr(pod_array, "pre_elected", False),
                    "frozen_at": frozen_datetime,
                    "progress": getattr(pod_array, "progress", None),
                    "status": getattr(pod_array, "status", None),
                }
            )
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        pods_tags = list(array.get_pods_tags(resource_destroyed=True).items)
        for tag in pods_tags:
            pods_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    return pods_info


def generate_pods_dict(array, performance):
    pods_info = {}
    pods = list(array.get_pods(destroyed=False).items)
    for pod in pods:
        name = pod.name
        pods_info[name] = {
            "arrays": [],
            "mediator": pod.mediator,
            "mediator_version": getattr(pod, "mediator_version", None),
            "link_source_count": pod.link_source_count,
            "link_target_count": pod.link_target_count,
            "promotion_status": pod.promotion_status,
            "requested_promotion_state": pod.requested_promotion_state,
            "failover_preference": [],
            "snapshots": getattr(pod.space, "snapshots", None),
            "shared": getattr(pod.space, "shared", None),
            "data_reduction": getattr(pod.space, "data_reduction", None),
            "thin_provisioning": getattr(pod.space, "thin_provisioning", None),
            "total_physical": getattr(pod.space, "total_physical", None),
            "total_provisioned": getattr(pod.space, "total_provisioned", None),
            "total_reduction": getattr(pod.space, "total_reduction", None),
            "unique": getattr(pod.space, "unique", None),
            "virtual": getattr(pod.space, "virtual", None),
            "replication": getattr(pod.space, "replication", None),
            "used_provisioned": getattr(pod.space, "used_provisioned", None),
            "quota_limit": getattr(pod, "quota_limit", None),
            "total_used": getattr(pod.space, "total_used", None),
            "tags": [],
            "source": getattr(pod.source, "name", None),
        }
        for preferences in pod.failover_preferences:
            pods_info[name]["failover_preference"].append(
                {
                    "array_id": preferences.id,
                    "name": preferences.name,
                }
            )
        for pod_array in pod.arrays:
            frozen_datetime = None
            if hasattr(pod_array, "frozen_at"):
                frozen_time = pod_array.frozen_at / 1000
                frozen_datetime = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(frozen_time)
                )
            pods_info[name]["arrays"].append(
                {
                    "array_id": pod_array.id,
                    "name": pod_array.member.name,
                    "type": pod_array.member.resource_type,
                    "pre_elected": pod_array.pre_elected,
                    "frozen_at": frozen_datetime,
                    "progress": getattr(pod_array, "progress", None),
                    "mediator_status": getattr(pod.arrays[0], "mediator_status", None),
                    "status": getattr(pod_array, "status", None),
                }
            )
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        pods_tags = list(array.get_pods_tags(resource_destroyed=False).items)
        for tag in pods_tags:
            pods_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    if performance:
        pods_performance = list(array.get_pods_performance().items)
        for perf in pods_performance:
            if perf.name in pods_info:
                pods_info[perf.name]["performance"] = {
                    "bytes_per_mirrored_write": perf.bytes_per_mirrored_write,
                    "bytes_per_op": perf.bytes_per_op,
                    "bytes_per_read": perf.bytes_per_read,
                    "bytes_per_write": perf.bytes_per_write,
                    "mirrored_write_bytes_per_sec": perf.mirrored_write_bytes_per_sec,
                    "mirrored_writes_per_sec": perf.mirrored_writes_per_sec,
                    "others_per_sec": perf.others_per_sec,
                    "qos_rate_limit_usec_per_mirrored_write_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_read_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_write_op": perf.qos_rate_limit_usec_per_read_op,
                    "queue_usec_per_mirrored_write_op": perf.queue_usec_per_mirrored_write_op,
                    "queue_usec_per_read_op": perf.queue_usec_per_read_op,
                    "queue_usec_per_write_op": perf.queue_usec_per_write_op,
                    "read_bytes_per_sec": perf.read_bytes_per_sec,
                    "reads_per_sec": perf.reads_per_sec,
                    "san_usec_per_mirrored_write_op": perf.san_usec_per_mirrored_write_op,
                    "san_usec_per_read_op": perf.san_usec_per_read_op,
                    "san_usec_per_write_op": perf.san_usec_per_write_op,
                    "service_usec_per_mirrored_write_op": perf.service_usec_per_mirrored_write_op,
                    "service_usec_per_read_op": perf.service_usec_per_read_op,
                    "service_usec_per_write_op": perf.service_usec_per_write_op,
                    "usec_per_mirrored_write_op": perf.usec_per_mirrored_write_op,
                    "usec_per_read_op": perf.usec_per_read_op,
                    "usec_per_write_op": perf.usec_per_write_op,
                    "write_bytes_per_sec": perf.write_bytes_per_sec,
                    "writes_per_sec": perf.writes_per_sec,
                }
    return pods_info


def generate_conn_array_dict(array):
    conn_array_info = {}
    carrays = list(array.get_array_connections().items)
    for carray in carrays:
        arrayname = carray.name
        conn_array_info[arrayname] = {
            "array_id": carray.id,
            "version": getattr(carray, "version", None),
            "status": carray.status,
            "type": carray.type,
            "mgmt_ip": getattr(carray, "management_address", "-"),
            "repl_ip": getattr(carray, "replication_addresses", "-"),
            "transport": getattr(carray, "replication_transport", "Unknown"),
            "throttling": {},
        }
        if hasattr(carray, "throttle"):
            if bool(carray.throttle.to_dict()):
                conn_array_info[arrayname]["throttled"] = True
                if hasattr(carray.throttle, "window"):
                    conn_array_info[arrayname]["throttling"][
                        "window"
                    ] = carray.throttle.window.to_dict()
                if hasattr(carray.throttle, "default_limit"):
                    conn_array_info[arrayname]["throttling"][
                        "default_limit"
                    ] = carray.throttle.default_limit
                if hasattr(carray.throttle, "window_limit"):
                    conn_array_info[arrayname]["throttling"][
                        "window_limit"
                    ] = carray.throttle.window_limit
    return conn_array_info


def generate_apps_dict(array):
    apps_info = {}
    apps = list(array.get_apps().items)
    for app in apps:
        appname = app.name
        apps_info[appname] = {
            "enabled": getattr(app, "enabled", None),
            "version": getattr(app, "version", None),
            "status": getattr(app, "status", None),
            "description": getattr(app, "description", None),
            "details": getattr(app, "details", None),
            "vnc_enabled": getattr(app, "vnc_enabled", None),
        }
    app_nodes = list(array.get_apps_nodes().items)
    for app_node in app_nodes:
        appname = app_node.name
        apps_info[appname]["index"] = app_node.index
        apps_info[appname]["vnc"] = getattr(app_node, "vnc", None)
    return apps_info


def generate_vgroups_dict(array, performance):
    vgroups_info = {}
    vgroups = list(array.get_volume_groups(destroyed=False).items)
    for vgroup in vgroups:
        name = vgroup.name
        vgroups_info[name] = {
            "volumes": [],
            "performance": [],
            "snapshots_space": getattr(vgroup.space, "snapshots", None),
            "system": getattr(vgroup.space, "unique", None),  # Backwards compatibility
            "unique_space": getattr(vgroup.space, "unique", None),
            "virtual_space": getattr(vgroup.space, "virtual", None),
            "data_reduction": getattr(vgroup.space, "data_reduction", None),
            "total_reduction": getattr(vgroup.space, "total_reduction", None),
            "total_provisioned": getattr(vgroup.space, "total_provisioned", None),
            "thin_provisioning": getattr(vgroup.space, "thin_provisioning", None),
            "used_provisioned": getattr(vgroup.space, "used_provisioned", None),
            "bandwidth_limit": getattr(vgroup.qos, "bandwidth_limit", ""),
            "iops_limit": getattr(vgroup.qos, "iops_limit", ""),
            "total_used": getattr(vgroup.space, "total_used", None),
            "tags": [],
        }
        if hasattr(vgroup, "priority_adjustment"):
            vgroups_info[name]["priority_adjustment"] = (
                vgroup.priority_adjustment.priority_adjustment_operator
                + str(vgroup.priority_adjustment.priority_adjustment_value)
            )
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        vgroup_tags = list(array.get_volume_groups_tags(resource_destroyed=False).items)
        for tag in vgroup_tags:
            vgroups_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    if performance:
        vgs_performance = list(array.get_volume_groups_performance().items)
        for perf in vgs_performance:
            if perf.name in vgroups_info:
                vgroups_info[perf.name]["performance"] = {
                    "bytes_per_mirrored_write": perf.bytes_per_mirrored_write,
                    "bytes_per_op": perf.bytes_per_op,
                    "bytes_per_read": perf.bytes_per_read,
                    "bytes_per_write": perf.bytes_per_write,
                    "mirrored_write_bytes_per_sec": perf.mirrored_write_bytes_per_sec,
                    "mirrored_writes_per_sec": perf.mirrored_writes_per_sec,
                    "qos_rate_limit_usec_per_mirrored_write_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_read_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_write_op": perf.qos_rate_limit_usec_per_read_op,
                    "queue_usec_per_mirrored_write_op": perf.queue_usec_per_mirrored_write_op,
                    "queue_usec_per_read_op": perf.queue_usec_per_read_op,
                    "queue_usec_per_write_op": perf.queue_usec_per_write_op,
                    "read_bytes_per_sec": perf.read_bytes_per_sec,
                    "reads_per_sec": perf.reads_per_sec,
                    "san_usec_per_mirrored_write_op": perf.san_usec_per_mirrored_write_op,
                    "san_usec_per_read_op": perf.san_usec_per_read_op,
                    "san_usec_per_write_op": perf.san_usec_per_write_op,
                    "service_usec_per_mirrored_write_op": perf.service_usec_per_mirrored_write_op,
                    "service_usec_per_read_op": perf.service_usec_per_read_op,
                    "service_usec_per_write_op": perf.service_usec_per_write_op,
                    "usec_per_mirrored_write_op": perf.usec_per_mirrored_write_op,
                    "usec_per_read_op": perf.usec_per_read_op,
                    "usec_per_write_op": perf.usec_per_write_op,
                    "write_bytes_per_sec": perf.write_bytes_per_sec,
                    "writes_per_sec": perf.writes_per_sec,
                }
    vg_volumes = list(array.get_volume_groups_volumes().items)
    for vg_vol in vg_volumes:
        group_name = vg_vol.group.name
        vgroups_info[group_name]["volumes"].append(vg_vol.member.name)
    return vgroups_info


def generate_del_vgroups_dict(array):
    vgroups_info = {}
    vgroups = list(array.get_volume_groups(destroyed=True).items)
    for vgroup in vgroups:
        name = vgroup.name
        vgroups_info[name] = {
            "volumes": [],
            "performance": [],
            "snapshots_space": getattr(vgroup.space, "snapshots", None),
            "system": getattr(vgroup.space, "unique", None),  # Backwards compatibility
            "unique_space": getattr(vgroup.space, "unique", None),
            "virtual_space": getattr(vgroup.space, "virtual", None),
            "data_reduction": getattr(vgroup.space, "data_reduction", None),
            "total_reduction": getattr(vgroup.space, "total_reduction", None),
            "total_provisioned": getattr(vgroup.space, "total_provisioned", None),
            "thin_provisioning": getattr(vgroup.space, "thin_provisioning", None),
            "used_provisioned": getattr(vgroup.space, "used_provisioned", None),
            "bandwidth_limit": getattr(vgroup.qos, "bandwidth_limit", ""),
            "iops_limit": getattr(vgroup.qos, "iops_limit", ""),
            "total_used": getattr(vgroup.space, "total_used", None),
            "tags": [],
        }
        if hasattr(vgroup, "priority_adjustment"):
            vgroups_info[name]["priority_adjustment"] = (
                vgroup.priority_adjustment.priority_adjustment_operator
                + str(vgroup.priority_adjustment.priority_adjustment_value)
            )
    vg_volumes = list(array.get_volume_groups_volumes().items)
    for vg_vol in vg_volumes:
        group_name = vg_vol.group.name
        if group_name in vgroups_info:
            vgroups_info[group_name]["volumes"].append(vg_vol.member.name)
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        vgroup_tags = list(array.get_volume_groups_tags(resource_destroyed=True).items)
        for tag in vgroup_tags:
            vgroups_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    return vgroups_info


def generate_certs_dict(array):
    certs_info = {}
    certs = list(array.get_certificates().items)
    for cert in certs:
        certificate = cert.name
        valid_from = time.strftime(
            "%a, %d %b %Y %H:%M:%S %Z",
            time.localtime(cert.valid_from / 1000),
        )
        valid_to = time.strftime(
            "%a, %d %b %Y %H:%M:%S %Z",
            time.localtime(cert.valid_to / 1000),
        )
        certs_info[certificate] = {
            "status": cert.status,
            "issued_to": getattr(cert, "issued_to", None),
            "valid_from": valid_from,
            "locality": getattr(cert, "locality", None),
            "country": getattr(cert, "country", None),
            "issued_by": getattr(cert, "issued_by", None),
            "valid_to": valid_to,
            "state": getattr(cert, "state", None),
            "key_algorithm": getattr(cert, "key_algorithm", None),
            "key_size": getattr(cert, "key_size", None),
            "org_unit": getattr(cert, "organizational_unit", None),
            "common_name": getattr(cert, "common_name", None),
            "organization": getattr(cert, "organization", None),
            "email": getattr(cert, "email", None),
            "certificate_type": getattr(cert, "certificate_type", None),
            "alternative_names": getattr(cert, "subject_alternative_names", None),
        }
    return certs_info


def generate_kmip_dict(array):
    kmip_info = {}
    kmips = list(array.get_kmip().items)
    for kmip in kmips:
        key = kmip.name
        kmip_info[key] = {
            "certificate": kmip.certificate.name,
            "ca_certificate": getattr(kmip, "ca_certificate", None),
            "ca_cert_configured": True,
            "uri": kmip.uris,
        }
    return kmip_info


def generate_nfs_offload_dict(array):
    offload_info = {}
    offloads_res = array.get_offloads(protocol="nfs")
    if offloads_res.status_code == 200:
        offloads = list(offloads_res.items)
        for offload in offloads:
            name = offload.name
            offload_info[name] = {
                "status": offload.status,
                "mount_point": getattr(offload.nfs, "mount_point", None),
                "protocol": offload.protocol,
                "profile": getattr(offload.nfs, "profile", None),
                "mount_options": getattr(offload.nfs, "mount_options", None),
                "address": getattr(offload.nfs, "address", None),
                "snapshots": getattr(offload.space, "snapshots", None),
                "shared": getattr(offload.space, "shared", None),
                "data_reduction": getattr(offload.space, "data_reduction", None),
                "thin_provisioning": getattr(offload.space, "thin_provisioning", None),
                "total_physical": getattr(offload.space, "total_physical", None),
                "total_provisioned": getattr(offload.space, "total_provisioned", None),
                "total_reduction": getattr(offload.space, "total_reduction", None),
                "unique": getattr(offload.space, "unique", None),
                "virtual": getattr(offload.space, "virtual", None),
                "replication": getattr(offload.space, "replication", None),
                "used_provisioned": getattr(offload.space, "used_provisioned", None),
                "total_used": getattr(offload.space, "total_used", None),
            }
    return offload_info


def generate_s3_offload_dict(array):
    offload_info = {}
    offloads_res = array.get_offloads(protocol="s3")
    if offloads_res.status_code == 200:
        offloads = list(offloads_res.items)
        for offload in offloads:
            name = offload.name
            offload_info[name] = {
                "status": offload.status,
                "bucket": getattr(offload.s3, "bucket", None),
                "protocol": offload.protocol,
                "uri": getattr(offload.s3, "uri", None),
                "auth_region": getattr(offload.s3, "auth_region", None),
                "profile": getattr(offload.s3, "profile", None),
                "access_key_id": getattr(offload.s3, "access_key_id", None),
                "placement_strategy": offload.s3.placement_strategy,
                "snapshots": getattr(offload.space, "snapshots", None),
                "shared": getattr(offload.space, "shared", None),
                "data_reduction": getattr(offload.space, "data_reduction", None),
                "thin_provisioning": getattr(offload.space, "thin_provisioning", None),
                "total_physical": getattr(offload.space, "total_physical", None),
                "total_provisioned": getattr(offload.space, "total_provisioned", None),
                "total_reduction": getattr(offload.space, "total_reduction", None),
                "unique": getattr(offload.space, "unique", None),
                "virtual": getattr(offload.space, "virtual", None),
                "replication": getattr(offload.space, "replication", None),
                "used_provisioned": getattr(offload.space, "used_provisioned", None),
                "total_used": getattr(offload.space, "total_used", None),
            }
    return offload_info


def generate_azure_offload_dict(array):
    offload_info = {}
    offloads_res = array.get_offloads(protocol="azure")
    if offloads_res.status_code == 200:
        offloads = list(offloads_res.items)
        for offload in offloads:
            name = offload.name
            offload_info[name] = {
                "status": offload.status,
                "account_name": getattr(offload.azure, "account_name", None),
                "profile": getattr(offload.azure, "profile", None),
                "protocol": offload.protocol,
                "secret_access_key": getattr(offload.azure, "secret_access_key", None),
                "container_name": getattr(offload.azure, "container_name", None),
                "snapshots": getattr(offload.space, "snapshots", None),
                "shared": getattr(offload.space, "shared", None),
                "data_reduction": getattr(offload.space, "data_reduction", None),
                "thin_provisioning": getattr(offload.space, "thin_provisioning", None),
                "total_physical": getattr(offload.space, "total_physical", None),
                "total_provisioned": getattr(offload.space, "total_provisioned", None),
                "total_reduction": getattr(offload.space, "total_reduction", None),
                "unique": getattr(offload.space, "unique", None),
                "virtual": getattr(offload.space, "virtual", None),
                "replication": getattr(offload.space, "replication", None),
                "used_provisioned": getattr(offload.space, "used_provisioned", None),
                "total_used": getattr(offload.space, "total_used", None),
            }
    return offload_info


def generate_google_offload_dict(array):
    offload_info = {}
    offloads_res = array.get_offloads(protocol="google-cloud")
    if offloads_res.status_code == 200:
        offloads = list(offloads_res.items)
        for offload in offloads:
            name = offload.name
            offload_info[name] = {
                "access_key_id": getattr(offload.google_cloud, "access_key_id", None),
                "bucket": getattr(offload.google_cloud, "bucket", None),
                "profile": getattr(offload.google_cloud, "profile", None),
                "secret_access_key": getattr(
                    offload.google_cloud, "secret_access_key", None
                ),
                "snapshots": getattr(offload.space, "snapshots", None),
                "shared": getattr(offload.space, "shared", None),
                "data_reduction": getattr(offload.space, "data_reduction", None),
                "thin_provisioning": getattr(offload.space, "thin_provisioning", None),
                "total_physical": getattr(offload.space, "total_physical", None),
                "total_provisioned": getattr(offload.space, "total_provisioned", None),
                "total_reduction": getattr(offload.space, "total_reduction", None),
                "unique": getattr(offload.space, "unique", None),
                "virtual": getattr(offload.space, "virtual", None),
                "replication": getattr(offload.space, "replication", None),
                "used_provisioned": getattr(offload.space, "used_provisioned", None),
                "total_used": getattr(offload.space, "total_used", None),
            }
    return offload_info


def generate_hgroups_dict(array, performance):
    hgroups_info = {}
    hgroups = list(array.get_host_groups().items)
    for hgroup in hgroups:
        if hgroup.is_local:
            name = hgroup.name
            hgroups_info[name] = {
                "hosts": [],
                "pgs": [],
                "vols": [],
                "tags": [],
                "snapshots": getattr(hgroup.space, "snapshots", None),
                "data_reduction": getattr(hgroup.space, "data_reduction", None),
                "thin_provisioning": getattr(hgroup.space, "thin_provisioning", None),
                "total_physical": getattr(hgroup.space, "total_physical", None),
                "total_provisioned": getattr(hgroup.space, "total_provisioned", None),
                "total_reduction": getattr(hgroup.space, "total_reduction", None),
                "unique": getattr(hgroup.space, "unique", None),
                "virtual": getattr(hgroup.space, "virtual", None),
                "used_provisioned": getattr(hgroup.space, "used_provisioned", None),
                "total_used": getattr(hgroup.space, "total_used", None),
                "destroyed": getattr(hgroup, "destroyed", False),
                "time_remaining": getattr(hgroup, "time_remaining", None),
            }
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        hgroup_tags = list(array.get_host_groups_tags(resource_destroyed=False).items)
        for tag in hgroup_tags:
            hgroups_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    if performance:
        hgs_performance = list(array.get_host_groups_performance().items)
        for perf in hgs_performance:
            if ":" not in perf.name:
                hgroups_info[perf.name]["performance"] = {
                    "bytes_per_mirrored_write": perf.bytes_per_mirrored_write,
                    "bytes_per_op": perf.bytes_per_op,
                    "bytes_per_read": perf.bytes_per_read,
                    "bytes_per_write": perf.bytes_per_write,
                    "mirrored_write_bytes_per_sec": perf.mirrored_write_bytes_per_sec,
                    "mirrored_writes_per_sec": perf.mirrored_writes_per_sec,
                    "qos_rate_limit_usec_per_mirrored_write_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_read_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                    "qos_rate_limit_usec_per_write_op": perf.qos_rate_limit_usec_per_read_op,
                    "queue_usec_per_mirrored_write_op": perf.queue_usec_per_mirrored_write_op,
                    "queue_usec_per_read_op": perf.queue_usec_per_read_op,
                    "queue_usec_per_write_op": perf.queue_usec_per_write_op,
                    "read_bytes_per_sec": perf.read_bytes_per_sec,
                    "reads_per_sec": perf.reads_per_sec,
                    "san_usec_per_mirrored_write_op": perf.san_usec_per_mirrored_write_op,
                    "san_usec_per_read_op": perf.san_usec_per_read_op,
                    "san_usec_per_write_op": perf.san_usec_per_write_op,
                    "service_usec_per_mirrored_write_op": perf.service_usec_per_mirrored_write_op,
                    "service_usec_per_read_op": perf.service_usec_per_read_op,
                    "service_usec_per_write_op": perf.service_usec_per_write_op,
                    "usec_per_mirrored_write_op": perf.usec_per_mirrored_write_op,
                    "usec_per_read_op": perf.usec_per_read_op,
                    "usec_per_write_op": perf.usec_per_write_op,
                    "write_bytes_per_sec": perf.write_bytes_per_sec,
                    "writes_per_sec": perf.writes_per_sec,
                }
    hg_vols = list(array.get_connections().items)
    for hg_vol in hg_vols:
        if (
            getattr(hg_vol.host_group, "name", None)
            and ":" not in hg_vol.host_group.name
        ):
            name = hg_vol.host_group.name
            vol_entry = {
                "name": hg_vol.volume.name,
                "lun": getattr(hg_vol, "lun", None),
                "nsid": getattr(hg_vol, "nsid", None),
            }
            vols_list = hgroups_info[name]["vols"]
            if vol_entry not in vols_list:
                vols_list.append(vol_entry)
    hg_hosts = list(array.get_host_groups_hosts().items)
    for hg_host in hg_hosts:
        if hg_host.group.name in hgroups_info:
            hgroups_info[hg_host.group.name]["hosts"].append(hg_host.member.name)
    hg_pgs = list(array.get_host_groups_protection_groups().items)
    for hg_pg in hg_pgs:
        if hg_pg.group.name in hgroups_info:
            hgroups_info[hg_pg.group.name]["pgs"].append(hg_pg.member.name)
    return hgroups_info


def generate_interfaces_dict(array):
    int_info = {}
    ports = list(array.get_ports().items)
    for port in ports:
        int_name = port.name
        if hasattr(port, "wwn"):
            int_info[int_name] = {
                "wwn": getattr(port, "wwn", None),
                "iqn": getattr(port, "iqn", None),
                "nqn": getattr(port, "nqn", None),
                "portal": getattr(port, "portal", None),
            }
    return int_info


def generate_vm_dict(array):
    vm_info = {}
    virt_machines = list(array.get_virtual_machines(vm_type="vvol").items)
    for machine in virt_machines:
        name = machine.name
        vm_info[name] = {
            "vm_type": machine.vm_type,
            "vm_id": machine.vm_id,
            "destroyed": machine.destroyed,
            "created": machine.created,
            "time_remaining": getattr(machine, "time_remaining", None),
            "latest_snapshot_name": getattr(machine.recover_context, "name", None),
            "latest_snapshot_id": getattr(machine.recover_context, "id", None),
        }
    return vm_info


def generate_alerts_dict(array):
    alerts_info = {}
    alerts = list(array.get_alerts().items)
    for alert in alerts:
        name = alert.name
        try:
            notified_time = alert.notified / 1000
            notified_datetime = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(notified_time)
            )
        except AttributeError:
            notified_datetime = ""
        try:
            closed_time = alert.closed / 1000
            closed_datetime = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(closed_time)
            )
        except AttributeError:
            closed_datetime = ""
        try:
            updated_time = alert.updated / 1000
            updated_datetime = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(updated_time)
            )
        except AttributeError:
            updated_datetime = ""
        try:
            created_time = alert.created / 1000
            created_datetime = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(created_time)
            )
        except AttributeError:
            updated_datetime = ""
        alerts_info[name] = {
            "flagged": alert.flagged,
            "category": alert.category,
            "code": alert.code,
            "issue": alert.issue,
            "kb_url": alert.knowledge_base_url,
            "summary": alert.summary,
            "id": alert.id,
            "state": alert.state,
            "severity": alert.severity,
            "component_name": alert.component_name,
            "component_type": alert.component_type,
            "created": created_datetime,
            "closed": closed_datetime,
            "notified": notified_datetime,
            "updated": updated_datetime,
            "actual": getattr(alert, "actual", ""),
            "expected": getattr(alert, "expected", ""),
        }
    return alerts_info


def generate_vmsnap_dict(array):
    vmsnap_info = {}
    virt_snaps = list(array.get_virtual_machine_snapshots(vm_type="vvol").items)
    for virt_snap in virt_snaps:
        name = virt_snap.name
        vmsnap_info[name] = {
            "vm_type": virt_snap.vm_type,
            "vm_id": virt_snap.vm_id,
            "destroyed": virt_snap.destroyed,
            "created": virt_snap.created,
            "time_remaining": getattr(virt_snap, "time_remaining", None),
            "latest_pgsnapshot_name": getattr(virt_snap.recover_context, "name", None),
            "latest_pgsnapshot_id": getattr(virt_snap.recover_context, "id", None),
        }
    return vmsnap_info


def generate_subs_dict(array):
    subs_info = {}
    subs = list(array.get_subscription_assets().items)
    for sub in subs:
        subs_info[sub.name] = {
            "subscription_id": sub.subscription.id,
        }
    return subs_info


def generate_fleet_dict(array):
    fleet_info = {}
    fleet = list(array.get_fleets().items)
    if fleet:
        fleet_name = list(array.get_fleets().items)[0].name
        fleet_info[fleet_name] = {
            "members": {},
        }
        members = list(array.get_fleets_members().items)
        for member in members:
            name = member.member.name
            fleet_info[fleet_name]["members"][name] = {
                "status": member.status,
                "status_details": member.status_details,
                "role": (
                    "fleet_coordinator" if hasattr(member, "coordinator_of") else None
                ),
            }
    return fleet_info


def generate_tgroups_dict(array):
    tgroups_info = {}
    tgroups = list(array.get_topology_groups().items)
    for tgroup in tgroups:
        tgroups_info[tgroup.name] = {
            "id": getattr(tgroup, "id", None),
            "context": tgroup.context.name,
            "parent_topology_group": tgroup.parent_topology_group.name,
            "arrays": [],
            "tgroups": [],
        }

    if not tgroups_info:
        return tgroups_info

    members = list(array.get_topology_groups_members().items)
    for member in members:
        group_name = member.topology_group.name
        member_ref = member.member
        member_name = member_ref.name
        member_type = member_ref.resource_type
        if group_name not in tgroups_info or not member_name:
            continue
        member_info = {
            "name": member_name,
            "status": member.status,
            "status_details": member.status_details,
        }
        if member_type == "remote-arrays":
            tgroups_info[group_name]["arrays"].append(member_info)
        elif member_type == "topology-groups":
            tgroups_info[group_name]["tgroups"].append(member_info)
    return tgroups_info


def generate_preset_dict(array):

    def to_plain(value):
        """Recursively convert SDK objects into JSON-safe primitives."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [to_plain(v) for v in value]
        if isinstance(value, dict):
            return {k: to_plain(v) for k, v in value.items()}
        if hasattr(value, "__dict__"):
            return {
                k: to_plain(v) for k, v in vars(value).items() if not k.startswith("_")
            }
        return str(value)

    def collate_by_name(items):
        """
        Given a list of dicts/SDK models with a 'name' attribute/key,
        returns a dict keyed by name.
        """
        result = {}
        for item in items or []:
            plain_item = to_plain(item)
            name = plain_item.get("name")
            if name:
                result[name] = plain_item
        return result

    preset_info = {}
    response = array.get_presets_workload()

    # Handle API errors gracefully
    if hasattr(response, "errors") and response.errors:
        raise RuntimeError(f"Failed to fetch presets: {response.errors}")

    for preset in getattr(response, "items", []):
        preset_name = getattr(preset, "name", None)
        if not preset_name:
            continue

        # Flatten parameters, collated by name
        parameters_collated = {}
        for param in getattr(preset, "parameters", []):
            param_type = getattr(param, "type", None)
            metadata = getattr(param, "metadata", None)
            constraints_obj = getattr(param, "constraints", None)

            # Get the actual constraint dict for this type
            constraint_dict = {}
            if constraints_obj and param_type:
                raw_constraints = getattr(constraints_obj, param_type, None)
                constraint_dict = to_plain(raw_constraints)

            param_entry = {
                "type": param_type,
                "name": getattr(param, "name", None),
                "description": getattr(metadata, "description", None),
                "display_name": getattr(metadata, "display_name", None),
                "subtype": getattr(metadata, "subtype", None),
                "constraints": constraint_dict,
            }

            if param_entry["name"]:
                parameters_collated[param_entry["name"]] = param_entry

        preset_dict = {
            "description": getattr(preset, "description", None),
            "workload_type": getattr(preset, "workload_type", None),
            "revision": getattr(preset, "revision", None),
            "context": to_plain(getattr(preset, "context", None)),
            "parameters": parameters_collated,  # collated by name
            # Collate other sublists by 'name'
            "volume_configurations": collate_by_name(
                getattr(preset, "volume_configurations", [])
            ),
            "placement_configurations": collate_by_name(
                getattr(preset, "placement_configurations", [])
            ),
            "qos_configurations": collate_by_name(
                getattr(preset, "qos_configurations", [])
            ),
            "snapshot_configurations": collate_by_name(
                getattr(preset, "snapshot_configurations", [])
            ),
            "periodic_replication_configurations": collate_by_name(
                getattr(preset, "periodic_replication_configurations", [])
            ),
            # workload_tags remain as list
            "workload_tags": to_plain(getattr(preset, "workload_tags", [])),
        }

        preset_info[preset_name] = preset_dict

    return preset_info


def generate_workload_dict(array):
    # LOCAL WORKAROUND - DO NOT COMMIT. Tracked separately in
    # lab/bug-purefa_info-workload-status-details.md; applied only so the
    # purefa_workload verification playbook can run past its purefa_info
    # read-backs. Revert with: git checkout plugins/modules/purefa_info.py
    workload_info = {}
    workloads = list(array.get_workloads().items)
    if workloads:
        for workload in workloads:
            created = getattr(workload, "created", None)
            workload_info[workload.name] = {
                "description": getattr(workload, "description", None),
                "context": getattr(getattr(workload, "context", None), "name", None),
                "destroyed": getattr(workload, "destroyed", False),
                "preset": getattr(getattr(workload, "preset", None), "name", None),
                "status": getattr(workload, "status", None),
                "status_details": getattr(workload, "status_details", []),
                "created": (
                    time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(created / 1000))
                    if created
                    else None
                ),
                "time_remaining": getattr(workload, "time_remaining", None),
            }
    return workload_info


def generate_realms_dict(array, performance):
    realms_info = {}
    realms = list(array.get_realms().items)
    for realm in realms:
        name = realm.name
        realms_info[name] = {
            "created": time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(realm.created / 1000)
            ),
            "destroyed": realm.destroyed,
            "quota_limit": realm.quota_limit,
            "data_reduction": getattr(realm.space, "data_reduction", None),
            "footprint": getattr(realm.space, "footprint", None),
            "shared": getattr(realm.space, "shared", None),
            "snapshots": getattr(realm.space, "snapshots", None),
            "thin_provisioning": getattr(realm.space, "thin_provisioning", None),
            "total_provisioned": getattr(realm.space, "total_provisioned", None),
            "total_reduction": getattr(realm.space, "total_reduction", None),
            "total_used": getattr(realm.space, "total_used", None),
            "unique": getattr(realm.space, "unique", None),
            "used_provisioned": getattr(realm.space, "used_provisioned", None),
            "virtual": getattr(realm.space, "virtual", None),
            "performance": [],
            "qos": [],
            "tags": [],
        }
        realms_info[name]["qos"] = {
            "iops_limit": getattr(realm.qos, "iops_limit", None),
            "bandwidth_limit": getattr(realm.qos, "bandwidth_limit", None),
        }
        if realms_info[name]["destroyed"]:
            realms_info[name]["time_remaining"] = realm.time_remaining
    if LooseVersion(TAGS_API_VERSION) <= LooseVersion(array.get_rest_version()):
        realms_tags = list(array.get_realms_tags(resource_destroyed=False).items)
        for tag in realms_tags:
            realms_info[tag.resource.name]["tags"].append(
                {
                    "key": tag.key,
                    "value": tag.value,
                    "copyable": tag.copyable,
                    "namespace": tag.namespace,
                }
            )
    if performance:
        r_perfs = list(array.get_realms_performance().items)
        for perf in r_perfs:
            realms_info[perf.name]["performance"] = {
                "bytes_per_mirrored_write": perf.bytes_per_mirrored_write,
                "bytes_per_op": perf.bytes_per_op,
                "bytes_per_read": perf.bytes_per_read,
                "bytes_per_write": perf.bytes_per_write,
                "mirrored_write_bytes_per_sec": perf.mirrored_write_bytes_per_sec,
                "mirrored_writes_per_sec": perf.mirrored_writes_per_sec,
                "others_per_sec": perf.others_per_sec,
                "qos_rate_limit_usec_per_mirrored_write_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                "qos_rate_limit_usec_per_read_op": perf.qos_rate_limit_usec_per_mirrored_write_op,
                "qos_rate_limit_usec_per_write_op": perf.qos_rate_limit_usec_per_read_op,
                "queue_usec_per_mirrored_write_op": perf.queue_usec_per_mirrored_write_op,
                "queue_usec_per_read_op": perf.queue_usec_per_read_op,
                "queue_usec_per_write_op": perf.queue_usec_per_write_op,
                "read_bytes_per_sec": perf.read_bytes_per_sec,
                "reads_per_sec": perf.reads_per_sec,
                "san_usec_per_mirrored_write_op": perf.san_usec_per_mirrored_write_op,
                "san_usec_per_read_op": perf.san_usec_per_read_op,
                "san_usec_per_write_op": perf.san_usec_per_write_op,
                "service_usec_per_mirrored_write_op": perf.service_usec_per_mirrored_write_op,
                "service_usec_per_read_op": perf.service_usec_per_read_op,
                "service_usec_per_write_op": perf.service_usec_per_write_op,
                "usec_per_mirrored_write_op": perf.usec_per_mirrored_write_op,
                "usec_per_other_op": perf.usec_per_other_op,
                "usec_per_read_op": perf.usec_per_read_op,
                "usec_per_write_op": perf.usec_per_write_op,
                "write_bytes_per_sec": perf.write_bytes_per_sec,
                "writes_per_sec": perf.writes_per_sec,
            }
    return realms_info


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(gather_subset=dict(default="minimum", type="list", elements="str"))
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    array = get_array(module)
    api_version = array.get_rest_version()
    subset = [test.lower() for test in module.params["gather_subset"]]
    valid_subsets = (
        "all",
        "minimum",
        "config",
        "performance",
        "capacity",
        "network",
        "subnet",
        "interfaces",
        "hgroups",
        "pgroups",
        "hosts",
        "admins",
        "volumes",
        "snapshots",
        "pods",
        "replication",
        "vgroups",
        "offload",
        "apps",
        "arrays",
        "certs",
        "kmip",
        "clients",
        "policies",
        "dir_snaps",
        "filesystems",
        "alerts",
        "virtual_machines",
        "subscriptions",
        "realms",
        "fleet",
        "presets",
        "workloads",
        "tgroups",
    )
    subset_test = (test in valid_subsets for test in subset)
    if not all(subset_test):
        module.fail_json(
            msg="value must gather_subset must be one or more of: %s, got: %s"
            % (",".join(valid_subsets), ",".join(subset))
        )

    info = {}
    performance = False
    if "minimum" in subset or "all" in subset or "apps" in subset:
        info["default"] = generate_default_dict(array)
    if "performance" in subset or "all" in subset:
        performance = True
        info["performance"] = generate_perf_dict(array)
    if "config" in subset or "all" in subset:
        info["config"] = generate_config_dict(module, array)
    if "capacity" in subset or "all" in subset:
        info["capacity"] = generate_capacity_dict(array)
    if "network" in subset or "all" in subset:
        info["network"] = generate_network_dict(array, performance)
    if "subnet" in subset or "all" in subset:
        info["subnet"] = generate_subnet_dict(array)
    if "interfaces" in subset or "all" in subset:
        info["interfaces"] = generate_interfaces_dict(array)
    if "hosts" in subset or "all" in subset:
        info["hosts"] = generate_host_dict(array, performance)
    if "volumes" in subset or "all" in subset:
        info["volumes"] = generate_vol_dict(array, performance)
        info["deleted_volumes"] = generate_del_vol_dict(array)
    if "snapshots" in subset or "all" in subset:
        info["snapshots"] = generate_snap_dict(array)
        info["deleted_snapshots"] = generate_del_snap_dict(array)
    if "hgroups" in subset or "all" in subset:
        info["hgroups"] = generate_hgroups_dict(array, performance)
    if "pgroups" in subset or "all" in subset:
        info["pgroups"] = generate_pgroups_dict(array)
        info["deleted_pgroups"] = generate_del_pgroups_dict(array)
    if "pods" in subset or "all" in subset or "replication" in subset:
        info["replica_links"] = generate_rl_dict(array)
        info["pods"] = generate_pods_dict(array, performance)
        info["deleted_pods"] = generate_del_pods_dict(array)
    if "admins" in subset or "all" in subset:
        info["admins"] = generate_admin_dict(array)
    if "vgroups" in subset or "all" in subset:
        info["vgroups"] = generate_vgroups_dict(array, performance)
        info["deleted_vgroups"] = generate_del_vgroups_dict(array)
    if "offload" in subset or "all" in subset:
        info["azure_offload"] = generate_azure_offload_dict(array)
        info["nfs_offload"] = generate_nfs_offload_dict(array)
        info["s3_offload"] = generate_s3_offload_dict(array)
    if "apps" in subset or "all" in subset:
        if "CBS" not in info["default"]["array_model"]:
            info["apps"] = generate_apps_dict(array)
        else:
            info["apps"] = {}
        if "minimum" not in subset or "all" not in subset:
            del info["default"]
    if "arrays" in subset or "all" in subset:
        info["arrays"] = generate_conn_array_dict(array)
    if "certs" in subset or "all" in subset:
        info["certs"] = generate_certs_dict(array)
    if "kmip" in subset or "all" in subset:
        info["kmip"] = generate_kmip_dict(array)
    if "offload" in subset or "all" in subset:
        info["google_offload"] = generate_google_offload_dict(array)
    if "filesystems" in subset or "all" in subset:
        info["filesystems"] = generate_filesystems_dict(array, performance)
    if "policies" in subset or "all" in subset:
        user_map = bool(LooseVersion(NFS_USER_MAP_VERSION) <= LooseVersion(api_version))
        quota = bool(LooseVersion(DIR_QUOTA_API_VERSION) <= LooseVersion(api_version))
        autodir = bool(LooseVersion(AUTODIR_API_VERSION) <= LooseVersion(api_version))
        info["policies"] = generate_policies_dict(array, quota, autodir, user_map)
    if "clients" in subset or "all" in subset:
        info["clients"] = generate_clients_dict(array)
    if "dir_snaps" in subset or "all" in subset:
        info["dir_snaps"] = generate_dir_snaps_dict(array)
    if "snapshots" in subset or "all" in subset:
        info["pg_snapshots"] = generate_pgsnaps_dict(array)
    if "alerts" in subset or "all" in subset:
        info["alerts"] = generate_alerts_dict(array)
    if LooseVersion(SUBS_API_VERSION) <= LooseVersion(api_version) and (
        "subscriptions" in subset or "all" in subset
    ):
        info["subscriptions"] = generate_subs_dict(array)
    if LooseVersion(VM_VERSION) <= LooseVersion(api_version) and (
        "virtual_machines" in subset or "all" in subset
    ):
        info["virtual_machines"] = generate_vm_dict(array)
        info["virtual_machines_snaps"] = generate_vmsnap_dict(array)
    if LooseVersion(DSROLE_POLICY_API_VERSION) <= LooseVersion(api_version):
        if "realms" in subset or "all" in subset:
            info["realms"] = generate_realms_dict(array, performance)
    if LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version):
        if "fleet" in subset or "all" in subset:
            info["fleet"] = generate_fleet_dict(array)
        if "presets" in subset or "all" in subset:
            info["presets"] = generate_preset_dict(array)
        if "workloads" in subset or "all" in subset:
            info["workloads"] = generate_workload_dict(array)
    if LooseVersion(TGROUP_API_VERSION) <= LooseVersion(api_version) and (
        "tgroups" in subset or "all" in subset
    ):
        info["tgroups"] = generate_tgroups_dict(array)
    module.exit_json(changed=False, purefa_info=info)


if __name__ == "__main__":
    main()
