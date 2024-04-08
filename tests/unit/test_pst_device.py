# pylint: disable=redefined-outer-name
# -*- coding: utf-8 -*-
"""
Some simple unit tests of the PowerSupply device, exercising the device from
another host using a DeviceProxy.
"""
import json
import logging
import time

import pytest
import tango
from ska_control_model import AdminMode, HealthState, ObsState, ResultCode

from ska_csp_simulators.common.pst_beam_simulator import PstBeamSimulatorDevice
from ska_csp_simulators.DevFactory import DevFactory

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": PstBeamSimulatorDevice,
            "devices": [
                {
                    "name": "sim-pst/beam/01",
                },
            ],
        },
    )


@pytest.fixture
def pst_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("sim-pst/beam/01")


@pytest.fixture(autouse=True)
def pst_device_online(pst_device, change_event_callbacks):
    for attribute in [
        "state",
        "adminMode",
        "healthState",
        "obsState",
        "channelBlockConfiguration",
        "longRunningCommandProgress",
        "longRunningCommandStatus",
        "longRunningCommandResult",
    ]:
        pst_device.subscribe_event(
            attribute,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attribute],
        )
    change_event_callbacks.assert_change_event("state", tango.DevState.DISABLE)
    change_event_callbacks.assert_change_event("adminMode", AdminMode.OFFLINE)
    change_event_callbacks.assert_change_event("healthState", HealthState.OK)
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)
    change_event_callbacks.assert_change_event(
        "channelBlockConfiguration", "{}"
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", ()
    )
    change_event_callbacks.assert_change_event("longRunningCommandStatus", ())
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult", ("", "")
    )
    pst_device.adminmode = 0
    change_event_callbacks.assert_change_event("adminMode", AdminMode.ONLINE)
    change_event_callbacks.assert_change_event("state", tango.DevState.OFF)


def test_pst_beam_configure(pst_device, change_event_callbacks):
    """Test configure request on PST Beam"""
    # load the cahnnel block configuration from a data file. This  file
    # is the same used by the PST simulator during beam configuration.
    f = open(
        "./tests/test_data/pst_channel_block_config.json",
        "r",
        encoding="utf-8",
    )
    channel_config = f.read().replace("\n", "")
    pst_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    [[result_code], [command_id]] = pst_device.Configure('{"subarray_id":1}')
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "obsState", ObsState.CONFIGURING
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)
    time.sleep(0.2)
    assert json.loads(pst_device.channelBlockConfiguration) == json.loads(
        channel_config
    )
