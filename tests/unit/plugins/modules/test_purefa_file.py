# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_file module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock, patch

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
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.common"] = (
    MagicMock()
)
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.error_handlers"
] = MagicMock()

# Create a mock version module with real LooseVersion
mock_version_module = MagicMock()
from packaging.version import Version as LooseVersion

mock_version_module.LooseVersion = LooseVersion
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    mock_version_module
)

from plugins.modules.purefa_file import (
    _check_dirs,
)


class TestCheckDirs:
    """Tests for _check_dirs function"""

    def test_check_dirs_success(self):
        """Test _check_dirs when both directories exist"""
        mock_module = Mock()
        mock_module.params = {"source_dir": "src_dir", "target_dir": "tgt_dir"}
        mock_array = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_array.get_directories.return_value = mock_response

        # Should not raise any errors
        _check_dirs(mock_module, mock_array)

        assert mock_array.get_directories.call_count == 2

    @patch("plugins.modules.purefa_file.check_response")
    def test_check_dirs_source_not_found(self, mock_check_response):
        """Test _check_dirs when source directory doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"source_dir": "missing_src", "target_dir": "tgt_dir"}
        mock_array = Mock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_array.get_directories.return_value = mock_response

        _check_dirs(mock_module, mock_array)

        mock_check_response.assert_called()

    @patch("plugins.modules.purefa_file.check_response")
    def test_check_dirs_target_not_found(self, mock_check_response):
        """Test _check_dirs when target directory doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"source_dir": "src_dir", "target_dir": "missing_tgt"}
        mock_array = Mock()
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response2 = Mock()
        mock_response2.status_code = 400
        mock_array.get_directories.side_effect = [mock_response1, mock_response2]

        _check_dirs(mock_module, mock_array)

        assert mock_array.get_directories.call_count == 2
        mock_check_response.assert_called()


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_file.get_array")
    @patch("plugins.modules.purefa_file.AnsibleModule")
    @patch("plugins.modules.purefa_file.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        """Test main fails when SDK is missing"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "source_file": "test.txt",
            "source_dir": "fs::dir1",
            "target_file": "copy.txt",
            "target_dir": "fs::dir2",
            "overwrite": False,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        from plugins.modules.purefa_file import main

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "py-pure-client sdk" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_file.get_array")
    @patch("plugins.modules.purefa_file.AnsibleModule")
    @patch("plugins.modules.purefa_file.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_file.LooseVersion")
    def test_main_api_version_too_low(
        self, mock_loose_version, mock_ansible_module, mock_get_array
    ):
        """Test main fails when API version is too low"""
        import pytest

        mock_loose_version.side_effect = lambda x: float(x) if "." in x else float(x)

        mock_module = Mock()
        mock_module.params = {
            "source_file": "test.txt",
            "source_dir": "fs::dir1",
            "target_file": "copy.txt",
            "target_dir": "fs::dir2",
            "overwrite": False,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Too old
        mock_get_array.return_value = mock_array

        from plugins.modules.purefa_file import main

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "REST version not supported" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_file.get_array")
    @patch("plugins.modules.purefa_file.AnsibleModule")
    @patch("plugins.modules.purefa_file.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_file.LooseVersion")
    def test_main_target_dir_bad_format(
        self, mock_loose_version, mock_ansible_module, mock_get_array
    ):
        """Test main fails when target directory format is wrong"""
        import pytest

        mock_loose_version.side_effect = lambda x: float(x) if "." in x else float(x)

        mock_module = Mock()
        mock_module.params = {
            "source_file": "test.txt",
            "source_dir": "fs::dir1",
            "target_file": "copy.txt",
            "target_dir": "bad_format",  # Missing ":"
            "overwrite": False,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        from plugins.modules.purefa_file import main

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "Target Directory" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_file.get_array")
    @patch("plugins.modules.purefa_file.AnsibleModule")
    @patch("plugins.modules.purefa_file.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_file.LooseVersion")
    def test_main_source_dir_bad_format(
        self, mock_loose_version, mock_ansible_module, mock_get_array
    ):
        """Test main fails when source directory format is wrong"""
        import pytest

        mock_loose_version.side_effect = lambda x: float(x) if "." in x else float(x)

        mock_module = Mock()
        mock_module.params = {
            "source_file": "test.txt",
            "source_dir": "bad_format",  # Missing ":"
            "target_file": "copy.txt",
            "target_dir": "fs::dir2",
            "overwrite": False,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        from plugins.modules.purefa_file import main

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "Source Directory" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_file._check_dirs")
    @patch("plugins.modules.purefa_file.get_array")
    @patch("plugins.modules.purefa_file.AnsibleModule")
    @patch("plugins.modules.purefa_file.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_file.LooseVersion")
    def test_main_check_mode(
        self, mock_loose_version, mock_ansible_module, mock_get_array, mock_check_dirs
    ):
        """Test main in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if "." in x else float(x)

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "source_file": "test.txt",
            "source_dir": "fs::dir1",
            "target_file": "copy.txt",
            "target_dir": "fs::dir2",
            "overwrite": False,
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        from plugins.modules.purefa_file import main

        main()

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.post_files.assert_not_called()

    @patch("plugins.modules.purefa_file.check_response")
    @patch("plugins.modules.purefa_file._check_dirs")
    @patch("plugins.modules.purefa_file.flasharray")
    @patch("plugins.modules.purefa_file.get_array")
    @patch("plugins.modules.purefa_file.AnsibleModule")
    @patch("plugins.modules.purefa_file.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_file.LooseVersion")
    def test_main_copy_file_success(
        self,
        mock_loose_version,
        mock_ansible_module,
        mock_get_array,
        mock_flasharray,
        mock_check_dirs,
        mock_check_response,
    ):
        """Test main successfully copies file"""
        mock_loose_version.side_effect = lambda x: float(x) if "." in x else float(x)

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "source_file": "test.txt",
            "source_dir": "fs::dir1",
            "target_file": "copy.txt",
            "target_dir": "fs::dir2",
            "overwrite": False,
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_array.post_files.return_value = Mock(status_code=200)
        mock_get_array.return_value = mock_array

        from plugins.modules.purefa_file import main

        main()

        mock_array.post_files.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)
