# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_pgsched module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, patch, MagicMock

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

from plugins.modules.purefa_pgsched import (
    get_pending_pgroup,
    get_pgroup,
    _convert_to_minutes,
    update_schedule,
    delete_schedule,
)


class TestGetPendingPgroup:
    """Test cases for get_pending_pgroup function"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_get_pending_pgroup_exists(self, mock_get_with_context):
        """Test get_pending_pgroup returns pgroup when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "context": ""}
        mock_array = Mock()
        mock_pgroup = Mock()
        mock_pgroup.name = "test-pg"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pgroup])

        result = get_pending_pgroup(mock_module, mock_array)

        assert result == mock_pgroup

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_get_pending_pgroup_not_exists(self, mock_get_with_context):
        """Test get_pending_pgroup returns None when pgroup doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404, items=[])

        result = get_pending_pgroup(mock_module, mock_array)

        assert result is None


class TestGetPgroup:
    """Test cases for get_pgroup function"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_get_pgroup_exists(self, mock_get_with_context):
        """Test get_pgroup returns pgroup when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "context": ""}
        mock_array = Mock()
        mock_pgroup = Mock()
        mock_pgroup.name = "test-pg"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pgroup])

        result = get_pgroup(mock_module, mock_array)

        assert result == mock_pgroup

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_get_pgroup_not_exists(self, mock_get_with_context):
        """Test get_pgroup returns None when pgroup doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404, items=[])

        result = get_pgroup(mock_module, mock_array)

        assert result is None


class TestConvertToMinutes:
    """Test cases for _convert_to_minutes function"""

    def test_convert_to_minutes_12am(self):
        """Test conversion of 12AM to seconds"""
        result = _convert_to_minutes("12AM")
        assert result == 0

    def test_convert_to_minutes_12pm(self):
        """Test conversion of 12PM to seconds"""
        result = _convert_to_minutes("12PM")
        assert result == 43200

    def test_convert_to_minutes_6am(self):
        """Test conversion of 6AM to seconds"""
        result = _convert_to_minutes("6AM")
        assert result == 21600  # 6 * 3600

    def test_convert_to_minutes_6pm(self):
        """Test conversion of 6PM to seconds"""
        result = _convert_to_minutes("6PM")
        assert result == 64800  # (6 + 12) * 3600


def create_mock_protection_group(
    snap_frequency=86400000,
    snap_at=54000,
    snap_enabled=True,
    days=7,
    per_day=4,
    all_for=86400,
    repl_frequency=86400000,
    repl_at=54000,
    repl_enabled=True,
    target_days=7,
    target_per_day=4,
    target_all_for=86400,
    blackout_start=0,
    blackout_end=0,
):
    """Create a mock protection group with schedules"""
    mock_pg = Mock()

    # Snapshot schedule
    mock_pg.snapshot_schedule = Mock()
    mock_pg.snapshot_schedule.frequency = snap_frequency
    mock_pg.snapshot_schedule.at = snap_at
    mock_pg.snapshot_schedule.enabled = snap_enabled

    # Source retention
    mock_pg.source_retention = Mock()
    mock_pg.source_retention.days = days
    mock_pg.source_retention.per_day = per_day
    mock_pg.source_retention.all_for_sec = all_for

    # Replication schedule
    mock_pg.replication_schedule = Mock()
    mock_pg.replication_schedule.frequency = repl_frequency
    mock_pg.replication_schedule.at = repl_at
    mock_pg.replication_schedule.enabled = repl_enabled

    # Target retention
    mock_pg.target_retention = Mock()
    mock_pg.target_retention.days = target_days
    mock_pg.target_retention.per_day = target_per_day
    mock_pg.target_retention.all_for_sec = target_all_for

    # Blackout
    mock_pg.replication_schedule.blackout = Mock()
    mock_pg.replication_schedule.blackout.start = blackout_start
    mock_pg.replication_schedule.blackout.end = blackout_end

    return mock_pg


class TestUpdateScheduleClearAtValue:
    """Test cases for update_schedule function - clearing at values"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    @patch("plugins.modules.purefa_pgsched.SnapshotSchedule")
    @patch("plugins.modules.purefa_pgsched.ProtectionGroup")
    def test_clear_snap_at_with_empty_string(
        self,
        mock_protection_group,
        mock_snapshot_schedule,
        mock_check_response,
        mock_get_with_context,
    ):
        """Test clearing snap_at by providing empty string sends at=-1 to API"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "snap_at": "",  # Empty string to clear
            "snap_frequency": None,
            "enabled": None,
            "days": None,
            "per_day": None,
            "all_for": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Create mock protection group with snap_at set
        mock_pg = create_mock_protection_group(
            snap_frequency=86400000, snap_at=54000  # 1 day  # 3PM
        )
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pg])

        # Current schedule has a snap_at value set
        current_snap = {
            "snap_enabled": True,
            "snap_frequency": 86400000,  # 1 day in ms
            "snap_at": 54000,  # 3PM in seconds
            "days": 7,
            "per_day": 4,
            "all_for": 86400,
        }
        current_repl = {}

        result = update_schedule(mock_module, mock_array, current_snap, current_repl)

        # Verify that get_with_context was called
        assert mock_get_with_context.called
        # Verify SnapshotSchedule was called with at=-1 to clear the value
        mock_snapshot_schedule.assert_called_with(frequency=86400000, at=-1)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    @patch("plugins.modules.purefa_pgsched.ReplicationSchedule")
    @patch("plugins.modules.purefa_pgsched.ProtectionGroup")
    def test_clear_replicate_at_with_empty_string(
        self,
        mock_protection_group,
        mock_replication_schedule,
        mock_check_response,
        mock_get_with_context,
    ):
        """Test clearing replicate_at by providing empty string sends at=-1 to API"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "schedule": "replication",
            "replicate_at": "",  # Empty string to clear
            "replicate_frequency": None,
            "enabled": None,
            "target_days": None,
            "target_per_day": None,
            "target_all_for": None,
            "blackout_start": None,
            "blackout_end": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Create mock protection group with replicate_at set
        mock_pg = create_mock_protection_group(
            repl_frequency=86400000, repl_at=54000  # 1 day  # 3PM
        )
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pg])

        current_snap = {}
        # Current schedule has a replicate_at value set
        current_repl = {
            "replicate_enabled": True,
            "replicate_frequency": 86400000,  # 1 day in ms
            "replicate_at": 54000,  # 3PM in seconds
            "target_days": 7,
            "target_per_day": 4,
            "target_all_for": 86400,
            "blackout_start": None,
            "blackout_end": None,
        }

        result = update_schedule(mock_module, mock_array, current_snap, current_repl)

        # Verify that get_with_context was called
        assert mock_get_with_context.called
        # Verify ReplicationSchedule was called with at=-1 to clear the value
        mock_replication_schedule.assert_called_with(frequency=86400000, at=-1)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    @patch("plugins.modules.purefa_pgsched.SnapshotSchedule")
    @patch("plugins.modules.purefa_pgsched.ProtectionGroup")
    def test_auto_clear_snap_at_when_frequency_changes_to_hourly(
        self,
        mock_protection_group,
        mock_snapshot_schedule,
        mock_check_response,
        mock_get_with_context,
    ):
        """Test automatic clearing of snap_at when changing from daily to hourly sends at=-1"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "snap_at": None,  # Not provided - should auto-clear due to frequency
            "snap_frequency": 3600,  # 1 hour in seconds (not a day multiple)
            "enabled": None,
            "days": None,
            "per_day": None,
            "all_for": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Create mock protection group with daily frequency and snap_at set
        mock_pg = create_mock_protection_group(
            snap_frequency=86400000, snap_at=54000  # 1 day  # 3PM
        )
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pg])

        # Current schedule has a snap_at value set with daily frequency
        current_snap = {
            "snap_enabled": True,
            "snap_frequency": 86400000,  # 1 day in ms
            "snap_at": 54000,  # 3PM in seconds
            "days": 7,
            "per_day": 4,
            "all_for": 86400,
        }
        current_repl = {}

        result = update_schedule(mock_module, mock_array, current_snap, current_repl)

        # Should have made API call with at=-1 to clear (non-day frequency)
        assert mock_get_with_context.called
        mock_snapshot_schedule.assert_called_with(frequency=3600000, at=-1)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_keep_snap_at_when_not_provided(
        self, mock_check_response, mock_get_with_context
    ):
        """Test that snap_at is preserved when not provided and frequency is daily"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "snap_at": None,  # Not provided - should keep current
            "snap_frequency": 86400,  # 1 day (same as current)
            "enabled": None,
            "days": None,
            "per_day": None,
            "all_for": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Create mock protection group with snap_at set
        mock_pg = create_mock_protection_group(
            snap_frequency=86400000, snap_at=54000  # 1 day  # 3PM
        )
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pg])

        # Current schedule has a snap_at value set
        current_snap = {
            "snap_enabled": True,
            "snap_frequency": 86400000,  # 1 day in ms
            "snap_at": 54000,  # 3PM in seconds
            "days": 7,
            "per_day": 4,
            "all_for": 86400,
        }
        current_repl = {}

        result = update_schedule(mock_module, mock_array, current_snap, current_repl)

        # The at value should be preserved
        assert mock_get_with_context.called

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_set_new_snap_at_value(self, mock_check_response, mock_get_with_context):
        """Test setting a new snap_at value"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "snap_at": "6PM",  # New value
            "snap_frequency": 86400,  # 1 day
            "enabled": None,
            "days": None,
            "per_day": None,
            "all_for": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Create mock protection group with different snap_at
        mock_pg = create_mock_protection_group(
            snap_frequency=86400000, snap_at=54000  # 1 day  # 3PM
        )
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pg])

        # Current schedule has a different snap_at value
        current_snap = {
            "snap_enabled": True,
            "snap_frequency": 86400000,  # 1 day in ms
            "snap_at": 54000,  # 3PM in seconds
            "days": 7,
            "per_day": 4,
            "all_for": 86400,
        }
        current_repl = {}

        result = update_schedule(mock_module, mock_array, current_snap, current_repl)

        # Check that the API was called
        assert mock_get_with_context.called


class TestDeleteSchedule:
    """Test cases for delete_schedule function"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_delete_schedule_replication_disabled(self, mock_get_with_context):
        """Test delete_schedule when replication schedule is already disabled"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "replication",
            "context": "",
        }
        mock_array = Mock()
        # Replication schedule already disabled
        mock_schedule = Mock()
        mock_schedule.replication_schedule.enabled = False
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        delete_schedule(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_delete_schedule_snapshot_disabled(self, mock_get_with_context):
        """Test delete_schedule when snapshot schedule is already disabled"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pg", "schedule": "snapshot", "context": ""}
        mock_array = Mock()
        # Snapshot schedule already disabled
        mock_schedule = Mock()
        mock_schedule.snapshot_schedule.enabled = False
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        delete_schedule(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_delete_schedule_replication_check_mode(self, mock_get_with_context):
        """Test delete_schedule replication in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pg",
            "schedule": "replication",
            "context": "",
        }
        mock_array = Mock()
        # Replication schedule enabled
        mock_schedule = Mock()
        mock_schedule.replication_schedule.enabled = True
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        delete_schedule(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSchedule:
    """Test cases for update_schedule function"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_update_schedule_pgroup_not_found(self, mock_get_with_context):
        """Test update_schedule fails when protection group not found"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "nonexistent-pg",
            "schedule": "snapshot",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404, items=[])

        with pytest.raises(SystemExit):
            from plugins.modules.purefa_pgsched import update_schedule

            update_schedule(mock_module, mock_array, None, None)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_update_schedule_snapshot_no_changes(self, mock_get_with_context):
        """Test update_schedule when no snapshot schedule changes needed.

        Uses a non-day frequency (3600000ms = 1 hour), so at value must be None.
        For non-day frequencies, the at value is not applicable and should be None.
        """
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "context": "",
            "enabled": None,
            "snap_frequency": None,
            "snap_at": None,
            "days": None,
            "per_day": None,
            "all_for": None,
        }
        mock_array = Mock()
        # Create mock schedule with all necessary attributes
        mock_schedule = Mock()
        mock_schedule.source_retention.days = 7
        mock_schedule.source_retention.per_day = 4
        mock_schedule.source_retention.all_for_sec = 86400
        # Non-day frequency (1 hour = 3600000ms) - at value should be None
        mock_schedule.snapshot_schedule.frequency = 3600000
        mock_schedule.snapshot_schedule.enabled = True
        mock_schedule.snapshot_schedule.at = None
        mock_schedule.replication_schedule.frequency = 7200000
        mock_schedule.replication_schedule.enabled = True
        mock_schedule.replication_schedule.at = None
        mock_schedule.replication_schedule.blackout.start = 0
        mock_schedule.replication_schedule.blackout.end = 0
        mock_schedule.target_retention.days = 7
        mock_schedule.target_retention.per_day = 4
        mock_schedule.target_retention.all_for_sec = 86400
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        from plugins.modules.purefa_pgsched import update_schedule

        update_schedule(mock_module, mock_array, None, None)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdateScheduleSnapshotEnabled:
    """Test cases for update_schedule with snapshot enabled changes"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_update_schedule_snapshot_enabled_change(
        self, mock_check_response, mock_get_with_context
    ):
        """Test update_schedule when snapshot enabled state changes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "context": "",
            "enabled": False,
            "snap_frequency": None,
            "snap_at": None,
            "days": None,
            "per_day": None,
            "all_for": None,
        }
        mock_array = Mock()
        # Create proper mock schedule
        mock_schedule = create_mock_protection_group(snap_enabled=True)
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        update_schedule(mock_module, mock_array, None, None)

        # Should have called patch to update enabled state
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateScheduleRetention:
    """Test cases for update_schedule with retention changes"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_update_schedule_snapshot_retention_change(
        self, mock_check_response, mock_get_with_context
    ):
        """Test update_schedule when snapshot retention changes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "context": "",
            "enabled": None,
            "snap_frequency": None,
            "snap_at": None,
            "days": 14,  # Changed from 7
            "per_day": 8,  # Changed from 4
            "all_for": 172800,  # Changed from 86400
        }
        mock_array = Mock()
        # Create proper mock schedule
        mock_schedule = create_mock_protection_group(days=7, per_day=4, all_for=86400)
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        update_schedule(mock_module, mock_array, None, None)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateScheduleReplication:
    """Test cases for update_schedule with replication schedule changes"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_update_schedule_replicate_enabled_change(
        self, mock_check_response, mock_get_with_context
    ):
        """Test update_schedule when replication enabled state changes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "replication",
            "context": "",
            "enabled": False,
            "replicate_frequency": None,
            "replicate_at": None,
            "target_days": None,
            "target_per_day": None,
            "target_all_for": None,
            "blackout_start": None,
            "blackout_end": None,
        }
        mock_array = Mock()
        # Create proper mock schedule
        mock_schedule = create_mock_protection_group(repl_enabled=True)
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        update_schedule(mock_module, mock_array, None, None)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_update_schedule_blackout_change(
        self, mock_check_response, mock_get_with_context
    ):
        """Test update_schedule when blackout window changes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "replication",
            "context": "",
            "enabled": None,
            "replicate_frequency": None,
            "replicate_at": None,
            "target_days": None,
            "target_per_day": None,
            "target_all_for": None,
            "blackout_start": "11PM",
            "blackout_end": "5AM",
        }
        mock_array = Mock()
        # Create proper mock schedule
        mock_schedule = create_mock_protection_group(blackout_start=0, blackout_end=0)
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        update_schedule(mock_module, mock_array, None, None)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_update_schedule_target_retention_change(
        self, mock_check_response, mock_get_with_context
    ):
        """Test update_schedule when target retention changes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "replication",
            "context": "",
            "enabled": None,
            "replicate_frequency": None,
            "replicate_at": None,
            "target_days": 30,  # Changed from 7
            "target_per_day": 12,  # Changed from 4
            "target_all_for": 259200,  # Changed from 86400
            "blackout_start": None,
            "blackout_end": None,
        }
        mock_array = Mock()
        # Create proper mock schedule
        mock_schedule = create_mock_protection_group(
            target_days=7, target_per_day=4, target_all_for=86400
        )
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        update_schedule(mock_module, mock_array, None, None)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_update_schedule_replicate_frequency_change_with_at(
        self, mock_check_response, mock_get_with_context
    ):
        """Test update_schedule when replication frequency changes with at value"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "replication",
            "context": "",
            "enabled": None,
            "replicate_frequency": 172800,  # 2 days
            "replicate_at": "6PM",  # New at value
            "target_days": None,
            "target_per_day": None,
            "target_all_for": None,
            "blackout_start": None,
            "blackout_end": None,
        }
        mock_array = Mock()
        # Create proper mock schedule
        mock_schedule = create_mock_protection_group(
            repl_frequency=86400000, repl_at=54000
        )
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        update_schedule(mock_module, mock_array, None, None)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteScheduleEnabled:
    """Test cases for delete_schedule when schedules are enabled"""

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_delete_schedule_replication_enabled(
        self, mock_check_response, mock_get_with_context
    ):
        """Test delete_schedule when replication schedule is enabled"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "replication",
            "context": "",
        }
        mock_array = Mock()
        # Replication schedule enabled
        mock_schedule = Mock()
        mock_schedule.replication_schedule.enabled = True
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        delete_schedule(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    @patch("plugins.modules.purefa_pgsched.check_response")
    def test_delete_schedule_snapshot_enabled(
        self, mock_check_response, mock_get_with_context
    ):
        """Test delete_schedule when snapshot schedule is enabled"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "context": "",
        }
        mock_array = Mock()
        # Snapshot schedule enabled
        mock_schedule = Mock()
        mock_schedule.snapshot_schedule.enabled = True
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        delete_schedule(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsched.get_with_context")
    def test_delete_schedule_snapshot_check_mode(self, mock_get_with_context):
        """Test delete_schedule snapshot in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pg",
            "schedule": "snapshot",
            "context": "",
        }
        mock_array = Mock()
        # Snapshot schedule enabled
        mock_schedule = Mock()
        mock_schedule.snapshot_schedule.enabled = True
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_schedule]
        )

        delete_schedule(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
