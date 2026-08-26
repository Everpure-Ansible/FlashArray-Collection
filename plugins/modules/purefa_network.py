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


DOCUMENTATION = """
---
module: purefa_network
short_description:  Manage network interfaces in a Everpure FlashArray
version_added: '1.0.0'
description:
    - This module manages the physical and virtual network interfaces on a Everpure FlashArray.
    - To manage VLAN interfaces use the I(everpure.flasharray.purefa_vlan) module.
    - To manage network subnets use the I(everpure.flasharray.purefa_subnet) module.
    - To remove an IP address from a non-management port use 0.0.0.0/0
author: Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
      - Interface name (physical or virtual).
    required: true
    type: str
  state:
    description:
      - State of existing interface (on/off).
    required: false
    default: present
    choices: [ "present", "absent" ]
    type: str
  address:
    description:
      - IPv4 or IPv6 address of interface in CIDR notation.
      - To remove an IP address from a non-management port use 0.0.0.0/0
    required: false
    type: str
  gateway:
    description:
      - IPv4 or IPv6 address of interface gateway.
    required: false
    type: str
  mtu:
    description:
      - MTU size of the interface. Range is 1280 to 9216.
    required: false
    type: int
  servicelist:
    description:
      - Assigns the specified (comma-separated) service list to one or more specified interfaces.
      - Replaces the previous service list.
      - Supported service lists depend on whether the network interface is Ethernet or Fibre Channel.
      - Note that I(system) is only valid for Cloud Block Store.
    elements: str
    type: list
    choices: [ "replication", "management", "ds", "file", "iscsi", "scsi-fc", "nvme-fc", "nvme-tcp", "nvme-roce", "system"]
    version_added: '1.15.0'
  interface:
    description:
      - Type of interface to create if subinterfaces is supplied
    type: str
    choices: [ "vif", "lacp" ]
    version_added: '1.22.0'
  subordinates:
    description:
     - List of one or more child devices to be added to a LACP interface
     - Subordinates must be on the same controller, therefore the full device needs
       to be provided.
    type: list
    elements: str
    version_added: '1.22.0'
  subinterfaces:
    description:
     - List of one or more child devices to be added to a VIF interface
     - Only the 'eth' name needs to be provided, such as 'eth6'. This interface on
       all controllers will be assigned to the interface.
    type: list
    elements: str
    version_added: '1.22.0'
  subnet:
    description:
     - Name of the subnet which interface is to be attached
    type: str
    version_added: '1.22.0'
  enabled:
    description:
    - State of the network interface
    type: bool
    default: true
    version_added: '1.22.0'
extends_documentation_fragment:
    - everpure.flasharray.everpure.fa
"""

EXAMPLES = """
- name: Configure and enable network interface ct0.eth8
  everpure.flasharray.purefa_network:
    name: ct0.eth8
    gateway: 10.21.200.1
    address: "10.21.200.18/24"
    mtu: 9000
    state: present
    fa_url: 10.10.10.2
    api_token: c6033033-fe69-2515-a9e8-966bb7fe4b40

- name: Disable physical interface ct1.eth2
  everpure.flasharray.purefa_network:
    name: ct1.eth2
    state: absent
    fa_url: 10.10.10.2
    api_token: c6033033-fe69-2515-a9e8-966bb7fe4b40

- name: Enable virtual network interface vir0
  everpure.flasharray.purefa_network:
    name: vir0
    state: present
    fa_url: 10.10.10.2
    api_token: c6033033-fe69-2515-a9e8-966bb7fe4b40

- name: Remove an IP address from iSCSI interface ct0.eth4
  everpure.flasharray.purefa_network:
    name: ct0.eth4
    address: 0.0.0.0/0
    gateway: 0.0.0.0
    fa_url: 10.10.10.2
    api_token: c6033033-fe69-2515-a9e8-966bb7fe4b40

- name: Change service list for FC interface ct0.fc1
  everpure.flasharray.purefa_network:
    name: ct0.fc1
    servicelist:
      - replication
    fa_url: 10.10.10.2
    api_token: c6033033-fe69-2515-a9e8-966bb7fe4b40
"""

RETURN = """
"""

try:
    from netaddr import IPAddress, IPNetwork, valid_ipv4

    HAS_NETADDR = True
except ImportError:
    HAS_NETADDR = False

try:
    from pypureclient.flasharray import (
        NetworkInterfacePatch,
        NetworkInterfacePost,
        NetworkinterfacepostEth,
        NetworkinterfacepatchEth,
        FixedReferenceNoId,
        ReferenceNoId,
    )

    HAS_PYPURECLIENT = True
except ImportError:
    HAS_PYPURECLIENT = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_response,
)

# An unconfigured address, netmask or gateway is reported by the array as null,
# but is cleared by writing 0.0.0.0 (or :: for IPv6). Those describe the same
# state, so both have to be reduced to a single representation before the
# current and desired settings can be compared - otherwise clearing an address
# looks like a change that still needs making on every subsequent run.
UNSET_IP = (None, "", "0.0.0.0", "::")
UNSET_NETMASK = (None, "", "0.0.0.0", "0")


def _comparable_state(state):
    """Return a copy of an interface state with cleared IP settings unified"""
    comparable = dict(state)
    for setting in ("address", "gateway"):
        if comparable[setting] in UNSET_IP:
            comparable[setting] = ""
    if comparable["netmask"] in UNSET_NETMASK:
        comparable["netmask"] = ""
    return comparable


def update_fc_interface(module, array, interface):
    """Modify FC Interface settings"""
    changed = False
    if not interface.enabled and module.params["state"] == "present":
        changed = True
        if not module.check_mode:
            network = NetworkInterfacePatch(enabled=True, override_npiv_check=True)
            res = array.patch_network_interfaces(
                names=[module.params["name"]], network=network
            )
            check_response(
                res, module, f"Failed to enable interface {module.params['name']}"
            )
    if interface.enabled and module.params["state"] == "absent":
        changed = True
        if not module.check_mode:
            network = NetworkInterfacePatch(enabled=False, override_npiv_check=True)
            res = array.patch_network_interfaces(
                names=[module.params["name"]], network=network
            )
            check_response(
                res, module, f"Failed to disable interface {module.params['name']}"
            )
    if module.params["servicelist"] and sorted(module.params["servicelist"]) != sorted(
        interface.services
    ):
        changed = True
        if not module.check_mode:
            network = NetworkInterfacePatch(services=module.params["servicelist"])
            res = array.patch_network_interfaces(
                names=[module.params["name"]], network=network
            )
            check_response(
                res,
                module,
                f"Failed to update interface service list {module.params['name']}",
            )

    module.exit_json(changed=changed)


def _check_subinterfaces(module, array):
    subordinates = []
    subinterfaces = list(
        array.get_network_interfaces(names=[module.params["name"]]).items
    )[0].eth.subinterfaces
    for subinterface in subinterfaces:
        # subinterfaces are FixedReferenceNoId objects; store the name so the
        # result is a list of sortable/comparable strings
        subordinates.append(subinterface.name)
    return subordinates


def _create_subordinates(module, array):
    subordinates_v1 = []
    subordinates_v2 = []
    all_children = True
    if module.params["subordinates"]:
        for inter in sorted(module.params["subordinates"]):
            if array.get_network_interfaces(names=[inter]).status_code != 200:
                all_children = False
            if not all_children:
                module.fail_json(
                    msg="Subordinate {0} does not exist. Ensure you have specified the controller.".format(
                        inter
                    )
                )
            subordinates_v2.append(FixedReferenceNoId(name=inter))
            subordinates_v1.append(inter)
    return subordinates_v1, subordinates_v2


def _create_subinterfaces(module, array):
    subinterfaces_v1 = []
    subinterfaces_v2 = []
    all_children = True
    purity_vm = bool(len(array.get_controllers().items) == 1)
    if module.params["subinterfaces"]:
        if any("lacp" in sub for sub in module.params["subinterfaces"]):
            for inter in sorted(module.params["subinterfaces"]):
                if array.get_network_interfaces(names=[inter]).status_code != 200:
                    all_children = False
                if not all_children:
                    module.fail_json(
                        msg="Child subinterface {0} does not exist".format(inter)
                    )
                subinterfaces_v2.append(FixedReferenceNoId(name=inter))
                subinterfaces_v1.append(inter)
        else:
            for inter in sorted(module.params["subinterfaces"]):
                # As we may be on a single controller device, only check for the ct0 version of the interface
                if (
                    array.get_network_interfaces(names=["ct0." + inter]).status_code
                    != 200
                ):
                    all_children = False
                if not all_children:
                    module.fail_json(
                        msg="Child subinterface {0} does not exist".format(inter)
                    )
                subinterfaces_v2.append(FixedReferenceNoId(name="ct0." + inter))
                subinterfaces_v1.append("ct0." + inter)
                if not purity_vm:
                    subinterfaces_v2.append(FixedReferenceNoId(name="ct1." + inter))
                    subinterfaces_v1.append("ct1." + inter)
    return subinterfaces_v1, subinterfaces_v2


def update_interface(module, array):
    """Modify Interface settings"""
    changed = False
    interfaces = list(array.get_network_interfaces(names=[module.params["name"]]).items)
    if not interfaces:
        module.fail_json("Interface {0} not found".format(module.params["name"]))

    interface = interfaces[0]

    def is_fc_interface(ifname):
        parts = ifname.split(".")
        return len(parts) > 1 and parts[1].lower().startswith("f")

    # Modify FC Interface settings
    if is_fc_interface(module.params["name"]):
        if not interface.enabled and module.params["state"] == "present":
            changed = True
            if not module.check_mode:
                network = NetworkInterfacePatch(enabled=True, override_npiv_check=True)
                res = array.patch_network_interfaces(
                    names=[module.params["name"]], network=network
                )
                check_response(
                    res, module, f"Failed to enable interface {module.params['name']}"
                )
        if interface.enabled and module.params["state"] == "absent":
            changed = True
            if not module.check_mode:
                network = NetworkInterfacePatch(enabled=False, override_npiv_check=True)
                res = array.patch_network_interfaces(
                    names=[module.params["name"]], network=network
                )
                check_response(
                    res, module, f"Failed to disable interface {module.params['name']}"
                )
        if module.params["servicelist"] and sorted(
            module.params["servicelist"]
        ) != sorted(interface.services):
            changed = True
            if not module.check_mode:
                network = NetworkInterfacePatch(services=module.params["servicelist"])
                res = array.patch_network_interfaces(
                    names=[module.params["name"]], network=network
                )
                check_response(
                    res,
                    module,
                    f"Failed to update interface service list {module.params['name']}",
                )
        module.exit_json(changed=changed)
    # Modify ETH Interface settings
    current_state = {
        "enabled": interface.enabled,
        "mtu": interface.eth.mtu,
        "gateway": getattr(interface.eth, "gateway", None),
        "address": getattr(interface.eth, "address", None),
        "netmask": getattr(interface.eth, "netmask", None),
        "services": sorted(interface.services),
        # subinterfaces are FixedReferenceNoId objects - sort by name, not object
        "subinterfaces": sorted(sub.name for sub in interface.eth.subinterfaces),
    }
    new_state = current_state.copy()

    if module.params["subinterfaces"]:
        new_subinterfaces = _check_subinterfaces(module, array)
        if sorted(new_subinterfaces) != current_state["subinterfaces"]:
            new_state["subinterfaces"] = sorted(new_subinterfaces)

    if module.params["subordinates"]:
        subordinates = _check_subinterfaces(module, array)
        if sorted(subordinates) != sorted(module.params["subordinates"]):
            new_state["subinterfaces"] = sorted(module.params["subordinates"])

    if module.params["enabled"] != current_state["enabled"]:
        new_state["enabled"] = module.params["enabled"]

    if (
        module.params["servicelist"]
        and sorted(module.params["servicelist"]) != current_state["services"]
    ):
        new_state["services"] = sorted(module.params["servicelist"])

    if (
        module.params["address"]
        and module.params["address"] != current_state["address"]
    ):
        new_state["netmask"] = current_state["netmask"]
        if module.params["gateway"] and module.params["gateway"] not in [
            "0.0.0.0",
            "::",
        ]:
            if module.params["gateway"] not in IPNetwork(module.params["address"]):
                module.fail_json(msg="Gateway and subnet are not compatible.")
        # current_state holds the gateway read with a default - reading
        # interface.eth.gateway directly raises AttributeError on an
        # interface that has no gateway configured
        if not module.params["gateway"] and current_state["gateway"] not in [
            None,
            IPNetwork(module.params["address"]),
        ]:
            module.fail_json(msg="Gateway and subnet are not compatible.")
        new_state["address"] = str(module.params["address"].split("/", 1)[0])
        if new_state["address"] in ["0.0.0.0", "::"]:
            new_state["netmask"] = ""

    if module.params["mtu"] and module.params["mtu"] != current_state["mtu"]:
        if not 1280 <= module.params["mtu"] <= 9216:
            module.fail_json(
                msg="MTU {0} is out of range (1280 to 9216)".format(
                    module.params["mtu"]
                )
            )
        else:
            new_state["mtu"] = module.params["mtu"]

    if module.params["address"]:
        if new_state["address"]:
            if valid_ipv4(new_state["address"]):
                new_state["netmask"] = str(IPNetwork(module.params["address"]).netmask)
            else:
                new_state["netmask"] = str(module.params["address"].split("/", 1)[1])
        if new_state["netmask"] in ["0.0.0.0", "0"]:
            new_state["netmask"] = ""

    if module.params["gateway"] and module.params["gateway"] in ["0.0.0.0", "::"]:
        new_state["gateway"] = ""
    elif module.params["gateway"]:
        # Only validate gateway against subnet if we have a valid address and netmask
        # Skip validation if address is being cleared (0.0.0.0 or ::) or netmask is empty
        if (
            new_state["address"]
            and new_state["address"] not in ["0.0.0.0", "::"]
            and new_state["netmask"]
            and valid_ipv4(new_state["address"])
        ):
            cidr = str(IPAddress(new_state["netmask"]).netmask_bits())
            full_addr = new_state["address"] + "/" + cidr
            if module.params["gateway"] not in IPNetwork(full_addr):
                module.fail_json(msg="Gateway and subnet are not compatible.")
        new_state["gateway"] = module.params["gateway"]

    if new_state["address"]:
        if (
            current_state["address"]
            and IPAddress(new_state["address"]).version
            != IPAddress(current_state["address"]).version
        ):
            if new_state["gateway"]:
                if (
                    IPAddress(new_state["gateway"]).version
                    != IPAddress(new_state["address"]).version
                ):
                    module.fail_json(
                        msg="Changing IP protocol requires gateway to change as well."
                    )
    if _comparable_state(new_state) != _comparable_state(current_state):
        changed = True
        if module.params["servicelist"] and sorted(
            module.params["servicelist"]
        ) != sorted(interface.services):
            if not module.check_mode:
                network = NetworkInterfacePatch(services=module.params["servicelist"])
                res = array.patch_network_interfaces(
                    names=[module.params["name"]], network=network
                )
                check_response(
                    res,
                    module,
                    f"Failed to update interface service list {module.params['name']}",
                )
        if (
            "management" in interface.services or "app" in interface.services
        ) and new_state["address"] in ["0.0.0.0", "::"]:
            module.fail_json(
                msg="Removing IP address from a management or app port is not supported"
            )
        if not module.check_mode:
            res = array.patch_network_interfaces(
                names=[interface.name],
                network=NetworkInterfacePatch(enabled=new_state["enabled"]),
            )
            check_response(
                res,
                module,
                f"Failed to enable or disable interface {module.params['name']}",
            )
            if new_state["gateway"] is not None:
                res = array.patch_network_interfaces(
                    names=[interface.name],
                    network=NetworkInterfacePatch(
                        eth=NetworkinterfacepatchEth(
                            address=new_state["address"],
                            mtu=new_state["mtu"],
                            netmask=new_state["netmask"],
                            gateway=new_state["gateway"],
                        )
                    ),
                )
                check_response(
                    res, module, f"Failed to update IP settings for {interface.name}"
                )
                if (
                    current_state["subinterfaces"] != new_state["subinterfaces"]
                    and new_state["subinterfaces"] != []
                ):
                    new_subs = []
                    for sub in new_state["subinterfaces"]:
                        new_subs.append(ReferenceNoId(sub))
                    res = array.patch_network_interfaces(
                        names=[interface.name],
                        network=NetworkInterfacePatch(
                            eth=NetworkinterfacepatchEth(
                                subinterfacelist=new_subs,
                            )
                        ),
                    )
                    check_response(
                        res,
                        module,
                        f"Failed to update subinterfaces for {interface.name}",
                    )
            else:
                try:
                    if valid_ipv4(new_state["address"]):
                        empty_gateway = "0.0.0.0"
                    else:
                        empty_gateway = "::"
                except Exception:
                    empty_gateway = "::"
                res = array.patch_network_interfaces(
                    names=[interface.name],
                    network=NetworkInterfacePatch(
                        eth=NetworkinterfacepatchEth(
                            address=new_state["address"],
                            mtu=new_state["mtu"],
                            netmask=new_state["netmask"],
                            gateway=empty_gateway,
                        )
                    ),
                )
                check_response(
                    res, module, f"Failed to update IP settings for {interface.name}"
                )
                if (
                    current_state["subinterfaces"] != new_state["subinterfaces"]
                    and new_state["subinterfaces"] != []
                ):
                    res = array.delete_network_interfaces(names=[module.params["name"]])
                    check_response(
                        res,
                        module,
                        f"Failed to delete network interface {module.params['name']}",
                    )
                    create_interface(module, array)
    module.exit_json(changed=changed)


def create_interface(module, array):
    changed = True
    subnet_exists = bool(
        array.get_subnets(names=[module.params["subnet"]]).status_code == 200
    )
    if module.params["subnet"] and not subnet_exists:
        module.fail_json(
            msg="Subnet {0} does not exist".format(module.params["subnet"])
        )

    if module.params["interface"] == "vif":
        dummy, subinterfaces = _create_subinterfaces(module, array)
    else:
        dummy, subinterfaces = _create_subordinates(module, array)

    if not module.check_mode:
        if module.params["address"]:
            address = str(module.params["address"].strip("[]").split("/", 1)[0])
            if valid_ipv4(address):
                netmask = str(IPNetwork(module.params["address"]).netmask)
            else:
                netmask = str(module.params["address"].strip("[]").split("/", 1)[1])
        else:
            netmask = None
            address = None
        if module.params["gateway"]:
            gateway = str(module.params["gateway"].strip("[]"))
            if gateway not in ["0.0.0.0", "::"]:
                if address and gateway not in IPNetwork(module.params["address"]):
                    module.fail_json(msg="Gateway and subnet are not compatible.")
        else:
            gateway = None
        if module.params["interface"] == "vif":
            res = array.post_network_interfaces(
                names=[module.params["name"]],
                network=NetworkInterfacePost(
                    eth=NetworkinterfacepostEth(subtype="vif")
                ),
            )
        else:
            res = array.post_network_interfaces(
                names=[module.params["name"]],
                network=NetworkInterfacePost(
                    eth=NetworkinterfacepostEth(
                        subtype="lacpbond", subinterfaces=subinterfaces
                    ),
                ),
            )

        check_response(
            res, module, f"Failed to create interface {module.params['name']}"
        )

        if module.params["subinterfaces"] and module.params["subnet"]:
            res = array.patch_network_interfaces(
                names=[module.params["name"]],
                network=NetworkInterfacePatch(
                    enabled=module.params["enabled"],
                    eth=NetworkinterfacepatchEth(
                        subinterfaces=subinterfaces,
                        address=address,
                        gateway=gateway,
                        mtu=module.params["mtu"],
                        netmask=netmask,
                        subnet=ReferenceNoId(name=module.params["subnet"]),
                    ),
                ),
            )
            if res.status_code != 200:
                array.delete_network_interfaces(names=[module.params["name"]])
                module.fail_json(
                    msg=f"Failed to create interface {module.params['name']}. "
                    f"Error: {res.errors[0].message}"
                )
        elif module.params["subinterfaces"] and not module.params["subnet"]:
            res = array.patch_network_interfaces(
                names=[module.params["name"]],
                network=NetworkInterfacePatch(
                    enabled=module.params["enabled"],
                    eth=NetworkinterfacepatchEth(
                        subinterfaces=subinterfaces,
                        address=address,
                        gateway=gateway,
                        mtu=module.params["mtu"],
                        netmask=netmask,
                    ),
                ),
            )
            if res.status_code != 200:
                array.delete_network_interfaces(names=[module.params["name"]])
                module.fail_json(
                    msg=f"Failed to create interface {module.params['name']}. "
                    f"Error: {res.errors[0].message}"
                )
        elif not module.params["subinterfaces"] and module.params["subnet"]:
            res = array.patch_network_interfaces(
                names=[module.params["name"]],
                network=NetworkInterfacePatch(
                    enabled=module.params["enabled"],
                    eth=NetworkinterfacepatchEth(
                        address=address,
                        gateway=gateway,
                        mtu=module.params["mtu"],
                        netmask=netmask,
                        subnet=ReferenceNoId(name=module.params["subnet"]),
                    ),
                ),
            )
            if res.status_code != 200:
                array.delete_network_interfaces(names=[module.params["name"]])
                module.fail_json(
                    msg=f"Failed to create interface {module.params['name']}. "
                    f"Error: {res.errors[0].message}"
                )
        else:
            res = array.patch_network_interfaces(
                names=[module.params["name"]],
                network=NetworkInterfacePatch(
                    enabled=module.params["enabled"],
                    eth=NetworkinterfacepatchEth(
                        address=address,
                        gateway=gateway,
                        mtu=module.params["mtu"],
                        netmask=netmask,
                    ),
                ),
            )
            if res.status_code != 200:
                array.delete_network_interfaces(names=[module.params["name"]])
                module.fail_json(
                    msg=f"Failed to create interface {module.params['name']}. "
                    f"Error: {res.errors[0].message}"
                )

    module.exit_json(changed=changed)


def delete_interface(module, array):
    changed = True
    if not module.check_mode:
        res = array.delete_network_interfaces(names=[module.params["name"]])
        check_response(
            res, module, f"Failed to delete network interface {module.params['name']}"
        )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            address=dict(type="str"),
            gateway=dict(type="str"),
            mtu=dict(type="int"),
            servicelist=dict(
                type="list",
                elements="str",
                choices=[
                    "replication",
                    "management",
                    "ds",
                    "file",
                    "iscsi",
                    "scsi-fc",
                    "nvme-fc",
                    "nvme-tcp",
                    "nvme-roce",
                    "system",
                ],
            ),
            interface=dict(type="str", choices=["vif", "lacp"]),
            subinterfaces=dict(type="list", elements="str"),
            subordinates=dict(type="list", elements="str"),
            subnet=dict(type="str"),
            enabled=dict(type="bool", default=True),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if module.params["state"] == "present":
        if module.params["interface"] == "lacp" and not module.params["subordinates"]:
            module.fail_json(
                msg="interface is lacp but all of the following are missing: subordinates"
            )

    creating_new_if = bool(module.params["interface"])

    if not HAS_NETADDR:
        module.fail_json(msg="netaddr module is required")

    if not HAS_PYPURECLIENT:
        module.fail_json(msg="pypureclient module is required")
    array = get_array(module)
    if module.params["address"]:
        module.params["address"] = module.params["address"].strip("[]")
        if "/" not in module.params["address"]:
            module.fail_json(msg="address must include valid netmask bits")
    if module.params["gateway"]:
        module.params["gateway"] = module.params["gateway"].strip("[]")
    if bool("CBS" in list(array.get_controllers().items)[0].model):
        if module.params["servicelist"] and "system" in module.params["servicelist"]:
            module.fail_json(
                msg="Only Cloud Block Store supports the 'system' service type"
            )
    if "." in module.params["name"]:
        interface = bool(
            array.get_network_interfaces(names=[module.params["name"]]).status_code
            == 200
        )
        if not interface:
            module.fail_json(msg="Invalid network interface specified.")
        else:
            update_interface(module, array)
    else:
        if (module.params["interface"] == "vif" and module.params["subordinates"]) or (
            module.params["interface"] == "lacp" and module.params["subinterfaces"]
        ):
            module.fail_json(
                msg="interface type not compatible with provided subinterfaces | subordinates"
            )
        interface = bool(
            array.get_network_interfaces(names=[module.params["name"]]).status_code
            == 200
        )
        if not creating_new_if:
            if not interface:
                module.fail_json(msg="Invalid network interface specified.")
            elif module.params["state"] == "present":
                update_interface(module, array)
            else:
                delete_interface(module, array)
        elif not interface and module.params["state"] == "present":
            create_interface(module, array)
        elif interface and module.params["state"] == "absent":
            delete_interface(module, array)
        elif interface and module.params["state"] == "present":
            update_interface(module, array)
        else:
            module.exit_json(changed=False)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
