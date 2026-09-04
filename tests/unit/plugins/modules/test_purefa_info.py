# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, patch, MagicMock
from packaging.version import Version as LooseVersion

# Mock external dependencies before importing module
sys.modules["grp"] = MagicMock()
sys.modules["pwd"] = MagicMock()
sys.modules["fcntl"] = MagicMock()
sys.modules["ansible"] = MagicMock()
sys.modules["ansible.module_utils"] = MagicMock()
sys.modules["ansible.module_utils.basic"] = MagicMock()
sys.modules["pypureclient"] = MagicMock()
sys.modules["pypureclient.flasharray"] = MagicMock()
sys.modules["ansible_collections"] = MagicMock()
sys.modules["ansible_collections.everpure"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils"] = (
    MagicMock()
)
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.purefa"] = (
    MagicMock()
)
# Provide real LooseVersion to avoid MagicMock comparison issues
mock_version_module = MagicMock()
mock_version_module.LooseVersion = LooseVersion
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    mock_version_module
)

from plugins.modules.purefa_info import (
    main,
    _is_cbs,
    generate_default_dict,
    generate_perf_dict,
    generate_admin_dict,
    generate_subnet_dict,
    generate_network_dict,
    generate_capacity_dict,
    generate_snap_dict,
    generate_del_snap_dict,
    generate_del_vol_dict,
    generate_vol_dict,
    generate_host_dict,
    generate_del_pgroups_dict,
    generate_pgroups_dict,
    generate_rl_dict,
    generate_del_pods_dict,
    generate_pods_dict,
    generate_conn_array_dict,
    generate_apps_dict,
    generate_vgroups_dict,
    generate_del_vgroups_dict,
    generate_certs_dict,
    generate_kmip_dict,
    generate_nfs_offload_dict,
    generate_s3_offload_dict,
    generate_azure_offload_dict,
    generate_google_offload_dict,
    generate_hgroups_dict,
    generate_interfaces_dict,
    generate_vm_dict,
    generate_alerts_dict,
    generate_vmsnap_dict,
    generate_subs_dict,
    generate_fleet_dict,
    generate_tgroups_dict,
    generate_preset_dict,
    generate_workload_dict,
    generate_realms_dict,
    generate_config_dict,
    generate_filesystems_dict,
    generate_pgsnaps_dict,
    generate_dir_snaps_dict,
    generate_policies_dict,
    generate_clients_dict,
)


class TestIsCbs:
    """Test cases for _is_cbs helper function"""

    def test_is_cbs_true(self):
        """Test _is_cbs returns True for CBS model"""
        mock_array = Mock()
        mock_hw_item = Mock()
        mock_hw_item.model = "CBS-S10"
        mock_hw_response = Mock()
        mock_hw_response.items = [mock_hw_item]
        mock_array.get_hardware.return_value = mock_hw_response

        result = _is_cbs(mock_array)

        assert result is True
        mock_array.get_hardware.assert_called_once_with(filter="type='controller'")

    def test_is_cbs_false(self):
        """Test _is_cbs returns False for non-CBS model"""
        mock_array = Mock()
        mock_hw_item = Mock()
        mock_hw_item.model = "FA-X70R3"
        mock_hw_response = Mock()
        mock_hw_response.items = [mock_hw_item]
        mock_array.get_hardware.return_value = mock_hw_response

        result = _is_cbs(mock_array)

        assert result is False


class TestGeneratePerfDict:
    """Test cases for generate_perf_dict function"""

    def test_generate_perf_dict_success(self):
        """Test performance dict generation"""
        mock_array = Mock()
        mock_perf_data = Mock()
        mock_perf_data.bytes_per_mirrored_write = 4096
        mock_perf_data.bytes_per_op = 8192
        mock_perf_data.bytes_per_read = 16384
        mock_perf_data.bytes_per_write = 8192
        mock_perf_data.mirrored_write_bytes_per_sec = 1000000
        mock_perf_data.mirrored_writes_per_sec = 100
        mock_perf_data.others_per_sec = 10
        mock_perf_data.qos_rate_limit_usec_per_mirrored_write_op = 0
        mock_perf_data.qos_rate_limit_usec_per_read_op = 0
        mock_perf_data.qos_rate_limit_usec_per_write_op = 0
        mock_perf_data.queue_usec_per_mirrored_write_op = 100
        mock_perf_data.queue_usec_per_read_op = 50
        mock_perf_data.queue_usec_per_write_op = 75
        mock_perf_data.read_bytes_per_sec = 5000000
        mock_perf_data.reads_per_sec = 500
        mock_perf_data.san_usec_per_mirrored_write_op = 200
        mock_perf_data.san_usec_per_read_op = 100
        mock_perf_data.san_usec_per_write_op = 150
        mock_perf_data.service_usec_per_mirrored_write_op = 300
        mock_perf_data.service_usec_per_read_op = 150
        mock_perf_data.service_usec_per_write_op = 200
        mock_perf_data.usec_per_mirrored_write_op = 500
        mock_perf_data.usec_per_other_op = 100
        mock_perf_data.usec_per_read_op = 250
        mock_perf_data.usec_per_write_op = 350
        mock_perf_data.write_bytes_per_sec = 3000000
        mock_perf_data.writes_per_sec = 300

        mock_perf_response = Mock()
        mock_perf_response.items = [mock_perf_data]
        mock_array.get_arrays_performance.return_value = mock_perf_response

        result = generate_perf_dict(mock_array)

        assert result["bytes_per_read"] == 16384
        assert result["reads_per_sec"] == 500
        assert result["writes_per_sec"] == 300
        # Legacy values should be 0
        assert result["input_per_sec"] == 0
        assert result["output_per_sec"] == 0
        assert result["queue_depth"] == 0


class TestGenerateAdminDict:
    """Test cases for generate_admin_dict function"""

    @patch("plugins.modules.purefa_info.LooseVersion")
    def test_generate_admin_dict_success(self, mock_loose_version):
        """Test admin dict generation"""
        mock_loose_version.side_effect = float
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_admin = Mock()
        mock_admin.name = "pureuser"
        mock_admin.is_local = True
        mock_admin.locked = False
        mock_admin.public_key = None
        mock_admin.lockout_remaining = None
        mock_role = Mock()
        mock_role.name = "array_admin"
        mock_admin.role = mock_role
        # Mock api_token with numeric values for expires_at and created_at
        mock_api_token = Mock()
        mock_api_token.expires_at = 1709424000000  # timestamp in ms
        mock_api_token.created_at = 1709337600000  # timestamp in ms
        mock_admin.api_token = mock_api_token
        # Mock management_access_policies as a list
        mock_policy = Mock()
        mock_policy.name = "default_policy"
        mock_admin.management_access_policies = [mock_policy]

        mock_admins_response = Mock()
        mock_admins_response.items = [mock_admin]
        mock_array.get_admins.return_value = mock_admins_response

        result = generate_admin_dict(mock_array)

        assert "pureuser" in result
        assert result["pureuser"]["local"] is True
        assert result["pureuser"]["locked"] is False
        assert result["pureuser"]["role"] == "array_admin"

    @patch("plugins.modules.purefa_info.LooseVersion")
    def test_generate_admin_dict_remote_user(self, mock_loose_version):
        """Test admin dict generation for remote user"""
        mock_loose_version.side_effect = float
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_admin = Mock()
        mock_admin.name = "ldapuser@domain.com"
        mock_admin.is_local = False
        mock_admin.locked = False
        mock_admin.public_key = None
        mock_admin.lockout_remaining = None
        mock_role = Mock()
        mock_role.name = "readonly"
        mock_admin.role = mock_role
        # Mock api_token with numeric values for expires_at and created_at
        mock_api_token = Mock()
        mock_api_token.expires_at = 1709424000000  # timestamp in ms
        mock_api_token.created_at = 1709337600000  # timestamp in ms
        mock_admin.api_token = mock_api_token

        mock_admins_response = Mock()
        mock_admins_response.items = [mock_admin]
        mock_array.get_admins.return_value = mock_admins_response

        result = generate_admin_dict(mock_array)

        assert "ldapuser@domain.com" in result
        assert result["ldapuser@domain.com"]["local"] is False


class TestGenerateSubnetDict:
    """Test cases for generate_subnet_dict function"""

    def test_generate_subnet_dict_success(self):
        """Test subnet dict generation"""
        mock_array = Mock()

        mock_subnet = Mock()
        mock_subnet.name = "mgmt-subnet"
        mock_subnet.enabled = True
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.services = ["management", "replication"]
        mock_iface = Mock()
        mock_iface.name = "ct0.eth0"
        mock_subnet.interfaces = [mock_iface]

        mock_subnets_response = Mock()
        mock_subnets_response.items = [mock_subnet]
        mock_array.get_subnets.return_value = mock_subnets_response

        result = generate_subnet_dict(mock_array)

        assert "mgmt-subnet" in result
        assert result["mgmt-subnet"]["enabled"] is True
        assert result["mgmt-subnet"]["gateway"] == "10.0.0.1"
        assert result["mgmt-subnet"]["mtu"] == 1500
        assert result["mgmt-subnet"]["vlan"] == 100
        assert "ct0.eth0" in result["mgmt-subnet"]["interfaces"]

    def test_generate_subnet_dict_no_interfaces(self):
        """Test subnet dict generation with no interfaces"""
        mock_array = Mock()

        mock_subnet = Mock()
        mock_subnet.name = "iscsi-subnet"
        mock_subnet.enabled = False
        mock_subnet.gateway = None
        mock_subnet.mtu = 9000
        mock_subnet.vlan = None
        mock_subnet.prefix = "192.168.1.0/24"
        mock_subnet.services = ["iscsi"]
        mock_subnet.interfaces = None

        mock_subnets_response = Mock()
        mock_subnets_response.items = [mock_subnet]
        mock_array.get_subnets.return_value = mock_subnets_response

        result = generate_subnet_dict(mock_array)

        assert "iscsi-subnet" in result
        assert result["iscsi-subnet"]["interfaces"] == []


class TestGenerateInterfacesDict:
    """Test cases for generate_interfaces_dict function"""

    def test_generate_interfaces_dict_success(self):
        """Test interfaces dict generation with FC port"""
        mock_array = Mock()

        # Generate_interfaces_dict uses get_ports() and checks for wwn attribute
        mock_port = Mock()
        mock_port.name = "CT0.FC0"
        mock_port.wwn = "50:00:00:00:00:00:00:01"
        mock_port.iqn = None
        mock_port.nqn = None
        mock_port.portal = None

        mock_ports_response = Mock()
        mock_ports_response.items = [mock_port]
        mock_array.get_ports.return_value = mock_ports_response

        result = generate_interfaces_dict(mock_array)

        assert "CT0.FC0" in result
        assert result["CT0.FC0"]["wwn"] == "50:00:00:00:00:00:00:01"
        assert result["CT0.FC0"]["iqn"] is None

    def test_generate_interfaces_dict_no_wwn(self):
        """Test interfaces dict skips ports without wwn"""
        mock_array = Mock()

        # Port without wwn attribute should be skipped
        mock_port = Mock(spec=["name"])  # No wwn attribute
        mock_port.name = "ct0.eth0"

        mock_ports_response = Mock()
        mock_ports_response.items = [mock_port]
        mock_array.get_ports.return_value = mock_ports_response

        result = generate_interfaces_dict(mock_array)

        # Port without wwn should not be included
        assert "ct0.eth0" not in result


class TestGenerateCertsDict:
    """Test cases for generate_certs_dict function"""

    def test_generate_certs_dict_success(self):
        """Test certificates dict generation"""
        mock_array = Mock()

        mock_cert = Mock()
        mock_cert.name = "management"
        mock_cert.status = "valid"
        mock_cert.valid_from = 1609459200000  # 2021-01-01
        mock_cert.valid_to = 1893456000000  # 2030-01-01
        mock_cert.issued_by = "CN=Pure Storage CA"
        mock_cert.issued_to = "CN=array1.example.com"
        mock_cert.key_size = 2048
        mock_cert_type = Mock()
        mock_cert_type.type = "external"
        mock_cert.certificate_type = mock_cert_type

        mock_certs_response = Mock()
        mock_certs_response.items = [mock_cert]
        mock_array.get_certificates.return_value = mock_certs_response

        result = generate_certs_dict(mock_array)

        assert "management" in result
        assert result["management"]["status"] == "valid"
        assert result["management"]["key_size"] == 2048


class TestGenerateKmipDict:
    """Test cases for generate_kmip_dict function"""

    def test_generate_kmip_dict_success(self):
        """Test KMIP dict generation"""
        mock_array = Mock()

        mock_kmip = Mock()
        mock_kmip.name = "kmip-server"
        mock_kmip.uri = "kmip://kmip.example.com:5696"

        mock_kmip_response = Mock()
        mock_kmip_response.items = [mock_kmip]
        mock_array.get_kmip().items = [mock_kmip]

        result = generate_kmip_dict(mock_array)

        assert "kmip-server" in result

    def test_generate_kmip_dict_empty(self):
        """Test KMIP dict generation with no KMIP servers"""
        mock_array = Mock()
        mock_kmip_response = Mock()
        mock_kmip_response.items = []
        mock_array.get_kmip.return_value = mock_kmip_response

        result = generate_kmip_dict(mock_array)

        assert result == {}


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_info.get_array")
    @patch("plugins.modules.purefa_info.AnsibleModule")
    def test_main_invalid_subset(self, mock_ansible_module, mock_get_array):
        """Test main fails with invalid subset"""
        mock_module = Mock()
        mock_module.params = {
            "gather_subset": ["invalid_subset"],
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "gather_subset" in call_args["msg"]

    @patch("plugins.modules.purefa_info.LooseVersion")
    @patch("plugins.modules.purefa_info.generate_default_dict")
    @patch("plugins.modules.purefa_info.get_array")
    @patch("plugins.modules.purefa_info.AnsibleModule")
    def test_main_minimum_subset(
        self, mock_ansible_module, mock_get_array, mock_gen_default, mock_loose_version
    ):
        """Test main with minimum subset"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {
            "gather_subset": ["minimum"],
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        mock_gen_default.return_value = {"api_versions": "2.38"}

        main()

        mock_gen_default.assert_called_once_with(mock_array)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False
        assert "purefa_info" in call_args
        assert "default" in call_args["purefa_info"]

    @patch("plugins.modules.purefa_info.LooseVersion")
    @patch("plugins.modules.purefa_info.generate_perf_dict")
    @patch("plugins.modules.purefa_info.get_array")
    @patch("plugins.modules.purefa_info.AnsibleModule")
    def test_main_performance_subset(
        self, mock_ansible_module, mock_get_array, mock_gen_perf, mock_loose_version
    ):
        """Test main with performance subset"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {
            "gather_subset": ["performance"],
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        mock_gen_perf.return_value = {"reads_per_sec": 500}

        main()

        mock_gen_perf.assert_called_once_with(mock_array)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert "performance" in call_args["purefa_info"]

    @patch("plugins.modules.purefa_info.LooseVersion")
    @patch("plugins.modules.purefa_info.generate_admin_dict")
    @patch("plugins.modules.purefa_info.get_array")
    @patch("plugins.modules.purefa_info.AnsibleModule")
    def test_main_admins_subset(
        self, mock_ansible_module, mock_get_array, mock_gen_admin, mock_loose_version
    ):
        """Test main with admins subset"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {
            "gather_subset": ["admins"],
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        mock_gen_admin.return_value = {"pureuser": {"type": "local"}}

        main()

        mock_gen_admin.assert_called_once_with(mock_array)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert "admins" in call_args["purefa_info"]

    @patch("plugins.modules.purefa_info.LooseVersion")
    @patch("plugins.modules.purefa_info.generate_tgroups_dict")
    @patch("plugins.modules.purefa_info.get_array")
    @patch("plugins.modules.purefa_info.AnsibleModule")
    def test_main_tgroups_subset(
        self, mock_ansible_module, mock_get_array, mock_gen_tgroups, mock_loose_version
    ):
        """Test main with tgroups subset"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {
            "gather_subset": ["tgroups"],
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.54"
        mock_get_array.return_value = mock_array

        mock_gen_tgroups.return_value = {"app-stack": {"arrays": [], "tgroups": []}}

        main()

        mock_gen_tgroups.assert_called_once_with(mock_array)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert "tgroups" in call_args["purefa_info"]


class TestGenerateDefaultDict:
    """Test cases for generate_default_dict function"""

    @patch("plugins.modules.purefa_info.LooseVersion")
    def test_generate_default_dict_success(self, mock_loose_version):
        """Test default dict generation with low API version to skip complex branches"""
        # Return low version to skip encryption and other complex branches
        mock_loose_version.side_effect = lambda x: float(x) if x != "1.0" else 1.0
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        # Mock various array calls - these use getattr(..., "items", [])
        mock_array.get_virtual_machines.return_value = Mock(items=[Mock(), Mock()])
        mock_array.get_virtual_machine_snapshots.return_value = Mock(items=[Mock()])
        mock_array.get_policies_snapshot.return_value = Mock(items=[Mock()])
        mock_array.get_policies_nfs.return_value = Mock(items=[])
        mock_array.get_policies_smb.return_value = Mock(items=[])
        mock_array.get_file_systems.return_value = Mock(items=[])
        mock_array.get_directories.return_value = Mock(items=[Mock()])
        mock_array.get_directory_exports.return_value = Mock(items=[])
        mock_array.get_directory_snapshots.return_value = Mock(items=[])
        # These calls use list(array.get_*().items)
        mock_array.get_volume_groups.return_value = Mock(items=[])
        mock_array.get_array_connections.return_value = Mock(items=[])
        mock_array.get_pods.return_value = Mock(items=[])
        mock_array.get_array_connections_connection_key.return_value = Mock(
            items=[Mock(connection_key="ABC123")]
        )
        # Additional required mocks
        mock_array.get_controllers.return_value = Mock(items=[Mock(model="FA-X70R3")])
        # Create array_data mock properly (name is special for Mock)
        mock_array_data = Mock(version="6.3.0")
        mock_array_data.name = "test-array"  # Set name separately
        mock_array.get_arrays.return_value = Mock(items=[mock_array_data])
        mock_array.get_hosts.return_value = Mock(items=[])
        mock_array.get_volume_snapshots.return_value = Mock(items=[])
        mock_array.get_volumes.return_value = Mock(items=[])
        mock_array.get_protection_groups.return_value = Mock(items=[])
        mock_array.get_host_groups.return_value = Mock(items=[])
        mock_array.get_admins.return_value = Mock(items=[])
        mock_array.get_support.return_value = Mock(
            items=[Mock(remote_assist_status="enabled")]
        )
        mock_array.get_maintenance_windows.return_value = Mock(items=[])
        mock_array.get_fleets.return_value = Mock(status_code=404, items=[])

        result = generate_default_dict(mock_array)

        assert "api_versions" in result
        assert result["api_versions"] == "2.0"
        assert result["snapshot_policies"] == 1
        assert result["directories"] == 1
        assert result["array_name"] == "test-array"


class TestGenerateCapacityDict:
    """Test cases for generate_capacity_dict function"""

    @patch("plugins.modules.purefa_info._is_cbs")
    def test_generate_capacity_dict_success(self, mock_is_cbs):
        """Test capacity dict generation"""
        mock_is_cbs.return_value = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock array capacity
        mock_array_data = Mock(capacity=1099511627776)  # 1TB
        mock_array.get_arrays.return_value = Mock(items=[mock_array_data])

        # Mock space data
        mock_space = Mock()
        mock_space.total_provisioned = 500000000000
        mock_space.total_physical = 300000000000
        mock_space.data_reduction = 2.5
        mock_space.system = 10000000000
        mock_space.unique = 200000000000
        mock_space.shared = 50000000000
        mock_space.snapshots = 40000000000
        mock_space.thin_provisioning = 0.6
        mock_space.total_reduction = 3.0
        mock_space.replication = 0
        mock_space.shared_effective = 50000000000
        mock_space.snapshots_effective = 40000000000
        mock_space.total_effective = 290000000000
        mock_space.used_provisioned = 400000000000
        mock_space.total_used = 350000000000

        mock_capacity = Mock(
            space=mock_space, parity=0.8, capacity_installed=1099511627776
        )
        mock_array.get_arrays_space.return_value = Mock(items=[mock_capacity])

        result = generate_capacity_dict(mock_array)

        assert "total_capacity" in result
        assert result["total_capacity"] == 1099511627776
        assert result["data_reduction"] == 2.5


class TestGenerateSnapDict:
    """Test cases for generate_snap_dict function"""

    def test_generate_snap_dict_success(self):
        """Test snapshot dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock snapshot
        mock_space = Mock()
        mock_space.total_provisioned = 1073741824
        mock_space.snapshots = 536870912
        mock_space.total_physical = 268435456
        mock_space.unique = 134217728
        mock_space.snapshots_effective = 536870912
        mock_space.total_used = 800000000

        mock_snap = Mock()
        mock_snap.name = "vol1.snap1"
        mock_snap.source = Mock(name="vol1")
        mock_snap.created = 1609459200000
        mock_snap.space = mock_space

        mock_array.get_volume_snapshots.return_value = Mock(items=[mock_snap])
        mock_array.get_offloads.return_value = Mock(items=[])
        mock_array.get_volume_snapshots_tags.return_value = Mock(items=[])

        result = generate_snap_dict(mock_array)

        assert "vol1.snap1" in result
        assert result["vol1.snap1"]["is_local"] is True


class TestGenerateDelSnapDict:
    """Test cases for generate_del_snap_dict function"""

    def test_generate_del_snap_dict_success(self):
        """Test deleted snapshot dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.total_provisioned = 1073741824
        mock_space.total_physical = 0
        mock_space.total_used = 0
        mock_space.snapshots = 0
        mock_space.unique = 0

        mock_snap = Mock()
        mock_snap.name = "vol1.deleted_snap"
        mock_snap.source = Mock(name="vol1")
        mock_snap.created = 1609459200000
        mock_snap.time_remaining = 86400000
        mock_snap.space = mock_space

        mock_array.get_volume_snapshots.return_value = Mock(items=[mock_snap])
        mock_array.get_offloads.return_value = Mock(items=[])
        mock_array.get_volume_snapshots_tags.return_value = Mock(items=[])

        result = generate_del_snap_dict(mock_array)

        assert "vol1.deleted_snap" in result


class TestGenerateDelVolDict:
    """Test cases for generate_del_vol_dict function"""

    def test_generate_del_vol_dict_success(self):
        """Test deleted volume dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.total_provisioned = 10737418240
        mock_space.total_physical = 0
        mock_space.total_used = 0
        mock_space.unique = 0
        mock_space.virtual = 0
        mock_space.snapshots = 0
        mock_space.data_reduction = 1.0
        mock_space.thin_provisioning = 0
        mock_space.total_reduction = 1.0
        mock_space.used_provisioned = 0
        mock_space.snapshots_effective = 0
        mock_space.unique_effective = 0

        mock_qos = Mock(bandwidth_limit=0, iops_limit=0)
        mock_priority = Mock()
        mock_priority.priority_adjustment_operator = "+"
        mock_priority.priority_adjustment_value = 0

        mock_vol = Mock()
        mock_vol.name = "deleted_vol"
        mock_vol.provisioned = 10737418240
        mock_vol.source = None
        mock_vol.serial = "ABCD1234567890EF"
        mock_vol.created = 1609459200000
        mock_vol.time_remaining = 86400000
        mock_vol.space = mock_space
        mock_vol.context = None
        mock_vol.subtype = "regular"
        mock_vol.promotion_status = "promoted"
        mock_vol.requested_promotion_state = "promoted"
        mock_vol.host_encryption_key_status = None
        mock_vol.qos = mock_qos
        mock_vol.priority = 50
        mock_vol.priority_adjustment = mock_priority

        mock_array.get_volumes.return_value = Mock(items=[mock_vol])
        mock_array.get_volumes_tags.return_value = Mock(items=[])

        result = generate_del_vol_dict(mock_array)

        assert "deleted_vol" in result


class TestGenerateVolDict:
    """Test cases for generate_vol_dict function"""

    def test_generate_vol_dict_success(self):
        """Test volume dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 100000000
        mock_space.unique = 500000000
        mock_space.virtual = 1000000000
        mock_space.total_physical = 600000000
        mock_space.data_reduction = 2.0
        mock_space.total_reduction = 2.5
        mock_space.total_provisioned = 10737418240
        mock_space.thin_provisioning = 0.6
        mock_space.snapshots_effective = 100000000
        mock_space.unique_effective = 500000000
        mock_space.total_effective = 600000000
        mock_space.used_provisioned = 800000000
        mock_space.total_used = 700000000

        mock_qos = Mock(bandwidth_limit=100000000, iops_limit=10000)
        mock_priority = Mock()
        mock_priority.priority_adjustment_operator = "+"
        mock_priority.priority_adjustment_value = 10

        mock_vol = Mock()
        mock_vol.name = "test_vol"
        mock_vol.subtype = "regular"
        mock_vol.provisioned = 10737418240
        mock_vol.source = None
        mock_vol.created = 1609459200000
        mock_vol.serial = "ABCD1234567890EF"
        mock_vol.promotion_status = "promoted"
        mock_vol.requested_promotion_state = "promoted"
        mock_vol.qos = mock_qos
        mock_vol.space = mock_space
        mock_vol.host_encryption_key_status = None
        mock_vol.priority = 50
        mock_vol.priority_adjustment = mock_priority
        mock_vol.protocol_endpoint = None

        mock_array.get_volumes.return_value = Mock(items=[mock_vol])
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.get_volumes_tags.return_value = Mock(items=[])

        result = generate_vol_dict(mock_array, performance=False)

        assert "test_vol" in result
        assert result["test_vol"]["serial"] == "ABCD1234567890EF"
        assert result["test_vol"]["size"] == 10737418240


class TestGenerateHostDict:
    """Test cases for generate_host_dict function"""

    def test_generate_host_dict_success(self):
        """Test host dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_chap = Mock(host_user=None, target_user=None)
        mock_host = Mock()
        mock_host.name = "test_host"
        mock_host.host_group = None
        mock_host.nqns = None
        mock_host.iqns = ["iqn.2021-01.com.example:host1"]
        mock_host.wwns = None
        mock_host.personality = "linux"
        mock_host.chap = mock_chap
        mock_host.preferred_arrays = {}
        mock_host.is_local = True
        mock_host.port_connectivity = Mock(details={})
        mock_host.destroyed = False
        mock_host.time_remaining = None
        mock_host.vlan = None

        mock_array.get_hosts.return_value = Mock(items=[mock_host])
        mock_array.get_hosts_performance_balance.return_value = Mock(items=[])
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.get_hosts_tags.return_value = Mock(items=[])
        mock_array.get_ports_initiators.return_value = Mock(items=[])

        result = generate_host_dict(mock_array, performance=False)

        assert "test_host" in result
        assert result["test_host"]["personality"] == "linux"
        assert result["test_host"]["logged_in_ports"] == {
            "iqn.2021-01.com.example:host1": []
        }

    def test_generate_host_dict_preferred_arrays(self):
        """preferred_arrays is a list of Reference objects, not a dict"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        pref1 = Mock()
        pref1.name = "arrayA"
        pref2 = Mock()
        pref2.name = "arrayB"

        mock_host = Mock()
        mock_host.name = "sync_host"
        mock_host.host_group = None
        mock_host.nqns = None
        mock_host.iqns = None
        mock_host.wwns = None
        mock_host.personality = None
        mock_host.chap = Mock(host_user=None, target_user=None)
        mock_host.preferred_arrays = [pref1, pref2]
        mock_host.is_local = True
        mock_host.port_connectivity = Mock(details={})
        mock_host.destroyed = False
        mock_host.time_remaining = None
        mock_host.vlan = None

        mock_array.get_hosts.return_value = Mock(items=[mock_host])
        mock_array.get_hosts_performance_balance.return_value = Mock(items=[])
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.get_hosts_tags.return_value = Mock(items=[])
        mock_array.get_ports_initiators.return_value = Mock(items=[])

        result = generate_host_dict(mock_array, performance=False)

        assert result["sync_host"]["preferred_array"] == ["arrayA", "arrayB"]

    def test_generate_host_dict_logged_in_ports(self):
        """Test logged_in_ports maps each WWN to the target ports it uses"""

        def _login(init_wwn, target_name):
            login = Mock()
            login.target = Mock()
            login.target.name = target_name
            login.initiator = Mock()
            login.initiator.wwn = init_wwn
            login.initiator.iqn = None
            login.initiator.nqn = None
            return login

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_host = Mock()
        mock_host.name = "fc_host"
        mock_host.host_group = None
        mock_host.nqns = None
        mock_host.iqns = None
        mock_host.wwns = ["52:4A:93:00:00:00:00:01", "52:4A:93:00:00:00:00:02"]
        mock_host.personality = None
        mock_host.chap = Mock(host_user=None, target_user=None)
        mock_host.preferred_arrays = {}
        mock_host.is_local = True
        mock_host.port_connectivity = Mock(details={})
        mock_host.destroyed = False
        mock_host.time_remaining = None
        mock_host.vlan = None

        mock_array.get_hosts.return_value = Mock(items=[mock_host])
        mock_array.get_hosts_performance_balance.return_value = Mock(items=[])
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.get_hosts_tags.return_value = Mock(items=[])
        # First WWN logged into two ports (lower-case/colon variant to prove
        # normalisation); second WWN not logged in anywhere.
        mock_array.get_ports_initiators.return_value = Mock(
            items=[
                _login("52:4a:93:00:00:00:00:01", "CT1.FC1"),
                _login("52:4a:93:00:00:00:00:01", "CT0.FC1"),
            ]
        )

        result = generate_host_dict(mock_array, performance=False)

        logged = result["fc_host"]["logged_in_ports"]
        assert logged["52:4A:93:00:00:00:00:01"] == ["CT0.FC1", "CT1.FC1"]
        assert logged["52:4A:93:00:00:00:00:02"] == []


class TestGeneratePgroupsDict:
    """Test cases for generate_pgroups_dict function"""

    def test_generate_pgroups_dict_success(self):
        """Test protection groups dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 100000000
        mock_space.shared = 50000000
        mock_space.data_reduction = 2.0
        mock_space.thin_provisioning = 0.5
        mock_space.total_physical = 150000000
        mock_space.total_provisioned = 500000000
        mock_space.total_reduction = 2.5
        mock_space.unique = 100000000
        mock_space.virtual = 200000000
        mock_space.replication = 0
        mock_space.used_provisioned = 200000000

        mock_snap_sched = Mock(frequency=3600, enabled=True, at=None)
        mock_repl_sched = Mock(
            frequency=86400, enabled=False, at=None, blackout=Mock(start=None, end=None)
        )
        mock_source_ret = Mock(per_day=2, days=7, all_for_sec=86400)
        mock_target_ret = Mock(per_day=1, days=30, all_for_sec=86400)

        mock_pgroup = Mock()
        mock_pgroup.name = "pg1"
        mock_pgroup.source = Mock(name="local")
        mock_pgroup.snapshot_schedule = mock_snap_sched
        mock_pgroup.replication_schedule = mock_repl_sched
        mock_pgroup.source_retention = mock_source_ret
        mock_pgroup.target_retention = mock_target_ret
        mock_pgroup.space = mock_space

        mock_array.get_protection_groups.return_value = Mock(items=[mock_pgroup])
        mock_array.get_protection_group_snapshots_transfer.return_value = Mock(
            status_code=200, items=[]
        )
        mock_array.get_protection_groups_volumes.return_value = Mock(items=[])
        mock_array.get_protection_groups_hosts.return_value = Mock(items=[])
        mock_array.get_protection_groups_host_groups.return_value = Mock(items=[])
        mock_array.get_protection_groups_targets.return_value = Mock(items=[])
        mock_array.get_protection_groups_tags.return_value = Mock(items=[])

        result = generate_pgroups_dict(mock_array)

        assert "pg1" in result
        assert result["pg1"]["snap_enabled"] is True


class TestGenerateDelPgroupsDict:
    """Test cases for generate_del_pgroups_dict function"""

    def test_generate_del_pgroups_dict_success(self):
        """Test deleted protection groups dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 0
        mock_space.shared = 0
        mock_space.data_reduction = 1.0
        mock_space.thin_provisioning = 0
        mock_space.total_physical = 0
        mock_space.total_provisioned = 0
        mock_space.total_reduction = 1.0
        mock_space.unique = 0
        mock_space.virtual = 0
        mock_space.replication = 0
        mock_space.used_provisioned = 0

        mock_snap_sched = Mock(frequency=3600, enabled=False, at=None)
        mock_repl_sched = Mock(
            frequency=86400, enabled=False, at=None, blackout=Mock(start=None, end=None)
        )
        mock_source_ret = Mock(per_day=0, days=0, all_for_sec=0)
        mock_target_ret = Mock(per_day=0, days=0, all_for_sec=0)

        mock_pgroup = Mock()
        mock_pgroup.name = "deleted_pg"
        mock_pgroup.source = Mock(name="local")
        mock_pgroup.time_remaining = 86400000
        mock_pgroup.snapshot_schedule = mock_snap_sched
        mock_pgroup.replication_schedule = mock_repl_sched
        mock_pgroup.source_retention = mock_source_ret
        mock_pgroup.target_retention = mock_target_ret
        mock_pgroup.space = mock_space
        mock_pgroup.eradication_config = Mock(manual_eradication=False)
        mock_pgroup.retention_lock = None

        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pgroup]
        )
        mock_array.get_protection_group_snapshots_transfer.return_value = Mock(
            status_code=200, items=[]
        )
        mock_array.get_protection_groups_volumes.return_value = Mock(items=[])
        mock_array.get_protection_groups_hosts.return_value = Mock(items=[])
        mock_array.get_protection_groups_host_groups.return_value = Mock(items=[])
        mock_array.get_protection_groups_targets.return_value = Mock(items=[])
        mock_array.get_protection_groups_tags.return_value = Mock(items=[])

        result = generate_del_pgroups_dict(mock_array)

        assert "deleted_pg" in result


class TestGeneratePodsDict:
    """Test cases for generate_pods_dict function"""

    def test_generate_pods_dict_success(self):
        """Test pods dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 100000000
        mock_space.shared = 50000000
        mock_space.data_reduction = 2.0
        mock_space.thin_provisioning = 0.5
        mock_space.total_physical = 150000000
        mock_space.total_provisioned = 500000000
        mock_space.total_reduction = 2.5
        mock_space.unique = 100000000
        mock_space.virtual = 200000000
        mock_space.replication = 0
        mock_space.used_provisioned = 200000000
        mock_space.total_used = 300000000

        mock_array_member = Mock()
        mock_array_member.id = "array-id-1"
        mock_array_member.member = Mock(name="array1", resource_type="arrays")
        mock_array_member.pre_elected = True
        mock_array_member.status = "online"
        mock_array_member.mediator_status = "online"
        mock_array_member.progress = None
        mock_array_member.frozen_at = 1609459200000  # Integer timestamp

        mock_pod = Mock()
        mock_pod.name = "pod1"
        mock_pod.mediator = "mediator.example.com"
        mock_pod.mediator_version = "1.0.0"
        mock_pod.link_source_count = 0
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"
        mock_pod.requested_promotion_state = "promoted"
        mock_pod.failover_preferences = []  # Empty list is iterable
        mock_pod.arrays = [mock_array_member]
        mock_pod.space = mock_space
        mock_pod.quota_limit = None
        mock_pod.source = None

        mock_array.get_pods.return_value = Mock(items=[mock_pod])
        mock_array.get_pods_tags.return_value = Mock(items=[])
        mock_array.get_pods_performance.return_value = Mock(items=[])

        result = generate_pods_dict(mock_array, performance=False)

        assert "pod1" in result
        assert result["pod1"]["mediator"] == "mediator.example.com"


class TestGenerateDelPodsDict:
    """Test cases for generate_del_pods_dict function"""

    def test_generate_del_pods_dict_success(self):
        """Test deleted pods dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 0
        mock_space.shared = 0
        mock_space.data_reduction = 1.0
        mock_space.thin_provisioning = 0
        mock_space.total_physical = 0
        mock_space.total_provisioned = 0
        mock_space.total_reduction = 1.0
        mock_space.unique = 0
        mock_space.virtual = 0
        mock_space.replication = 0
        mock_space.used_provisioned = 0
        mock_space.total_used = 0

        mock_pod = Mock()
        mock_pod.name = "deleted_pod"
        mock_pod.time_remaining = 86400000
        mock_pod.mediator = None
        mock_pod.mediator_version = None
        mock_pod.link_source_count = 0
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "demoted"
        mock_pod.requested_promotion_state = "demoted"
        mock_pod.failover_preferences = []  # Must be iterable
        mock_pod.arrays = []  # Must be iterable
        mock_pod.space = mock_space
        mock_pod.quota_limit = None

        mock_array.get_pods.return_value = Mock(items=[mock_pod])
        mock_array.get_pods_tags.return_value = Mock(items=[])

        result = generate_del_pods_dict(mock_array)

        assert "deleted_pod" in result


class TestGenerateHgroupsDict:
    """Test cases for generate_hgroups_dict function"""

    def test_generate_hgroups_dict_success(self):
        """Test host groups dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 100000000
        mock_space.data_reduction = 2.0
        mock_space.thin_provisioning = 0.5
        mock_space.total_physical = 150000000
        mock_space.total_provisioned = 500000000
        mock_space.total_reduction = 2.5
        mock_space.unique = 100000000
        mock_space.virtual = 200000000
        mock_space.used_provisioned = 200000000
        mock_space.total_used = 300000000

        mock_hgroup = Mock()
        mock_hgroup.name = "hg1"
        mock_hgroup.is_local = True
        mock_hgroup.space = mock_space
        mock_hgroup.destroyed = False
        mock_hgroup.time_remaining = None

        mock_array.get_host_groups.return_value = Mock(items=[mock_hgroup])
        mock_array.get_host_groups_tags.return_value = Mock(items=[])
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.get_host_groups_hosts.return_value = Mock(items=[])
        mock_array.get_host_groups_protection_groups.return_value = Mock(items=[])

        result = generate_hgroups_dict(mock_array, performance=False)

        assert "hg1" in result
        assert result["hg1"]["destroyed"] is False


class TestGenerateVgroupsDict:
    """Test cases for generate_vgroups_dict function"""

    def test_generate_vgroups_dict_success(self):
        """Test volume groups dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 100000000
        mock_space.data_reduction = 2.0
        mock_space.thin_provisioning = 0.5
        mock_space.total_physical = 150000000
        mock_space.total_provisioned = 500000000
        mock_space.total_reduction = 2.5
        mock_space.unique = 100000000
        mock_space.virtual = 200000000
        mock_space.used_provisioned = 200000000
        mock_space.total_used = 300000000

        mock_qos = Mock(bandwidth_limit=100000000, iops_limit=10000)
        mock_priority = Mock()
        mock_priority.priority_adjustment_operator = "+"
        mock_priority.priority_adjustment_value = 0

        mock_vgroup = Mock()
        mock_vgroup.name = "vg1"
        mock_vgroup.space = mock_space
        mock_vgroup.qos = mock_qos
        mock_vgroup.priority_adjustment = mock_priority

        mock_array.get_volume_groups.return_value = Mock(items=[mock_vgroup])
        mock_array.get_volume_groups_tags.return_value = Mock(items=[])
        mock_array.get_volume_groups_volumes.return_value = Mock(items=[])

        result = generate_vgroups_dict(mock_array, performance=False)

        assert "vg1" in result
        assert result["vg1"]["volumes"] == []  # volumes is a list, not volume_count


class TestGenerateDelVgroupsDict:
    """Test cases for generate_del_vgroups_dict function"""

    def test_generate_del_vgroups_dict_success(self):
        """Test deleted volume groups dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 0
        mock_space.unique = 0
        mock_space.virtual = 0
        mock_space.data_reduction = 1.0
        mock_space.total_reduction = 1.0
        mock_space.total_provisioned = 0
        mock_space.thin_provisioning = 0
        mock_space.used_provisioned = 0
        mock_space.total_used = 0

        mock_qos = Mock(bandwidth_limit=0, iops_limit=0)
        mock_priority = Mock()
        mock_priority.priority_adjustment_operator = "+"
        mock_priority.priority_adjustment_value = 0

        mock_vgroup = Mock()
        mock_vgroup.name = "deleted_vg"
        mock_vgroup.time_remaining = 86400000
        mock_vgroup.space = mock_space
        mock_vgroup.qos = mock_qos
        mock_vgroup.priority_adjustment = mock_priority

        mock_array.get_volume_groups.return_value = Mock(items=[mock_vgroup])
        mock_array.get_volume_groups_tags.return_value = Mock(items=[])
        mock_array.get_volume_groups_volumes.return_value = Mock(items=[])

        result = generate_del_vgroups_dict(mock_array)

        assert "deleted_vg" in result


class TestGenerateAppsDict:
    """Test cases for generate_apps_dict function"""

    def test_generate_apps_dict_success(self):
        """Test apps dict generation"""
        mock_array = Mock()

        mock_app = Mock()
        mock_app.name = "test_app"
        mock_app.description = "Test Application"
        mock_app.enabled = True
        mock_app.status = "healthy"
        mock_app.version = "1.0.0"

        # Mock get_apps().items to return a list
        mock_array.get_apps.return_value = Mock(items=[mock_app])
        # Mock get_apps_nodes().items to return a list with app_node
        mock_app_node = Mock()
        mock_app_node.name = "test_app"
        mock_app_node.index = 0
        mock_app_node.vnc = None
        mock_array.get_apps_nodes.return_value = Mock(items=[mock_app_node])

        result = generate_apps_dict(mock_array)

        assert "test_app" in result
        assert result["test_app"]["status"] == "healthy"


class TestGenerateConnArrayDict:
    """Test cases for generate_conn_array_dict function"""

    def test_generate_conn_array_dict_success(self):
        """Test connected arrays dict generation"""
        mock_array = Mock()

        mock_conn = Mock()
        mock_conn.name = "remote-array"
        mock_conn.id = "array-id-123"
        mock_conn.status = "connected"
        mock_conn.version = "6.3.0"
        mock_conn.replication_transport = "ip"
        mock_conn.management_address = "10.0.0.100"
        mock_conn.replication_addresses = ["10.0.1.100"]

        mock_array.get_array_connections.return_value = Mock(items=[mock_conn])

        result = generate_conn_array_dict(mock_array)

        assert "remote-array" in result
        assert result["remote-array"]["status"] == "connected"


class TestGenerateNetworkDict:
    """Test cases for generate_network_dict function"""

    def test_generate_network_dict_success(self):
        """Test network dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # The function checks port.interface_type and uses port.eth for eth interfaces
        mock_eth = Mock()
        mock_eth.mac_address = "00:50:56:ab:cd:ef"
        mock_eth.mtu = 1500
        mock_eth.address = "10.0.0.10"
        mock_eth.gateway = "10.0.0.1"
        mock_eth.netmask = "255.255.255.0"
        mock_eth.subtype = "virtual"
        mock_eth.vlan = None
        mock_eth.subinterfaces = []
        mock_eth.subnet = Mock(name="mgmt-subnet")

        mock_port = Mock()
        mock_port.name = "ct0.eth0"
        mock_port.interface_type = "eth"
        mock_port.enabled = True
        mock_port.speed = 10000000000
        mock_port.services = ["management"]
        mock_port.eth = mock_eth

        mock_array.get_network_interfaces.return_value = Mock(items=[mock_port])
        mock_array.get_network_interfaces_performance.return_value = Mock(items=[])
        mock_array.get_network_interfaces_neighbors.return_value = Mock(items=[])

        result = generate_network_dict(mock_array, performance=False)

        assert "ct0.eth0" in result
        assert result["ct0.eth0"]["address"] == "10.0.0.10"


class TestGenerateRlDict:
    """Test cases for generate_rl_dict function"""

    def test_generate_rl_dict_success(self):
        """Test replica links dict generation"""
        mock_array = Mock()

        mock_link = Mock()
        mock_link.local_pod = Mock(name="local_pod")
        mock_link.remote_pod = Mock(name="remote_pod")
        mock_link.remotes = [Mock(name="remote_array")]  # Must be a list
        mock_link.status = "replicating"
        mock_link.direction = "outbound"
        mock_link.recovery_point = 1609459200000
        mock_link.lag = 1000  # Integer, not Mock
        mock_link.paused = False

        mock_array.get_pod_replica_links.return_value = Mock(items=[mock_link])

        result = generate_rl_dict(mock_array)

        assert len(result) > 0


class TestGenerateOffloadDicts:
    """Test cases for offload dict generation functions"""

    def test_generate_nfs_offload_dict_success(self):
        """Test NFS offload dict generation"""
        mock_array = Mock()

        mock_offload = Mock()
        mock_offload.name = "nfs-offload-1"
        mock_offload.status = "connected"
        mock_offload.nfs = Mock(
            mount_point="/backup",
            mount_options="rw,sync",
            address="nfs.example.com",
            profile=None,
        )
        mock_offload.space = Mock(total_physical=1000000000, virtual=2000000000)
        mock_offload.protocol = "nfs"

        # get_offloads returns a response with status_code and items
        mock_array.get_offloads.return_value = Mock(
            status_code=200, items=[mock_offload]
        )

        result = generate_nfs_offload_dict(mock_array)

        assert "nfs-offload-1" in result
        assert result["nfs-offload-1"]["status"] == "connected"

    def test_generate_s3_offload_dict_success(self):
        """Test S3 offload dict generation"""
        mock_array = Mock()

        mock_offload = Mock()
        mock_offload.name = "s3-offload-1"
        mock_offload.status = "connected"
        mock_offload.s3 = Mock(
            bucket="my-bucket",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            uri=None,
            auth_region=None,
            profile=None,
            placement_strategy="array-wide",
        )
        mock_offload.space = Mock(total_physical=1000000000, virtual=2000000000)
        mock_offload.protocol = "s3"

        mock_array.get_offloads.return_value = Mock(
            status_code=200, items=[mock_offload]
        )

        result = generate_s3_offload_dict(mock_array)

        assert "s3-offload-1" in result
        assert result["s3-offload-1"]["bucket"] == "my-bucket"

    def test_generate_azure_offload_dict_success(self):
        """Test Azure offload dict generation"""
        mock_array = Mock()

        mock_offload = Mock()
        mock_offload.name = "azure-offload-1"
        mock_offload.status = "connected"
        mock_offload.azure = Mock(
            container_name="backup-container",
            account_name="mystorageaccount",
            secret_access_key=None,
            profile=None,
        )
        mock_offload.space = Mock(total_physical=1000000000, virtual=2000000000)
        mock_offload.protocol = "azure"

        mock_array.get_offloads.return_value = Mock(
            status_code=200, items=[mock_offload]
        )

        result = generate_azure_offload_dict(mock_array)

        assert "azure-offload-1" in result
        assert result["azure-offload-1"]["container_name"] == "backup-container"

    def test_generate_google_offload_dict_success(self):
        """Test Google Cloud offload dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_offload = Mock()
        mock_offload.name = "gcs-offload-1"
        mock_offload.status = "connected"
        mock_offload.google_cloud = Mock(bucket="gcs-backup-bucket", profile=None)
        mock_offload.space = Mock(total_physical=1000000000, virtual=2000000000)
        mock_offload.protocol = "google-cloud"

        mock_array.get_offloads.return_value = Mock(
            status_code=200, items=[mock_offload]
        )

        result = generate_google_offload_dict(mock_array)

        assert "gcs-offload-1" in result
        assert result["gcs-offload-1"]["bucket"] == "gcs-backup-bucket"


class TestGenerateVmDict:
    """Test cases for generate_vm_dict function"""

    def test_generate_vm_dict_success(self):
        """Test virtual machines dict generation"""
        mock_array = Mock()

        mock_vm = Mock()
        mock_vm.name = "vm1"
        mock_vm.vm_type = "vvol"
        mock_vm.vm_id = "vm-12345"
        mock_vm.destroyed = False
        mock_vm.created = 1609459200000
        mock_vm.time_remaining = None
        mock_vm.recover_context = Mock(name="snap1", id="snap-id-1")

        mock_array.get_virtual_machines.return_value = Mock(items=[mock_vm])

        result = generate_vm_dict(mock_array)

        assert "vm1" in result
        assert result["vm1"]["vm_type"] == "vvol"


class TestGenerateVmsnapDict:
    """Test cases for generate_vmsnap_dict function"""

    def test_generate_vmsnap_dict_success(self):
        """Test VM snapshots dict generation"""
        mock_array = Mock()

        mock_snap = Mock()
        mock_snap.name = "vm1.snap1"
        mock_snap.vm_type = "vvol"
        mock_snap.vm_id = "vm-12345"
        mock_snap.destroyed = False
        mock_snap.created = 1609459200000
        mock_snap.time_remaining = None

        mock_array.get_virtual_machine_snapshots.return_value = Mock(items=[mock_snap])

        result = generate_vmsnap_dict(mock_array)

        assert "vm1.snap1" in result


class TestGenerateAlertsDict:
    """Test cases for generate_alerts_dict function"""

    def test_generate_alerts_dict_success(self):
        """Test alerts dict generation"""
        mock_array = Mock()

        mock_alert = Mock()
        mock_alert.name = "alert-001"
        mock_alert.severity = "warning"
        mock_alert.category = "hardware"
        mock_alert.state = "open"
        mock_alert.flagged = False
        mock_alert.issue = "Component degraded"
        mock_alert.code = 1001
        mock_alert.actual = "degraded"
        mock_alert.expected = "healthy"
        mock_alert.component_name = "CT0.FC0"
        mock_alert.component_type = "port"
        mock_alert.knowledge_base_url = "https://kb.example.com/1001"
        mock_alert.summary = "Alert summary"
        mock_alert.id = "alert-id-001"
        # Timestamps must be integers for division operations
        mock_alert.notified = 1609459200000
        mock_alert.closed = 1609545600000
        mock_alert.updated = 1609459200000
        mock_alert.created = 1609459200000

        mock_array.get_alerts.return_value = Mock(items=[mock_alert])

        result = generate_alerts_dict(mock_array)

        assert "alert-001" in result
        assert result["alert-001"]["severity"] == "warning"


class TestGenerateSubsDict:
    """Test cases for generate_subs_dict function"""

    def test_generate_subs_dict_success(self):
        """Test subscriptions dict generation"""
        mock_array = Mock()

        mock_sub = Mock()
        mock_sub.name = "subscription-asset-1"
        mock_sub.subscription = Mock(id="sub-id-123")

        # Function uses get_subscription_assets not get_subscriptions
        mock_array.get_subscription_assets.return_value = Mock(items=[mock_sub])

        result = generate_subs_dict(mock_array)

        assert "subscription-asset-1" in result
        assert result["subscription-asset-1"]["subscription_id"] == "sub-id-123"


class TestGenerateFleetDict:
    """Test cases for generate_fleet_dict function"""

    def test_generate_fleet_dict_success(self):
        """Test fleet dict generation"""
        mock_array = Mock()

        # Fleet info is only returned if there's a fleet
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"

        mock_member = Mock()
        mock_member.member = Mock(name="fleet-member-1")
        mock_member.status = "healthy"
        mock_member.status_details = None

        # Need both get_fleets() and get_fleets_members()
        mock_fleet = Mock()
        mock_fleet.name = "test-fleet"
        mock_array.get_fleets.return_value = Mock(items=[mock_fleet])
        mock_array.get_fleets_members.return_value = Mock(items=[mock_member])

        result = generate_fleet_dict(mock_array)

        assert "test-fleet" in result
        assert "members" in result["test-fleet"]


class TestGenerateTgroupsDict:
    """Test cases for generate_tgroups_dict function"""

    def test_generate_tgroups_dict_success(self):
        """Test topology groups dict generation"""
        from types import SimpleNamespace

        mock_array = Mock()

        mock_tgroup = SimpleNamespace(
            name="app-stack",
            id="tg-1",
            context=SimpleNamespace(name="array-a"),
            parent_topology_group=SimpleNamespace(name="parent-stack"),
        )
        array_member = SimpleNamespace(
            topology_group=SimpleNamespace(name="app-stack"),
            member=SimpleNamespace(name="array-b", resource_type="remote-arrays"),
            status="joined",
            status_details="",
        )
        child_member = SimpleNamespace(
            topology_group=SimpleNamespace(name="app-stack"),
            member=SimpleNamespace(
                name="app-stack-dev", resource_type="topology-groups"
            ),
            status="joined",
            status_details="",
        )

        mock_array.get_topology_groups.return_value = Mock(items=[mock_tgroup])
        mock_array.get_topology_groups_members.return_value = Mock(
            items=[array_member, child_member]
        )

        result = generate_tgroups_dict(mock_array)

        assert "app-stack" in result
        assert result["app-stack"]["id"] == "tg-1"
        assert result["app-stack"]["context"] == "array-a"
        assert result["app-stack"]["parent_topology_group"] == "parent-stack"
        assert result["app-stack"]["arrays"] == [
            {"name": "array-b", "status": "joined", "status_details": ""}
        ]
        assert result["app-stack"]["tgroups"] == [
            {
                "name": "app-stack-dev",
                "status": "joined",
                "status_details": "",
            }
        ]


class TestGeneratePresetDict:
    """Test cases for generate_preset_dict function"""

    def test_generate_preset_dict_success(self):
        """Test preset dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_preset = Mock()
        mock_preset.name = "preset-1"
        mock_preset.description = "Test preset"
        mock_preset.workload_type = "database"
        mock_preset.revision = 1
        mock_preset.context = None
        mock_preset.parameters = []
        mock_preset.volume_configurations = []
        mock_preset.placement_configurations = []
        mock_preset.qos_configurations = []
        mock_preset.snapshot_configurations = []
        mock_preset.periodic_replication_configurations = []
        mock_preset.workload_tags = []

        # Return response without errors attribute (or errors=None)
        mock_response = Mock()
        mock_response.errors = None
        mock_response.items = [mock_preset]
        mock_array.get_presets_workload.return_value = mock_response

        result = generate_preset_dict(mock_array)

        assert "preset-1" in result
        assert result["preset-1"]["workload_type"] == "database"


class TestGenerateWorkloadDict:
    """Test cases for generate_workload_dict function"""

    def test_generate_workload_dict_success(self):
        """Test workload dict generation"""
        mock_array = Mock()

        mock_workload = Mock()
        mock_workload.name = "workload-1"
        mock_workload.description = "Test Workload"
        mock_workload.context = Mock(name="context-1")
        mock_workload.destroyed = False
        mock_workload.preset = Mock(name="preset-1")
        mock_workload.status = "healthy"
        mock_workload.status_details = None
        mock_workload.created = 1609459200000  # Timestamp must be integer
        mock_workload.time_remaining = None

        mock_array.get_workloads.return_value = Mock(items=[mock_workload])

        result = generate_workload_dict(mock_array)

        assert "workload-1" in result
        assert result["workload-1"]["status"] == "healthy"


class TestGenerateRealmsDict:
    """Test cases for generate_realms_dict function"""

    def test_generate_realms_dict_success(self):
        """Test realms dict generation"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_space = Mock()
        mock_space.snapshots = 100000000
        mock_space.total_physical = 150000000
        mock_space.total_provisioned = 500000000
        mock_space.unique = 100000000
        mock_space.virtual = 200000000
        mock_space.total_used = 300000000
        mock_space.data_reduction = 2.0
        mock_space.thin_provisioning = 0.5
        mock_space.total_reduction = 2.5
        mock_space.shared = 50000000
        mock_space.used_provisioned = 200000000
        mock_space.footprint = 250000000

        mock_qos = Mock(bandwidth_limit=100000000, iops_limit=10000)

        mock_realm = Mock()
        mock_realm.name = "realm-1"
        mock_realm.quota_limit = None
        mock_realm.space = mock_space
        mock_realm.qos = mock_qos
        mock_realm.created = 1609459200000  # Timestamp must be integer
        mock_realm.destroyed = False

        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        mock_array.get_realms_tags.return_value = Mock(items=[])
        mock_array.get_realms_performance.return_value = Mock(items=[])

        result = generate_realms_dict(mock_array, performance=False)

        assert "realm-1" in result
        assert result["realm-1"]["destroyed"] is False


class TestGenerateConfigDict:
    """Test cases for generate_config_dict function"""

    @patch("plugins.modules.purefa_info.LooseVersion", side_effect=LooseVersion)
    def test_generate_config_dict_success(self, mock_lv):
        """Test generate_config_dict returns expected config info"""
        mock_module = Mock()
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock array info
        mock_array_info = Mock()
        mock_array_info.console_lock_enabled = True
        mock_array.get_arrays.return_value = Mock(items=[mock_array_info])

        # Mock alert watchers
        mock_watcher = Mock()
        mock_watcher.name = "admin@example.com"
        mock_watcher.enabled = True
        mock_array.get_alert_watchers.return_value = Mock(items=[mock_watcher])

        # Mock SNMP managers
        mock_snmp_manager = Mock()
        mock_snmp_manager.name = "snmp-manager-1"
        mock_snmp_manager.host = "192.168.1.100"
        mock_snmp_manager.version = "v3"
        mock_snmp_manager.v3 = Mock(
            user="snmpuser",
            auth_password="***",
            auth_protocol="SHA",
            privacy_password="***",
            privacy_protocol="AES",
        )
        mock_snmp_manager.v2c = Mock(community=None)
        mock_snmp_manager.notification = "trap"
        mock_array.get_snmp_managers.return_value = Mock(items=[mock_snmp_manager])

        # Mock SNMP agent
        mock_snmp_agent = Mock()
        mock_snmp_agent.name = "snmp-agent"
        mock_snmp_agent.version = "v3"
        mock_snmp_agent.engine_id = "engine123"
        mock_snmp_agent.v3 = Mock(
            user="agent-user",
            auth_password=None,
            auth_protocol=None,
            privacy_password=None,
            privacy_protocol=None,
        )
        mock_snmp_agent.v2c = Mock(community=None)
        mock_snmp_agent.notification = None
        mock_array.get_snmp_agents.return_value = Mock(items=[mock_snmp_agent])

        # Mock SMTP servers
        mock_smtp = Mock()
        mock_smtp.name = "smtp-server"
        mock_smtp.password = ""
        mock_smtp.user_name = ""
        mock_smtp.encryption_mode = "starttls"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.sender_domain = "example.com"
        mock_array.get_smtp_servers.return_value = Mock(items=[mock_smtp])

        # Mock directory services
        mock_ds = Mock()
        mock_ds.name = "management"
        mock_ds.base_dn = "dc=example,dc=com"
        mock_ds.bind_user = "admin"
        mock_ds.enabled = True
        mock_ds.services = ["management"]
        mock_ds.uris = ["ldap://ldap.example.com"]
        mock_array.get_directory_services.return_value = Mock(items=[mock_ds])

        # Mock directory service roles
        mock_role = Mock()
        mock_role.role = Mock(name="array_admin")
        mock_role.group = "admins"
        mock_role.group_base = "ou=groups"
        mock_role.management_access_policies = [Mock(name="policy1")]
        mock_array.get_directory_services_roles.return_value = Mock(items=[mock_role])

        # Mock SMI-S
        mock_smis = Mock()
        mock_smis.slp_enabled = True
        mock_smis.wbem_https_enabled = True
        mock_array.get_smi_s.return_value = Mock(items=[mock_smis])

        # Mock DNS
        mock_dns = Mock()
        mock_dns.services = ["management"]
        mock_dns.nameservers = ["8.8.8.8"]
        mock_dns.domain = "example.com"
        mock_dns.source = Mock(name="ct0.eth0")
        mock_array.get_dns.return_value = Mock(items=[mock_dns])

        # Mock SAML2 (not available in older versions)
        mock_array.get_sso_saml2_idps.return_value = Mock(items=[])

        # Mock NTP
        mock_ntp = Mock()
        mock_ntp.ntp_servers = ["time.google.com"]
        mock_ntp.source = Mock(name="ct0.eth0")
        mock_array.get_arrays_ntp_test.return_value = Mock(status_code=400)
        mock_array_info.ntp_symmetric_key = None
        mock_array_info.time_zone = "UTC"
        mock_array.get_arrays.return_value = Mock(items=[mock_array_info])

        # Mock container default protections - must return iterable
        mock_array.get_container_default_protections.return_value = Mock(items=[])

        # Mock syslog servers
        mock_array.get_syslog_servers.return_value = Mock(items=[])

        # Mock support info
        mock_support = Mock()
        mock_support.phonehome_enabled = True
        mock_support.proxy = ""
        mock_array.get_support.return_value = Mock(items=[mock_support])

        # Mock array info with idle/scsi timeout
        mock_array_info.idle_timeout = 600000
        mock_array_info.scsi_timeout = 30000

        # Mock admin settings
        mock_admin_settings = Mock()
        mock_admin_settings.lockout_duration = 0
        mock_admin_settings.max_login_attempts = 5
        mock_admin_settings.min_password_length = 8
        mock_admin_settings.single_sign_on_enabled = False
        mock_array.get_admins_settings.return_value = Mock(items=[mock_admin_settings])

        result = generate_config_dict(mock_module, mock_array)

        assert "console_lock" in result
        assert result["console_lock"] == "enabled"
        assert "smtp" in result
        assert "snmp" in result


class TestGenerateFilesystemsDict:
    """Test cases for generate_filesystems_dict function"""

    @patch("plugins.modules.purefa_info.LooseVersion", side_effect=LooseVersion)
    def test_generate_filesystems_dict_success(self, mock_lv):
        """Test generate_filesystems_dict returns expected filesystem info"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock filesystem
        mock_fs = Mock()
        mock_fs.name = "fs1"
        mock_fs.destroyed = False
        mock_array.get_file_systems.return_value = Mock(items=[mock_fs])

        # Mock directory
        mock_dir = Mock()
        mock_dir.name = "fs1:dir1"
        mock_dir.directory_name = "dir1"
        mock_dir.path = "/fs1/dir1"
        mock_dir.destroyed = False
        mock_dir.space = Mock(
            data_reduction=2.5,
            snapshots=1000,
            thin_provisioning=0.8,
            total_physical=2000,
            total_provisioned=5000,
            total_reduction=3.0,
            total_used=1500,
            unique=1200,
            virtual=4000,
            used_provisioned=3000,
        )
        mock_dir.limited_by = None
        mock_array.get_directories.return_value = Mock(items=[mock_dir])

        # Mock policies
        mock_array.get_directories_policies.return_value = Mock(items=[])

        # Mock exports
        mock_array.get_directory_exports.return_value = Mock(items=[])

        # Mock performance
        mock_array.get_directories_performance.return_value = Mock(items=[])

        result = generate_filesystems_dict(mock_array, performance=False)

        assert "fs1" in result
        assert result["fs1"]["destroyed"] is False
        assert "directories" in result["fs1"]


class TestGeneratePgsnapsDict:
    """Test cases for generate_pgsnaps_dict function"""

    def test_generate_pgsnaps_dict_success(self):
        """Test generate_pgsnaps_dict returns expected snapshot info"""
        mock_array = Mock()

        # Mock protection group snapshot
        mock_snap = Mock()
        mock_snap.name = "pgroup1.snap1"
        mock_snap.destroyed = False
        mock_source = Mock()
        mock_source.name = "pgroup1"
        mock_snap.source = mock_source
        mock_snap.suffix = "snap1"
        mock_snap.space = Mock(snapshots=5000, used_provisioned=3000)
        mock_snap.eradication_config = Mock(manual_eradication="all-enabled")
        mock_array.get_protection_group_snapshots.return_value = Mock(items=[mock_snap])

        result = generate_pgsnaps_dict(mock_array)

        assert "pgroup1.snap1" in result
        assert result["pgroup1.snap1"]["destroyed"] is False
        assert result["pgroup1.snap1"]["source"] == "pgroup1"
        assert result["pgroup1.snap1"]["suffix"] == "snap1"


class TestGenerateDirSnapsDict:
    """Test cases for generate_dir_snaps_dict function"""

    @patch("plugins.modules.purefa_info.LooseVersion", side_effect=LooseVersion)
    def test_generate_dir_snaps_dict_success(self, mock_lv):
        """Test generate_dir_snaps_dict returns expected snapshot info"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock directory snapshot
        mock_snap = Mock()
        mock_snap.name = "fs1:dir1.snap1"
        mock_snap.destroyed = False
        mock_source = Mock()
        mock_source.name = "fs1:dir1"
        mock_snap.source = mock_source
        mock_snap.suffix = "snap1"
        mock_snap.client_name = "client1"
        mock_snap.space = Mock(
            snapshots=1000,
            total_physical=2000,
            unique=1500,
            used_provisioned=1800,
            total_used=1600,
        )
        mock_policy = Mock()
        mock_policy.name = "snap-policy1"
        mock_snap.policy = mock_policy
        mock_snap.time_remaining = None
        mock_array.get_directory_snapshots.return_value = Mock(items=[mock_snap])

        result = generate_dir_snaps_dict(mock_array)

        assert "fs1:dir1.snap1" in result
        assert result["fs1:dir1.snap1"]["destroyed"] is False
        assert result["fs1:dir1.snap1"]["source"] == "fs1:dir1"


class TestGeneratePoliciesDict:
    """Test cases for generate_policies_dict function"""

    def test_generate_policies_dict_success(self):
        """Test generate_policies_dict returns expected policy info"""
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock policy - using snapshot type to avoid NFS-specific code paths
        mock_policy = Mock()
        mock_policy.name = "snap-policy1"
        mock_policy.policy_type = "snapshot"
        mock_policy.enabled = True
        mock_array.get_policies.return_value = Mock(items=[mock_policy])

        # Mock directories_policies (for policy members) - must return iterable
        mock_array.get_directories_policies.return_value = Mock(items=[])

        # Mock snapshot rules
        mock_rule = Mock()
        mock_rule.at = 3600000  # 1:00
        mock_rule.client_name = "client1"
        mock_rule.every = 3600000  # 60 mins
        mock_rule.keep_for = 86400000  # 24 hours
        mock_rule.suffix = "hourly"
        mock_array.get_policies_snapshot_rules.return_value = Mock(items=[mock_rule])

        result = generate_policies_dict(
            mock_array,
            quota_available=False,
            autodir_available=False,
            nfs_user_mapping=False,
        )

        assert "snap-policy1" in result
        assert result["snap-policy1"]["type"] == "snapshot"
        assert result["snap-policy1"]["enabled"] is True


class TestGenerateClientsDict:
    """Test cases for generate_clients_dict function"""

    def test_generate_clients_dict_success(self):
        """Test generate_clients_dict returns expected API client info"""
        mock_array = Mock()

        # Mock API client
        mock_client = Mock()
        mock_client.name = "api-client-1"
        mock_client.enabled = True
        mock_client.id = "client-id-123"
        mock_client.key_id = "key-id-456"
        mock_client.issuer = "pure-storage"
        mock_client.max_role = "array_admin"
        mock_client.access_token_ttl_in_ms = 3600000
        mock_client.public_key = "ssh-rsa AAAA..."
        mock_client.access_policies = [Mock(name="full-access")]
        mock_array.get_api_clients.return_value = Mock(items=[mock_client])

        result = generate_clients_dict(mock_array)

        assert "api-client-1" in result
        assert result["api-client-1"]["enabled"] is True
        assert result["api-client-1"]["client_id"] == "client-id-123"
        assert result["api-client-1"]["access_token_ttl_seconds"] == 3600


class TestGenerateSoftwareDict:
    """Tests for generate_software_dict"""

    @staticmethod
    def _array(**responses):
        array = Mock()
        for name, value in responses.items():
            getattr(array, name).return_value = value
        return array

    def test_each_endpoint_guarded_on_its_own_version(self):
        """Test an array too old for one endpoint still reports the others

        The three endpoints arrived in 2.2, 2.9 and 2.17, so a single floor
        would hide data an older array can serve.
        """
        from plugins.modules.purefa_info import generate_software_dict

        step = Mock()
        step.id = "step-1"
        step.name = "pre-upgrade check"
        step.status = "finished"
        step.checks = []
        array = self._array(
            get_software_installation_steps=Mock(status_code=200, items=[step]),
        )

        out = generate_software_dict(array, "2.2")

        assert list(out["installation_steps"]) == ["step-1"]
        assert out["versions"] == {}
        assert out["patches"] == {}
        array.get_software_versions.assert_not_called()
        array.get_software_patches_catalog.assert_not_called()

    def test_all_three_on_a_current_array(self):
        from plugins.modules.purefa_info import generate_software_dict

        version = Mock()
        version.name = "6.10.6"
        patch = Mock()
        patch.name = "patch-1"
        step = Mock()
        step.id = "step-1"
        step.checks = []
        array = self._array(
            get_software_versions=Mock(status_code=200, items=[version]),
            get_software_patches_catalog=Mock(status_code=200, items=[patch]),
            get_software_installation_steps=Mock(status_code=200, items=[step]),
        )

        out = generate_software_dict(array, "2.56")

        assert list(out["versions"]) == ["6.10.6"]
        assert list(out["patches"]) == ["patch-1"]
        assert list(out["installation_steps"]) == ["step-1"]

    def test_installation_steps_keyed_on_id_not_name(self):
        """Step names repeat across upgrades, so the id is the key"""
        from plugins.modules.purefa_info import generate_software_dict

        first, second = Mock(), Mock()
        first.id, second.id = "a", "b"
        first.name = second.name = "pre-upgrade check"
        first.checks = second.checks = []
        array = self._array(
            get_software_installation_steps=Mock(
                status_code=200, items=[first, second]
            ),
        )

        out = generate_software_dict(array, "2.2")

        assert sorted(out["installation_steps"]) == ["a", "b"]

    def test_a_failed_read_is_not_fatal(self):
        from plugins.modules.purefa_info import generate_software_dict

        array = self._array(
            get_software_versions=Mock(status_code=400, items=[]),
            get_software_patches_catalog=Mock(status_code=400, items=[]),
            get_software_installation_steps=Mock(status_code=400, items=[]),
        )

        out = generate_software_dict(array, "2.56")

        assert out == {"versions": {}, "patches": {}, "installation_steps": {}}


class TestGenerateSupportDict:
    """Tests for generate_support_dict"""

    @staticmethod
    def _manifest_array(raw):
        array = Mock()
        item = Mock()
        item.system_manifest = raw
        array.get_support_system_manifest.return_value = Mock(
            status_code=200, items=[item]
        )
        array.get_support_diagnostics_details.return_value = Mock(
            status_code=200, items=[]
        )
        return array

    def test_manifest_is_summarised_not_copied(self):
        """Test only the header fields are kept

        The manifest is a single JSON document of tens of kilobytes, so the
        bulk of it is deliberately left out.
        """
        import json

        from plugins.modules.purefa_info import generate_support_dict

        raw = json.dumps(
            {
                "manifest_version": 1.0,
                "purity_version": "6.10.6",
                "array_name": "arrayone",
                "components": [{"a": 1}, {"b": 2}, {"c": 3}],
                "licensed_features": ["one"],
                "space": {"lots": "of detail"},
            }
        )

        out = generate_support_dict(self._manifest_array(raw), "2.56")

        assert out["manifest"]["purity_version"] == "6.10.6"
        assert out["manifest"]["array_name"] == "arrayone"
        assert out["manifest"]["component_count"] == 3
        assert out["manifest"]["raw_length"] == len(raw)
        # the bulky members are not carried through
        assert "components" not in out["manifest"]
        assert "space" not in out["manifest"]

    def test_unparseable_manifest_does_not_raise(self):
        from plugins.modules.purefa_info import generate_support_dict

        out = generate_support_dict(self._manifest_array("not json at all"), "2.56")

        assert out["manifest"]["purity_version"] is None
        assert out["manifest"]["raw_length"] == len("not json at all")

    def test_manifest_skipped_on_an_older_array(self):
        from plugins.modules.purefa_info import generate_support_dict

        array = self._manifest_array("{}")

        out = generate_support_dict(array, "2.40")

        assert out["manifest"] == {}
        array.get_support_system_manifest.assert_not_called()
        array.get_support_diagnostics_details.assert_called_once()

    def test_diagnostics_keyed_on_test_name(self):
        from plugins.modules.purefa_info import generate_support_dict

        diag = Mock()
        diag.test_name = "a check"
        diag.test_type = "hardware"
        diag.severity = "info"
        diag.result_details = "all good"
        array = Mock()
        array.get_support_diagnostics_details.return_value = Mock(
            status_code=200, items=[diag]
        )
        array.get_support_system_manifest.return_value = Mock(status_code=200, items=[])

        out = generate_support_dict(array, "2.56")

        assert out["diagnostics"]["a check"]["severity"] == "info"


class FakeModel:
    """Stands in for an SDK model, including its habit of raising on null"""

    def __init__(self, **fields):
        self._values = fields
        type(self).__fields__ = {k: None for k in fields}

    def __getattr__(self, name):
        values = self.__dict__.get("_values", {})
        if name in values:
            if values[name] is _NULL:
                raise AttributeError(name)
            return values[name]
        raise AttributeError(name)


_NULL = object()


class TestPlain:
    """Tests for _plain, which keeps SDK objects out of the module result"""

    def test_primitives_pass_through(self):
        from plugins.modules.purefa_info import _plain

        for value in (None, True, 1, 1.5, "text"):
            assert _plain(value) == value

    def test_nested_model_becomes_a_dict(self):
        """An SDK model cannot be serialised, so it has to be walked

        This is what took the replication gather down twice: lag is an object,
        and so is each of a pod's replication rates.
        """
        from plugins.modules.purefa_info import _plain

        lag = FakeModel(avg=1500, max=1500)

        assert _plain(lag) == {"avg": 1500, "max": 1500}

    def test_reference_reduces_to_its_name(self):
        from plugins.modules.purefa_info import _plain

        assert _plain(FakeModel(id="abc", name="pod1")) == "pod1"

    def test_null_field_does_not_raise(self):
        from plugins.modules.purefa_info import _plain

        assert _plain(FakeModel(avg=1, max=_NULL)) == {"avg": 1, "max": None}

    def test_lists_are_walked(self):
        from plugins.modules.purefa_info import _plain

        out = _plain([FakeModel(id="a", name="one"), FakeModel(id="b", name="two")])

        assert out == ["one", "two"]


class TestDirectoryQuotas:
    """Tests for add_directory_quotas"""

    @staticmethod
    def _files_info():
        return {"fs1": {"directories": {"dir1": {}}}}

    @staticmethod
    def _array(**responses):
        array = Mock()
        empty = Mock(status_code=200, items=[])
        for name in (
            "get_directory_quotas",
            "get_directory_user_quotas",
            "get_directory_group_quotas",
            "get_directories_users",
            "get_directories_groups",
        ):
            getattr(array, name).return_value = responses.get(name, empty)
        return array

    def test_quota_lands_on_the_right_directory(self):
        """A quota names its directory as filesystem colon directory"""
        from plugins.modules.purefa_info import add_directory_quotas

        quota = Mock()
        quota.directory = Mock()
        quota.directory.name = "fs1:dir1"
        quota.quota_limit = 1024
        quota.usage = 512
        quota.policy = Mock()
        quota.policy.name = "pol1"
        files_info = self._files_info()

        add_directory_quotas(
            self._array(get_directory_quotas=Mock(status_code=200, items=[quota])),
            files_info,
            "2.56",
        )

        quotas = files_info["fs1"]["directories"]["dir1"]["quotas"]
        assert len(quotas) == 1
        assert quotas[0]["quota_limit"] == 1024
        assert quotas[0]["policy"] == "pol1"

    def test_a_quota_for_an_unreported_directory_is_dropped(self):
        """Test a row that matches nothing does not invent a directory"""
        from plugins.modules.purefa_info import add_directory_quotas

        quota = Mock()
        quota.directory = Mock()
        quota.directory.name = "otherfs:otherdir"
        files_info = self._files_info()

        add_directory_quotas(
            self._array(get_directory_quotas=Mock(status_code=200, items=[quota])),
            files_info,
            "2.56",
        )

        assert files_info == {"fs1": {"directories": {"dir1": {}}}}

    def test_identity_views_skipped_on_an_older_array(self):
        """The user and group views arrived in 2.44"""
        from plugins.modules.purefa_info import add_directory_quotas

        array = self._array()

        add_directory_quotas(array, self._files_info(), "2.40")

        array.get_directory_quotas.assert_called_once()
        array.get_directory_user_quotas.assert_not_called()
        array.get_directories_users.assert_not_called()


class TestReplicationPerf:
    """Tests for generate_replication_perf_dict"""

    @staticmethod
    def _array(**responses):
        array = Mock()
        empty = Mock(status_code=200, items=[])
        for name in (
            "get_pod_replica_links_lag",
            "get_pod_replica_links_performance_replication",
            "get_pods_performance_replication",
            "get_protection_groups_performance_replication",
            "get_remote_protection_group_snapshots_transfer",
            "get_volume_snapshots_transfer",
        ):
            getattr(array, name).return_value = responses.get(name, empty)
        return array

    def test_lag_and_throughput_merge_on_the_same_link(self):
        """Both come from separate endpoints keyed on the same link id"""
        from plugins.modules.purefa_info import generate_replication_perf_dict

        lag = Mock()
        lag.id = "link-1"
        lag.lag = FakeModel(avg=1500, max=1500)
        throughput = Mock()
        throughput.id = "link-1"
        throughput.bytes_per_sec_total = 99

        out = generate_replication_perf_dict(
            self._array(
                get_pod_replica_links_lag=Mock(status_code=200, items=[lag]),
                get_pod_replica_links_performance_replication=Mock(
                    status_code=200, items=[throughput]
                ),
            ),
            "2.56",
        )

        link = out["pod_replica_links"]["link-1"]
        assert link["lag"] == {"avg": 1500, "max": 1500}
        assert link["bytes_per_sec_total"] == 99

    def test_local_and_remote_transfers_are_distinguished(self):
        from plugins.modules.purefa_info import generate_replication_perf_dict

        remote, local = Mock(), Mock()
        remote.name = "pgroup.snap"
        local.name = "vol.snap"

        out = generate_replication_perf_dict(
            self._array(
                get_remote_protection_group_snapshots_transfer=Mock(
                    status_code=200, items=[remote]
                ),
                get_volume_snapshots_transfer=Mock(status_code=200, items=[local]),
            ),
            "2.56",
        )

        assert out["snapshot_transfers"]["pgroup.snap"]["remote"] is True
        assert out["snapshot_transfers"]["vol.snap"]["remote"] is False

    def test_a_failed_read_is_not_fatal(self):
        from plugins.modules.purefa_info import generate_replication_perf_dict

        array = self._array(
            get_pod_replica_links_lag=Mock(status_code=400, items=[]),
            get_pods_performance_replication=Mock(status_code=400, items=[]),
        )

        out = generate_replication_perf_dict(array, "2.56")

        assert out["pod_replica_links"] == {}
        assert out["pods"] == {}
