# pylint: disable=redefined-outer-name
# -*- coding: utf-8 -*-
"""
Some simple unit tests of the PowerSupply device, exercising the device from
another host using a DeviceProxy.
"""
import json
import logging

import pytest
import tango
from ska_control_model import AdminMode, HealthState, ResultCode

from ska_csp_simulators.DevFactory import DevFactory
from ska_csp_simulators.mid.mid_cbf_ctrl_simulator import MidCbfCtrlSimulator

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": MidCbfCtrlSimulator,
            "devices": [
                {
                    "name": "sim-mid-cbf/control/0",
                },
            ],
        },
    )


@pytest.fixture
def ctrl_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("sim-mid-cbf/control/0")


@pytest.fixture(autouse=True)
def ctrl_device_online(ctrl_device, change_event_callbacks):
    for attribute in [
        "state",
        "adminMode",
        "healthState",
        "longRunningCommandProgress",
        "longRunningCommandStatus",
        "longRunningCommandResult",
    ]:
        ctrl_device.subscribe_event(
            attribute,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attribute],
            # print_event
        )
    change_event_callbacks.assert_change_event("state", tango.DevState.DISABLE)
    change_event_callbacks.assert_change_event("adminMode", AdminMode.OFFLINE)
    change_event_callbacks.assert_change_event("healthState", HealthState.OK)
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", ()
    )
    change_event_callbacks.assert_change_event("longRunningCommandStatus", ())
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult", ("", "")
    )
    ctrl_device.adminmode = 0
    change_event_callbacks.assert_change_event("adminMode", AdminMode.ONLINE)
    change_event_callbacks.assert_change_event("state", tango.DevState.OFF)


def test_init_sys_param_with_uri(ctrl_device, change_event_callbacks):
    """
    Test InitSysParam when the input data is the URI from where
    download the VCC-Dish map
    """
    vcc_map_url = """{
    "interface": "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0",
    "tm_data_sources": ["car://gitlab.com/ska-telescope/0#tmdata"],
    "tm_data_filepath": "./tests/test_data/system-parameters.json"}
    """
    f = open("./tests/test_data/system-parameters.json", "r", encoding="utf-8")
    vcc_map = f.read()
    [[result_code], [command_id]] = ctrl_device.InitSysParam(vcc_map_url)
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", (command_id, "33")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", (command_id, "66")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    # need to wait for a while before the update of the map info
    import time

    time.sleep(0.2)

    assert json.loads(vcc_map) == json.loads(ctrl_device.sysParam)
    assert ctrl_device.sourceSysParam == vcc_map_url


def test_init_sys_param_wrong_file_path(ctrl_device, change_event_callbacks):
    """Test device sets current on request"""
    vcc_map_uri = """{
    "interface": "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0",
    "tm_data_sources": ["car://gitlab.com/ska-telescope/0#tmdata"],
    "tm_data_filepath": "./tests/test_data/system.json"}
    """

    [[result_code], [command_id]] = ctrl_device.InitSysParam(vcc_map_uri)
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", (command_id, "33")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", (command_id, "66")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    # need to wait for a while before the update of the map info
    import time

    time.sleep(0.2)

    assert not ctrl_device.sysParam
    assert ctrl_device.sourceSysParam == vcc_map_uri


def test_init_sys_param_with_file(ctrl_device):
    """
    Test InitSysParam when the input data is the
    VCC-Dish map
    """
    f = open("./tests/test_data/system-parameters.json", "r", encoding="utf-8")
    vcc_map = f.read()
    result_code = ctrl_device.InitSysParam(vcc_map)
    assert result_code[0] == ResultCode.OK
    assert json.loads(vcc_map) == json.loads(ctrl_device.sysParam)
    assert not ctrl_device.sourceSysParam


def test_init_sys_param_with_invalid_json(ctrl_device):
    """
    Test InitSysParam when the input data is the
    VCC-Dish map
    """
    vcc_map = ""
    result_code, _ = ctrl_device.InitSysParam(vcc_map)
    assert result_code[0] == ResultCode.FAILED
    assert not ctrl_device.sysParam
    assert not ctrl_device.sourceSysParam
