# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_metrics module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock

# Mock external dependencies before importing module
sys.modules["grp"] = MagicMock()
sys.modules["pwd"] = MagicMock()
sys.modules["fcntl"] = MagicMock()
sys.modules["ansible"] = MagicMock()
sys.modules["ansible.module_utils"] = MagicMock()
sys.modules["ansible.module_utils.basic"] = MagicMock()
sys.modules["ansible.module_utils.urls"] = MagicMock()
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

from unittest.mock import patch

import pytest

from plugins.modules.purefa_metrics import (
    ENDPOINTS,
    NAMESPACE,
    _parse_labels,
    _parse_value,
    _split_sample,
    parse_exposition,
    read_exposition,
    select_metrics,
)

# Trimmed verbatim from the exporter on a FlashArray at REST 2.54, keeping the
# shapes that matter: a metric with no labels, one with a single label, one
# with several, and the scientific notation the array actually emits.
EXPOSITION = """\
# HELP purefa_array_performance_queue_depth_ops FlashArray array queue depth size
# TYPE purefa_array_performance_queue_depth_ops gauge
purefa_array_performance_queue_depth_ops 0
# HELP purefa_array_space_bytes FlashArray array space in bytes
# TYPE purefa_array_space_bytes gauge
purefa_array_space_bytes{space="capacity"} 6.2742755016704e+13
purefa_array_space_bytes{space="empty"} 6.1123817302879e+13
# HELP purefa_hw_component_temperature_celsius FlashArray hardware component temperature
# TYPE purefa_hw_component_temperature_celsius gauge
purefa_hw_component_temperature_celsius{component_name="CT0.TMP0",component_type="temp_sensor"} 30
purefa_hw_component_temperature_celsius{component_name="CT1.TMP0",component_type="temp_sensor"} 31
# HELP purefa_info FlashArray system information
# TYPE purefa_info gauge
purefa_info{array_name="sn1-x50r2",os="Purity//FA",subscription_type="FlashArray",system_id="abc",version="6.10.6"} 1
"""


def _params(**overrides):
    params = {
        "fa_url": "10.10.10.2",
        "api_token": "token",
        "subset": "all",
        "metrics": None,
        "labels": None,
        "include_samples": True,
        "raw": False,
        "validate_certs": False,
        "timeout": 60,
    }
    params.update(overrides)
    return params


def _module(**overrides):
    module = Mock()
    module.check_mode = False
    module.params = _params(**overrides)
    module.fail_json.side_effect = SystemExit(1)
    return module


class TestEndpoints:
    """The exporter's own index page lists exactly these paths"""

    def test_the_six_documented_endpoints(self):
        assert sorted(ENDPOINTS) == [
            "all",
            "array",
            "directories",
            "hosts",
            "pods",
            "volumes",
        ]

    def test_all_reads_the_root_path(self):
        assert ENDPOINTS["all"] == "/metrics"

    def test_resource_paths_are_plural(self):
        """Singular forms fall through to the exporter's HTML index page"""
        assert ENDPOINTS["volumes"] == "/metrics/volumes"
        assert ENDPOINTS["hosts"] == "/metrics/hosts"
        assert ENDPOINTS["pods"] == "/metrics/pods"

    def test_namespace_is_the_only_value_the_array_accepts(self):
        assert NAMESPACE == "purefa"


class TestParseLabels:
    """Label parsing, including the cases a comma split would get wrong"""

    def test_no_labels(self):
        assert _parse_labels("") == {}

    def test_single_label(self):
        assert _parse_labels('space="capacity"') == {"space": "capacity"}

    def test_several_labels(self):
        assert _parse_labels(
            'component_name="CT0.TMP0",component_type="temp_sensor"'
        ) == {"component_name": "CT0.TMP0", "component_type": "temp_sensor"}

    def test_value_containing_a_comma(self):
        """A comma inside a quoted value must not split the label list"""
        assert _parse_labels('summary="disk 1, bay 2",code="13"') == {
            "summary": "disk 1, bay 2",
            "code": "13",
        }

    def test_escaped_quote_and_backslash(self):
        assert _parse_labels(r'issue="the \"left\" path\\here"') == {
            "issue": 'the "left" path\\here'
        }

    def test_escaped_newline(self):
        assert _parse_labels(r'summary="first\nsecond"') == {"summary": "first\nsecond"}

    def test_empty_value(self):
        assert _parse_labels('nqn="",wwn="21000024ff8f4d02"') == {
            "nqn": "",
            "wwn": "21000024ff8f4d02",
        }

    def test_spaces_around_separators(self):
        assert _parse_labels('name="eth0", type="eth"') == {
            "name": "eth0",
            "type": "eth",
        }


class TestParseValue:
    """Values are doubles, and JSON cannot carry the non-finite ones"""

    def test_integer(self):
        assert _parse_value("30") == 30.0

    def test_float(self):
        assert _parse_value("1.5") == 1.5

    def test_scientific_notation(self):
        """The array emits capacity as 6.2742755016704e+13"""
        assert _parse_value("6.2742755016704e+13") == 6.2742755016704e13

    def test_negative(self):
        assert _parse_value("-1") == -1.0

    def test_nan_becomes_none(self):
        assert _parse_value("NaN") is None

    def test_positive_infinity_becomes_none(self):
        assert _parse_value("+Inf") is None

    def test_negative_infinity_becomes_none(self):
        assert _parse_value("-Inf") is None

    def test_unparseable_becomes_none(self):
        assert _parse_value("banana") is None


class TestSplitSample:
    def test_sample_without_labels(self):
        assert _split_sample("purefa_x 0") == ("purefa_x", "", "0")

    def test_sample_with_labels(self):
        assert _split_sample('purefa_x{a="b"} 1.5') == ("purefa_x", 'a="b"', "1.5")

    def test_sample_with_a_brace_inside_a_label_value(self):
        """The closing brace is found from the right, not the left"""
        name, labels, value = _split_sample('purefa_x{summary="a } b"} 2')
        assert name == "purefa_x"
        assert _parse_labels(labels) == {"summary": "a } b"}
        assert value == "2"

    def test_name_with_no_value_is_rejected(self):
        assert _split_sample("purefa_x") is None

    def test_unterminated_labels_are_rejected(self):
        assert _split_sample('purefa_x{a="b" 1') is None


class TestParseExposition:
    def test_every_metric_is_found(self):
        parsed = parse_exposition(EXPOSITION)

        assert sorted(parsed) == [
            "purefa_array_performance_queue_depth_ops",
            "purefa_array_space_bytes",
            "purefa_hw_component_temperature_celsius",
            "purefa_info",
        ]

    def test_help_and_type_are_captured(self):
        parsed = parse_exposition(EXPOSITION)

        metric = parsed["purefa_hw_component_temperature_celsius"]
        assert metric["help"] == "FlashArray hardware component temperature"
        assert metric["type"] == "gauge"

    def test_samples_carry_labels_and_values(self):
        parsed = parse_exposition(EXPOSITION)

        samples = parsed["purefa_hw_component_temperature_celsius"]["samples"]
        assert samples == [
            {
                "labels": {
                    "component_name": "CT0.TMP0",
                    "component_type": "temp_sensor",
                },
                "value": 30.0,
            },
            {
                "labels": {
                    "component_name": "CT1.TMP0",
                    "component_type": "temp_sensor",
                },
                "value": 31.0,
            },
        ]

    def test_a_metric_with_no_labels(self):
        parsed = parse_exposition(EXPOSITION)

        metric = parsed["purefa_array_performance_queue_depth_ops"]
        assert metric["samples"] == [{"labels": {}, "value": 0.0}]
        assert metric["sample_count"] == 1

    def test_sample_count_matches_the_samples(self):
        parsed = parse_exposition(EXPOSITION)

        for metric in parsed.values():
            assert metric["sample_count"] == len(metric["samples"])

    def test_empty_response(self):
        assert parse_exposition("") == {}

    def test_a_metric_declared_but_never_sampled(self):
        """An array with no pods declares nothing for them, but be safe"""
        parsed = parse_exposition("# HELP purefa_x help text\n# TYPE purefa_x gauge\n")

        assert parsed["purefa_x"]["samples"] == []
        assert parsed["purefa_x"]["sample_count"] == 0

    def test_plain_comments_are_ignored(self):
        parsed = parse_exposition("# just a comment\npurefa_x 1\n")

        assert sorted(parsed) == ["purefa_x"]
        assert parsed["purefa_x"]["help"] is None


class TestSelectMetrics:
    def test_no_filters_returns_everything(self):
        module = _module()

        selected = select_metrics(module, parse_exposition(EXPOSITION))

        assert len(selected) == 4

    def test_named_metrics_only(self):
        module = _module(metrics=["purefa_info"])

        selected = select_metrics(module, parse_exposition(EXPOSITION))

        assert sorted(selected) == ["purefa_info"]

    def test_an_unknown_metric_name_fails_and_lists_what_exists(self):
        module = _module(metrics=["purefa_nonsense"])

        with pytest.raises(SystemExit):
            select_metrics(module, parse_exposition(EXPOSITION))

        message = str(module.fail_json.call_args)
        assert "purefa_nonsense" in message
        assert "purefa_info" in message

    def test_labels_select_an_individual_component(self):
        module = _module(
            metrics=["purefa_hw_component_temperature_celsius"],
            labels={"component_name": "CT0.TMP0"},
        )

        selected = select_metrics(module, parse_exposition(EXPOSITION))

        samples = selected["purefa_hw_component_temperature_celsius"]["samples"]
        assert len(samples) == 1
        assert samples[0]["labels"]["component_name"] == "CT0.TMP0"
        assert samples[0]["value"] == 30.0

    def test_labels_select_every_component_of_a_type(self):
        module = _module(labels={"component_type": "temp_sensor"})

        selected = select_metrics(module, parse_exposition(EXPOSITION))

        assert len(selected["purefa_hw_component_temperature_celsius"]["samples"]) == 2

    def test_labels_must_all_match(self):
        module = _module(
            labels={"component_name": "CT0.TMP0", "component_type": "nonsense"}
        )

        selected = select_metrics(module, parse_exposition(EXPOSITION))

        assert selected["purefa_hw_component_temperature_celsius"]["samples"] == []

    def test_label_filtering_leaves_sample_count_as_the_unfiltered_total(self):
        """sample_count says what the metric has, not what came back"""
        module = _module(labels={"component_name": "CT0.TMP0"})

        selected = select_metrics(module, parse_exposition(EXPOSITION))

        metric = selected["purefa_hw_component_temperature_celsius"]
        assert metric["sample_count"] == 2
        assert len(metric["samples"]) == 1

    def test_a_non_string_label_value_still_matches(self):
        """YAML turns an unquoted 13 into an int, the exposition has "13" """
        module = _module(labels={"space": "capacity"})
        parsed = parse_exposition(EXPOSITION)
        module.params["labels"] = {"space": "capacity"}

        selected = select_metrics(module, parsed)
        assert len(selected["purefa_array_space_bytes"]["samples"]) == 1

        module = _module(labels={"version": 6})
        selected = select_metrics(module, parse_exposition(EXPOSITION))
        assert selected["purefa_info"]["samples"] == []

    def test_include_samples_false_drops_the_samples(self):
        module = _module(include_samples=False)

        selected = select_metrics(module, parse_exposition(EXPOSITION))

        for name, metric in selected.items():
            assert "samples" not in metric, name
            assert "sample_count" in metric
            assert "help" in metric
            assert "type" in metric

    def test_filtering_does_not_mutate_the_parsed_metrics(self):
        parsed = parse_exposition(EXPOSITION)
        module = _module(labels={"component_name": "CT0.TMP0"})

        select_metrics(module, parsed)

        assert len(parsed["purefa_hw_component_temperature_celsius"]["samples"]) == 2


class TestReadExposition:
    """The HTTP layer - the array's error shapes are not all what they seem"""

    def _fetch(self, status=200, content_type="text/plain; version=0.0.4", body=""):
        response = Mock()
        response.read.return_value = body.encode()
        info = {"status": status, "content-type": content_type, "msg": "", "body": b""}
        return response, info

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_url_is_built_from_the_subset_and_namespace(self, mock_fetch):
        mock_fetch.return_value = self._fetch(body=EXPOSITION)
        module = _module(subset="volumes")

        read_exposition(module)

        url = mock_fetch.call_args[0][1]
        assert url == "https://10.10.10.2/metrics/volumes?namespace=purefa"

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_the_api_token_is_sent_as_a_bearer_credential(self, mock_fetch):
        mock_fetch.return_value = self._fetch(body=EXPOSITION)
        module = _module()

        read_exposition(module)

        headers = mock_fetch.call_args[1]["headers"]
        assert headers == {"Authorization": "Bearer token"}

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_a_url_in_fa_url_is_tolerated(self, mock_fetch):
        """Build https://host once, not https://https://host"""
        mock_fetch.return_value = self._fetch(body=EXPOSITION)
        module = _module(fa_url="https://10.10.10.2/")

        read_exposition(module)

        assert mock_fetch.call_args[0][1].startswith("https://10.10.10.2/metrics")

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_html_is_rejected_even_with_a_200(self, mock_fetch):
        """An unrecognised path returns the exporter's index page, not a 404"""
        mock_fetch.return_value = self._fetch(
            content_type="text/html; charset=utf-8", body="<html>"
        )
        module = _module()

        with pytest.raises(SystemExit):
            read_exposition(module)

        assert "6.7.0" in str(module.fail_json.call_args)

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_a_missing_content_type_is_rejected(self, mock_fetch):
        mock_fetch.return_value = self._fetch(content_type=None, body="")
        module = _module()

        with pytest.raises(SystemExit):
            read_exposition(module)

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_a_bad_token_is_reported_as_an_auth_problem(self, mock_fetch):
        mock_fetch.return_value = self._fetch(status=400)
        module = _module()

        with pytest.raises(SystemExit):
            read_exposition(module)

        assert "bearer" in str(module.fail_json.call_args).lower()

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_rate_limiting_is_reported_as_such(self, mock_fetch):
        mock_fetch.return_value = self._fetch(status=429)
        module = _module()

        with pytest.raises(SystemExit):
            read_exposition(module)

        assert "rate limited" in str(module.fail_json.call_args)

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_an_unreachable_array_is_reported(self, mock_fetch):
        response = Mock()
        mock_fetch.return_value = (
            response,
            {"status": -1, "msg": "Connection refused", "content-type": None},
        )
        module = _module()

        with pytest.raises(SystemExit):
            read_exposition(module)

        assert "Connection refused" in str(module.fail_json.call_args)

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_no_token_fails_before_any_request(self, mock_fetch):
        module = _module(api_token=None)
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit):
                read_exposition(module)

        mock_fetch.assert_not_called()
        message = str(module.fail_json.call_args)
        assert "id_token" in message

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_no_url_fails_before_any_request(self, mock_fetch):
        module = _module(fa_url=None)
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit):
                read_exposition(module)

        mock_fetch.assert_not_called()

    @patch("plugins.modules.purefa_metrics.fetch_url")
    def test_credentials_come_from_the_environment_when_not_given(self, mock_fetch):
        mock_fetch.return_value = self._fetch(body=EXPOSITION)
        module = _module(fa_url=None, api_token=None)

        with patch.dict(
            "os.environ",
            {"PUREFA_URL": "1.2.3.4", "PUREFA_API": "env-token"},
            clear=True,
        ):
            read_exposition(module)

        assert mock_fetch.call_args[0][1].startswith("https://1.2.3.4/")
        assert mock_fetch.call_args[1]["headers"] == {
            "Authorization": "Bearer env-token"
        }
