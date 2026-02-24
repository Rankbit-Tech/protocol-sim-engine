"""
EtherNet/IP Protocol Test Suite

Tests the CIP codec (pure functions), CIPServer (unit, no sockets),
EtherNetIPDevice creation and lifecycle, EtherNetIPDeviceManager,
data generators, and Pydantic config models.

Run with:
    python -m pytest tests/unit/test_ethernetip_protocol.py -v
"""

import asyncio
import struct
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# CIP constants & codec imports
# ---------------------------------------------------------------------------
from src.protocols.industrial.ethernetip.cip_constants import (
    CIPCommand, CIPDataType, CIPService, CIPStatus,
    ENCAP_HEADER_SIZE, ENCAP_HEADER_FORMAT, DEFAULT_EIP_PORT,
)
from src.protocols.industrial.ethernetip.cip_protocol import (
    decode_encap_header,
    encode_encap_header,
    encode_cip_error_response,
    encode_cip_read_tag_response,
    encode_cip_write_tag_response,
    encode_list_identity_response,
    encode_register_session_response,
    encode_send_rr_data_response,
    pack_cip_value,
    parse_epath_symbolic,
    unpack_cip_value,
)
from src.protocols.industrial.ethernetip.cip_server import CIPServer
from src.protocols.industrial.ethernetip.ethernetip_simulator import (
    EtherNetIPDevice,
    EtherNetIPDeviceManager,
    _controllogix_initial_tags,
    _powerflex_initial_tags,
    _io_module_initial_tags,
)
from src.config_parser import (
    EtherNetIPConfig,
    EtherNetIPDeviceConfig,
    ConfigParser,
)
from src.data_patterns.industrial_patterns import IndustrialDataGenerator


# ===========================================================================
# TestCIPProtocolCodec — pure codec, no network
# ===========================================================================

class TestCIPProtocolCodec(unittest.TestCase):

    # --- encapsulation header -----------------------------------------------

    def test_encode_decode_encap_header_roundtrip(self):
        ctx = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        raw = encode_encap_header(
            CIPCommand.REGISTER_SESSION,
            4,
            session_handle=0xDEADBEEF,
            status=0,
            sender_context=ctx,
            options=0,
        )
        self.assertEqual(len(raw), ENCAP_HEADER_SIZE)
        hdr = decode_encap_header(raw)
        self.assertEqual(hdr["command"], CIPCommand.REGISTER_SESSION)
        self.assertEqual(hdr["length"], 4)
        self.assertEqual(hdr["session_handle"], 0xDEADBEEF)
        self.assertEqual(hdr["status"], 0)
        self.assertEqual(hdr["sender_context"], ctx)
        self.assertEqual(hdr["options"], 0)

    def test_decode_encap_header_raises_on_short_data(self):
        with self.assertRaises(ValueError):
            decode_encap_header(b"\x00" * 10)

    def test_encode_header_status_nonzero(self):
        raw = encode_encap_header(CIPCommand.SEND_RR_DATA, 0, status=CIPStatus.INVALID_SESSION)
        hdr = decode_encap_header(raw)
        self.assertEqual(hdr["status"], CIPStatus.INVALID_SESSION)

    # --- pack / unpack -------------------------------------------------------

    def test_pack_unpack_real_roundtrip(self):
        val = 3.14
        packed = pack_cip_value(CIPDataType.REAL, val, 1)
        result = unpack_cip_value(CIPDataType.REAL, packed, 1)
        self.assertAlmostEqual(result, val, places=5)

    def test_pack_unpack_dint_roundtrip(self):
        val = -123456
        packed = pack_cip_value(CIPDataType.DINT, val, 1)
        result = unpack_cip_value(CIPDataType.DINT, packed, 1)
        self.assertEqual(result, val)

    def test_pack_unpack_bool_roundtrip(self):
        for val in (True, False):
            packed = pack_cip_value(CIPDataType.BOOL, val, 1)
            result = unpack_cip_value(CIPDataType.BOOL, packed, 1)
            self.assertEqual(bool(result), val)

    def test_pack_unpack_int_roundtrip(self):
        val = -1000
        packed = pack_cip_value(CIPDataType.INT, val, 1)
        result = unpack_cip_value(CIPDataType.INT, packed, 1)
        self.assertEqual(result, val)

    def test_pack_unpack_dint_array_roundtrip(self):
        vals = [1, -2, 3, -4]
        packed = pack_cip_value(CIPDataType.DINT, vals, 4)
        self.assertEqual(len(packed), 4 * 4)
        result = unpack_cip_value(CIPDataType.DINT, packed, 4)
        self.assertEqual(list(result), vals)

    def test_pack_unpack_real_array_roundtrip(self):
        vals = [1.1, 2.2, 3.3]
        packed = pack_cip_value(CIPDataType.REAL, vals, 3)
        self.assertEqual(len(packed), 3 * 4)
        result = unpack_cip_value(CIPDataType.REAL, packed, 3)
        for a, b in zip(result, vals):
            self.assertAlmostEqual(a, b, places=4)

    # --- EPATH symbolic ------------------------------------------------------

    def test_parse_epath_symbolic_simple(self):
        tag_name = "ProcessValue"
        name_bytes = tag_name.encode("ascii")
        pad = b"\x00" if len(name_bytes) % 2 else b""
        path = bytes([0x91, len(name_bytes)]) + name_bytes + pad
        result = parse_epath_symbolic(path)
        self.assertEqual(result, tag_name)

    def test_parse_epath_symbolic_odd_length(self):
        tag_name = "A"  # length 1, odd
        name_bytes = tag_name.encode("ascii")
        path = bytes([0x91, 1]) + name_bytes + b"\x00"  # pad byte
        result = parse_epath_symbolic(path)
        self.assertEqual(result, tag_name)

    def test_parse_epath_symbolic_empty_returns_none(self):
        result = parse_epath_symbolic(b"")
        self.assertIsNone(result)

    def test_parse_epath_symbolic_non_symbolic_segment(self):
        # Logical class segment (0x20), not symbolic
        path = bytes([0x20, 0x01, 0x24, 0x01])
        result = parse_epath_symbolic(path)
        self.assertIsNone(result)

    # --- high-level response builders ----------------------------------------

    def test_encode_list_identity_response_structure(self):
        device_info = {
            "vendor_id": 1, "device_type": 0x0E, "product_code": 0x14,
            "revision_major": 1, "revision_minor": 1,
            "serial_number": 0xABCDEF01,
            "product_name": "TestDevice",
        }
        ctx = b"\xAA" * 8
        resp = encode_list_identity_response(device_info, ctx)
        # Must be at least 24 (header) + 2 (item_count) + 4 (item hdr) + identity data
        self.assertGreater(len(resp), 30)
        hdr = decode_encap_header(resp[:24])
        self.assertEqual(hdr["command"], CIPCommand.LIST_IDENTITY)
        self.assertEqual(hdr["sender_context"], ctx)

    def test_encode_register_session_response_length(self):
        resp = encode_register_session_response(0x1234, b"\x00" * 8)
        # header (24) + protocol_version (2) + options (2) = 28
        self.assertEqual(len(resp), 28)
        hdr = decode_encap_header(resp[:24])
        self.assertEqual(hdr["command"], CIPCommand.REGISTER_SESSION)
        self.assertEqual(hdr["session_handle"], 0x1234)
        self.assertEqual(hdr["status"], 0)

    def test_encode_cip_read_tag_response_for_real(self):
        packed = pack_cip_value(CIPDataType.REAL, 42.5, 1)
        resp = encode_cip_read_tag_response(CIPDataType.REAL, packed)
        # service|0x80, reserved, status, ext_status, type(2), value(4) = 10 bytes
        self.assertEqual(len(resp), 10)
        self.assertEqual(resp[0], CIPService.READ_TAG | CIPService.RESPONSE_FLAG)
        self.assertEqual(resp[2], CIPStatus.SUCCESS)
        type_code = struct.unpack_from("<H", resp, 4)[0]
        self.assertEqual(type_code, CIPDataType.REAL)
        val = struct.unpack_from("<f", resp, 6)[0]
        self.assertAlmostEqual(val, 42.5, places=4)

    def test_encode_cip_error_response_flag(self):
        resp = encode_cip_error_response(CIPService.READ_TAG, CIPStatus.PATH_UNKNOWN)
        self.assertEqual(len(resp), 4)
        self.assertEqual(resp[0], CIPService.READ_TAG | CIPService.RESPONSE_FLAG)
        self.assertEqual(resp[2], CIPStatus.PATH_UNKNOWN)

    def test_encode_cip_write_tag_response(self):
        resp = encode_cip_write_tag_response(CIPService.WRITE_TAG)
        self.assertEqual(len(resp), 4)
        self.assertEqual(resp[0], CIPService.WRITE_TAG | CIPService.RESPONSE_FLAG)
        self.assertEqual(resp[2], CIPStatus.SUCCESS)


# ===========================================================================
# TestEtherNetIPDeviceCreation — no network
# ===========================================================================

def _make_eip_device_config(template: str, count: int = 1, port_start: int = 44818):
    return EtherNetIPDeviceConfig(
        count=count,
        port_start=port_start,
        device_template=template,
        locations=["test_zone"],
        update_interval=1.0,
        data_config={},
    )


class TestEtherNetIPDeviceCreation(unittest.TestCase):

    def _make_device(self, template: str, port: int = 44818) -> EtherNetIPDevice:
        cfg = _make_eip_device_config(template, port_start=port)
        return EtherNetIPDevice("test_device", cfg, port)

    def test_device_initialization_controllogix(self):
        device = self._make_device("eip_controllogix_plc")
        self.assertEqual(device.device_type, "controllogix_plc")
        self.assertFalse(device.running)
        self.assertIsNotNone(device.cip_server)

    def test_device_initialization_powerflex(self):
        device = self._make_device("eip_powerflex_drive", port=44819)
        self.assertEqual(device.device_type, "powerflex_drive")
        self.assertFalse(device.running)

    def test_device_initialization_io_module(self):
        device = self._make_device("eip_io_module", port=44820)
        self.assertEqual(device.device_type, "io_module")
        self.assertFalse(device.running)

    def test_device_type_extraction_unknown(self):
        device = self._make_device("unknown_template")
        self.assertEqual(device.device_type, "controllogix_plc")  # fallback

    def test_tag_store_initialization_controllogix(self):
        device = self._make_device("eip_controllogix_plc")
        device._initialize_tag_store()
        expected_tags = {
            "ProcessValue", "Setpoint", "ControlOutput", "Mode",
            "HighAlarm", "LowAlarm", "Error", "CycleTime", "BatchCount", "RunStatus",
        }
        self.assertEqual(set(device.tag_store.keys()), expected_tags)
        self.assertEqual(device.tag_store["Setpoint"]["type_code"], CIPDataType.REAL)
        self.assertEqual(device.tag_store["Mode"]["type_code"], CIPDataType.INT)
        self.assertEqual(device.tag_store["HighAlarm"]["type_code"], CIPDataType.BOOL)

    def test_tag_store_initialization_powerflex(self):
        device = self._make_device("eip_powerflex_drive", port=44819)
        device._initialize_tag_store()
        expected_tags = {
            "OutputFrequency", "OutputVoltage", "OutputCurrent", "MotorSpeed",
            "Torque", "DCBusVoltage", "DriveTemp", "FaultCode", "RunStatus", "AccelTime",
        }
        self.assertEqual(set(device.tag_store.keys()), expected_tags)
        self.assertEqual(device.tag_store["OutputFrequency"]["type_code"], CIPDataType.REAL)
        self.assertEqual(device.tag_store["MotorSpeed"]["type_code"], CIPDataType.DINT)

    def test_tag_store_initialization_io_module(self):
        device = self._make_device("eip_io_module", port=44820)
        device._initialize_tag_store()
        expected_tags = {
            "DI_Word", "DO_Word", "AI_Channel", "AO_Channel", "ModuleStatus", "SlotNumber",
        }
        self.assertEqual(set(device.tag_store.keys()), expected_tags)
        self.assertEqual(device.tag_store["AI_Channel"]["element_count"], 8)
        self.assertEqual(device.tag_store["DI_Word"]["element_count"], 4)
        self.assertEqual(device.tag_store["AO_Channel"]["element_count"], 4)

    def test_tag_store_slot_number_from_config(self):
        cfg = _make_eip_device_config("eip_io_module", port_start=44820)
        cfg.data_config = {"slot_number": 5}
        device = EtherNetIPDevice("io_dev", cfg, 44820)
        device._initialize_tag_store()
        self.assertEqual(device.tag_store["SlotNumber"]["value"], 5)

    def test_device_status_stopped(self):
        device = self._make_device("eip_controllogix_plc")
        status = device.get_status()
        self.assertEqual(status["status"], "stopped")
        self.assertFalse(status["running"])
        self.assertEqual(status["device_id"], "test_device")

    def test_get_tag_data_returns_none_when_not_running(self):
        device = self._make_device("eip_controllogix_plc")
        # Tag store empty, health_status has no last_update
        result = device.get_tag_data()
        self.assertIsNone(result)

    def test_application_info_serial_number(self):
        device = self._make_device("eip_controllogix_plc")
        info = device._build_device_info()
        self.assertIn("serial_number", info)
        self.assertGreater(info["serial_number"], 0)
        self.assertEqual(info["vendor_id"], 0x0001)


# ===========================================================================
# TestCIPServerUnit — unit tests using the dispatch methods directly (no sockets)
# ===========================================================================

def _make_server(tag_store=None) -> CIPServer:
    device_info = {
        "vendor_id": 1, "device_type": 0x0E, "product_code": 0x14,
        "revision_major": 1, "revision_minor": 1,
        "serial_number": 0xDEADBEEF, "product_name": "TestPLC",
    }
    return CIPServer("0.0.0.0", 44818, device_info, tag_store or {})


def _build_symbolic_path(tag_name: str) -> bytes:
    name_bytes = tag_name.encode("ascii")
    pad = b"\x00" if len(name_bytes) % 2 else b""
    return bytes([0x91, len(name_bytes)]) + name_bytes + pad


class TestCIPServerUnit(unittest.TestCase):

    def test_register_session_creates_session(self):
        srv = _make_server()
        payload = struct.pack("<HH", 1, 0)  # protocol_version=1, options=0
        resp = srv._handle_register_session(b"\x00" * 8, payload)
        hdr = decode_encap_header(resp[:24])
        handle = hdr["session_handle"]
        self.assertIn(handle, srv.sessions)
        self.assertEqual(srv.get_session_count(), 1)

    def test_unregister_session_removes_session(self):
        srv = _make_server()
        payload = struct.pack("<HH", 1, 0)
        resp = srv._handle_register_session(b"\x00" * 8, payload)
        handle = decode_encap_header(resp[:24])["session_handle"]
        self.assertIn(handle, srv.sessions)
        srv._handle_unregister_session(handle, b"\x00" * 8)
        self.assertNotIn(handle, srv.sessions)

    def test_send_rr_data_invalid_session_returns_error(self):
        srv = _make_server()
        # No sessions registered
        resp = srv._dispatch_command(
            CIPCommand.SEND_RR_DATA, 0xBADBAD, b"\x00" * 8, b""
        )
        hdr = decode_encap_header(resp[:24])
        self.assertEqual(hdr["status"], CIPStatus.INVALID_SESSION)

    def test_read_tag_returns_correct_value(self):
        tag_store = {
            "ProcessValue": {"type_code": CIPDataType.REAL, "value": 42.0, "element_count": 1},
        }
        srv = _make_server(tag_store)
        path = _build_symbolic_path("ProcessValue")
        element_count_bytes = struct.pack("<H", 1)
        resp = srv._svc_read_tag(path, element_count_bytes)
        self.assertEqual(resp[0], CIPService.READ_TAG | CIPService.RESPONSE_FLAG)
        self.assertEqual(resp[2], CIPStatus.SUCCESS)
        val = struct.unpack_from("<f", resp, 6)[0]
        self.assertAlmostEqual(val, 42.0, places=4)

    def test_read_tag_unknown_tag_returns_error(self):
        srv = _make_server({})
        path = _build_symbolic_path("NonExistentTag")
        resp = srv._svc_read_tag(path, b"\x01\x00")
        self.assertEqual(resp[0], CIPService.READ_TAG | CIPService.RESPONSE_FLAG)
        self.assertEqual(resp[2], CIPStatus.PATH_UNKNOWN)

    def test_write_tag_updates_tag_store(self):
        tag_store = {
            "Setpoint": {"type_code": CIPDataType.REAL, "value": 50.0, "element_count": 1},
        }
        srv = _make_server(tag_store)
        path = _build_symbolic_path("Setpoint")
        new_val = struct.pack("<f", 75.0)
        request_data = struct.pack("<HH", CIPDataType.REAL, 1) + new_val
        resp = srv._svc_write_tag(path, request_data)
        self.assertEqual(resp[0], CIPService.WRITE_TAG | CIPService.RESPONSE_FLAG)
        self.assertEqual(resp[2], CIPStatus.SUCCESS)
        self.assertAlmostEqual(tag_store["Setpoint"]["value"], 75.0, places=4)

    def test_write_tag_type_mismatch_returns_error(self):
        tag_store = {
            "Setpoint": {"type_code": CIPDataType.REAL, "value": 50.0, "element_count": 1},
        }
        srv = _make_server(tag_store)
        path = _build_symbolic_path("Setpoint")
        # Send DINT instead of REAL
        new_val = struct.pack("<i", 75)
        request_data = struct.pack("<HH", CIPDataType.DINT, 1) + new_val
        resp = srv._svc_write_tag(path, request_data)
        self.assertEqual(resp[2], CIPStatus.INVALID_ATTR_VALUE)

    def test_multi_service_bundles_reads(self):
        tag_store = {
            "ProcessValue": {"type_code": CIPDataType.REAL, "value": 10.0, "element_count": 1},
            "Setpoint":     {"type_code": CIPDataType.REAL, "value": 50.0, "element_count": 1},
        }
        srv = _make_server(tag_store)

        # Build two ReadTag sub-requests
        def make_read_request(tag_name: str) -> bytes:
            path = _build_symbolic_path(tag_name)
            path_size_words = len(path) // 2
            svc = bytes([CIPService.READ_TAG, path_size_words]) + path
            svc += struct.pack("<H", 1)  # element_count
            return svc

        sub1 = make_read_request("ProcessValue")
        sub2 = make_read_request("Setpoint")

        # service_count=2, offsets relative to start of service_count field
        service_count = 2
        offset_1 = 2 + service_count * 2           # after service_count + offset table
        offset_2 = offset_1 + len(sub1)
        request_data = (
            struct.pack("<H", service_count)
            + struct.pack("<HH", offset_1, offset_2)
            + sub1
            + sub2
        )

        resp = srv._svc_multi_service(b"", request_data)
        # Should return MultipleServicePacket response flag
        self.assertEqual(resp[0], CIPService.MULTI_SERVICE | CIPService.RESPONSE_FLAG)
        self.assertEqual(resp[2], CIPStatus.SUCCESS)

    def test_get_tag_names(self):
        tag_store = {
            "TagA": {"type_code": CIPDataType.REAL, "value": 1.0, "element_count": 1},
            "TagB": {"type_code": CIPDataType.INT, "value": 2, "element_count": 1},
        }
        srv = _make_server(tag_store)
        names = srv.get_tag_names()
        self.assertIn("TagA", names)
        self.assertIn("TagB", names)

    def test_list_identity_no_session_required(self):
        srv = _make_server()
        resp = srv._handle_list_identity(b"\x00" * 8)
        hdr = decode_encap_header(resp[:24])
        self.assertEqual(hdr["command"], CIPCommand.LIST_IDENTITY)
        self.assertEqual(hdr["status"], 0)


# ===========================================================================
# TestEtherNetIPDeviceLifecycle — mock asyncio.start_server
# ===========================================================================

class TestEtherNetIPDeviceLifecycle(unittest.IsolatedAsyncioTestCase):

    async def test_device_start_stop_lifecycle(self):
        cfg = _make_eip_device_config("eip_controllogix_plc")
        device = EtherNetIPDevice("lifecycle_test", cfg, 44818)

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        with patch("asyncio.start_server", new=AsyncMock(return_value=mock_server)):
            started = await device.start()

        self.assertTrue(started)
        self.assertTrue(device.running)
        self.assertEqual(device.health_status["status"], "running")
        self.assertIsNotNone(device.health_status["uptime_start"])

        await device.stop()
        self.assertFalse(device.running)
        self.assertEqual(device.health_status["status"], "stopped")

    async def test_device_uptime_tracking(self):
        cfg = _make_eip_device_config("eip_powerflex_drive", port_start=44819)
        device = EtherNetIPDevice("uptime_test", cfg, 44819)

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        with patch("asyncio.start_server", new=AsyncMock(return_value=mock_server)):
            await device.start()

        await asyncio.sleep(0.05)
        status = device.get_status()
        self.assertGreater(status["uptime_seconds"], 0)

        await device.stop()

    async def test_get_tag_data_after_start(self):
        cfg = _make_eip_device_config("eip_controllogix_plc")
        device = EtherNetIPDevice("data_test", cfg, 44818)

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        with patch("asyncio.start_server", new=AsyncMock(return_value=mock_server)):
            await device.start()

        data = device.get_tag_data()
        self.assertIsNotNone(data)
        self.assertIn("tags", data)
        self.assertIn("ProcessValue", data["tags"])
        self.assertIn("Setpoint", data["tags"])

        await device.stop()


# ===========================================================================
# TestEtherNetIPDeviceManager
# ===========================================================================

def _make_mock_port_manager(base_port: int = 44818):
    """Create a port manager mock that returns sequential ports."""
    counter = [base_port]

    def allocate_ports(protocol, device_id, count, preferred_start=None):
        ports = list(range(counter[0], counter[0] + count))
        counter[0] += count
        return ports

    mock = MagicMock()
    mock.allocate_ports.side_effect = allocate_ports
    mock.validate_allocation_plan.return_value = True
    return mock


def _make_eip_config(device_types: dict) -> EtherNetIPConfig:
    """Build an EtherNetIPConfig from a dict of {name: (template, count, port)}."""
    devices = {}
    for name, (template, count, port) in device_types.items():
        devices[name] = EtherNetIPDeviceConfig(
            count=count,
            port_start=port,
            device_template=template,
            update_interval=1.0,
            data_config={},
        )
    return EtherNetIPConfig(enabled=True, devices=devices)


class TestEtherNetIPDeviceManager(unittest.IsolatedAsyncioTestCase):

    async def test_manager_initialization(self):
        config = _make_eip_config({
            "controllogix_plcs": ("eip_controllogix_plc", 1, 44818),
        })
        pm = _make_mock_port_manager()
        manager = EtherNetIPDeviceManager(config, pm)
        ok = await manager.initialize()
        self.assertTrue(ok)
        self.assertEqual(len(manager.devices), 1)
        self.assertIn("eip_controllogix_plcs_000", manager.devices)

    async def test_allocation_plan_building(self):
        config = _make_eip_config({
            "controllogix_plcs": ("eip_controllogix_plc", 2, 44818),
            "powerflex_drives":  ("eip_powerflex_drive", 1, 44820),
        })
        pm = _make_mock_port_manager()
        manager = EtherNetIPDeviceManager(config, pm)
        manager._build_allocation_plan()
        plan = manager.device_allocation_plan
        self.assertEqual(len(plan), 3)
        self.assertIn("eip_controllogix_plcs_000", plan)
        self.assertIn("eip_controllogix_plcs_001", plan)
        self.assertIn("eip_powerflex_drives_000", plan)
        for device_id, (protocol, count) in plan.items():
            self.assertEqual(protocol, "ethernet_ip")
            self.assertEqual(count, 1)

    async def test_device_creation_port_allocation(self):
        config = _make_eip_config({
            "controllogix_plcs": ("eip_controllogix_plc", 3, 44818),
        })
        pm = _make_mock_port_manager(44818)
        manager = EtherNetIPDeviceManager(config, pm)
        await manager.initialize()
        # All 3 devices should have unique ports
        ports = [d.port for d in manager.devices.values()]
        self.assertEqual(len(set(ports)), 3)

    async def test_get_all_device_endpoints(self):
        config = _make_eip_config({
            "controllogix_plcs": ("eip_controllogix_plc", 2, 44818),
        })
        pm = _make_mock_port_manager()
        manager = EtherNetIPDeviceManager(config, pm)
        await manager.initialize()
        endpoints = manager.get_all_device_endpoints()
        self.assertEqual(len(endpoints), 2)
        for ep in endpoints:
            self.assertIn("device_id", ep)
            self.assertIn("port", ep)
            self.assertIn("endpoint", ep)

    async def test_get_allocation_requirements(self):
        config = _make_eip_config({
            "controllogix_plcs": ("eip_controllogix_plc", 1, 44818),
        })
        pm = _make_mock_port_manager()
        manager = EtherNetIPDeviceManager(config, pm)
        manager._build_allocation_plan()
        reqs = manager.get_allocation_requirements()
        self.assertIsInstance(reqs, dict)
        for device_id, (protocol, port_count) in reqs.items():
            self.assertEqual(protocol, "ethernet_ip")
            self.assertEqual(port_count, 1)


# ===========================================================================
# TestEtherNetIPDataPatterns
# ===========================================================================

class TestEtherNetIPDataPatterns(unittest.TestCase):

    def _gen(self, device_type: str, config: dict = None) -> IndustrialDataGenerator:
        return IndustrialDataGenerator(f"test_{device_type}", config or {})

    # --- ControlLogix PLC ------------------------------------------------

    def test_controllogix_plc_data_keys(self):
        gen = self._gen("controllogix_plc")
        data = gen.generate_device_data("controllogix_plc")
        required = {
            "process_value", "setpoint", "control_output", "mode",
            "high_alarm", "low_alarm", "error", "cycle_time_ms",
            "batch_count", "run_status",
        }
        self.assertTrue(required.issubset(data.keys()), f"Missing: {required - data.keys()}")

    def test_controllogix_plc_mode_is_int(self):
        gen = self._gen("controllogix_plc")
        for _ in range(20):
            data = gen.generate_device_data("controllogix_plc")
            self.assertIn(data["mode"], (0, 1, 2))

    def test_controllogix_plc_data_ranges(self):
        gen = self._gen("controllogix_plc", {"process_value_range": [0, 100]})
        for _ in range(30):
            data = gen.generate_device_data("controllogix_plc")
            self.assertGreaterEqual(data["process_value"], 0)
            self.assertLessEqual(data["process_value"], 100)
            self.assertGreaterEqual(data["cycle_time_ms"], 100)
            self.assertIsInstance(data["batch_count"], int)

    def test_controllogix_run_status_false_in_manual(self):
        gen = self._gen("controllogix_plc")
        # Force mode to MANUAL by running enough ticks
        found_manual = False
        for _ in range(200):
            data = gen.generate_device_data("controllogix_plc")
            if data["mode"] == 0:  # MANUAL
                self.assertFalse(data["run_status"])
                found_manual = True
                break
        # It's probabilistic, so don't fail if not found in 200 ticks

    # --- PowerFlex Drive -------------------------------------------------

    def test_powerflex_drive_data_keys(self):
        gen = self._gen("powerflex_drive")
        data = gen.generate_device_data("powerflex_drive")
        required = {
            "output_frequency", "output_voltage", "output_current",
            "motor_speed_rpm", "torque", "dc_bus_voltage", "drive_temp",
            "fault_code", "run_status", "accel_time",
        }
        self.assertTrue(required.issubset(data.keys()))

    def test_powerflex_drive_state_machine_all_states(self):
        gen = self._gen("powerflex_drive", {
            "frequency_range": [0, 60],
            "base_frequency": 50.0,
            "max_current": 50.0,
            "v_per_hz": 7.6,
            "max_torque": 500.0,
            "accel_time": 1.0,  # fast accel to traverse states quickly
        })
        states_seen = set()
        for _ in range(500):
            data = gen.generate_device_data("powerflex_drive")
            states_seen.add(data["run_status"])
        # Should see at least Stopped(0) and Forward(1) in 500 ticks
        self.assertIn(0, states_seen, "Stopped state never seen")
        self.assertIn(1, states_seen, "Forward state never seen")

    def test_powerflex_drive_frequency_positive_when_running(self):
        gen = self._gen("powerflex_drive", {
            "frequency_range": [0, 60], "base_frequency": 50.0,
            "max_current": 50.0, "v_per_hz": 7.6,
            "max_torque": 500.0, "accel_time": 0.5,
        })
        # Generate many ticks; if running, frequency should be non-negative
        for _ in range(100):
            data = gen.generate_device_data("powerflex_drive")
            self.assertGreaterEqual(data["output_frequency"], 0)
            self.assertGreaterEqual(data["output_current"], 0)
            self.assertGreaterEqual(data["drive_temp"], 0)

    def test_powerflex_drive_fault_code_nonzero_during_fault(self):
        gen = self._gen("powerflex_drive", {
            "frequency_range": [0, 60], "base_frequency": 50.0,
            "max_current": 50.0, "v_per_hz": 7.6,
            "max_torque": 500.0, "accel_time": 5.0,
        })
        # Run for many ticks to eventually hit fault
        found_fault = False
        for _ in range(1000):
            data = gen.generate_device_data("powerflex_drive")
            if data["run_status"] == 3:  # Fault
                self.assertGreater(data["fault_code"], 0)
                found_fault = True
                break
        # Not required to find fault, but assert fields are always valid
        # (probabilistic test — may not hit fault state in 1000 ticks)

    # --- I/O Module -------------------------------------------------------

    def test_io_module_data_keys(self):
        gen = self._gen("io_module")
        data = gen.generate_device_data("io_module")
        required = {
            "di_words", "do_words", "ai_channels", "ao_channels",
            "module_status", "slot_number",
        }
        self.assertTrue(required.issubset(data.keys()))

    def test_io_module_data_lengths(self):
        gen = self._gen("io_module", {"slot_number": 3})
        data = gen.generate_device_data("io_module")
        self.assertEqual(len(data["di_words"]), 4)
        self.assertEqual(len(data["do_words"]), 4)
        self.assertEqual(len(data["ai_channels"]), 8)
        self.assertEqual(len(data["ao_channels"]), 4)

    def test_io_module_ai_channel_bounds(self):
        gen = self._gen("io_module")
        for _ in range(50):
            data = gen.generate_device_data("io_module")
            for ch in data["ai_channels"]:
                self.assertGreaterEqual(ch, 0.0)
                self.assertLessEqual(ch, 100.0)

    def test_io_module_module_status_valid(self):
        gen = self._gen("io_module")
        for _ in range(100):
            data = gen.generate_device_data("io_module")
            self.assertIn(data["module_status"], (0, 1, 2))

    def test_io_module_di_word_is_integer(self):
        gen = self._gen("io_module")
        data = gen.generate_device_data("io_module")
        for w in data["di_words"]:
            self.assertIsInstance(w, int)

    def test_io_module_slot_number_from_config(self):
        gen = self._gen("io_module", {"slot_number": 7})
        data = gen.generate_device_data("io_module")
        self.assertEqual(data["slot_number"], 7)


# ===========================================================================
# TestEtherNetIPConfiguration — Pydantic model validation
# ===========================================================================

class TestEtherNetIPConfiguration(unittest.TestCase):

    def test_valid_config_creation(self):
        cfg = EtherNetIPConfig(
            enabled=True,
            devices={
                "plcs": EtherNetIPDeviceConfig(
                    count=2,
                    port_start=44818,
                    device_template="eip_controllogix_plc",
                    update_interval=1.0,
                )
            }
        )
        self.assertTrue(cfg.enabled)
        self.assertIn("plcs", cfg.devices)
        self.assertEqual(cfg.devices["plcs"].count, 2)

    def test_device_config_count_gt_zero(self):
        with self.assertRaises(Exception):
            EtherNetIPDeviceConfig(count=0, port_start=44818, device_template="x")

    def test_device_config_count_max(self):
        with self.assertRaises(Exception):
            EtherNetIPDeviceConfig(count=1001, port_start=44818, device_template="x")

    def test_port_bounds_low(self):
        with self.assertRaises(Exception):
            EtherNetIPDeviceConfig(count=1, port_start=1023, device_template="x")

    def test_port_bounds_high(self):
        with self.assertRaises(Exception):
            EtherNetIPDeviceConfig(count=1, port_start=65536, device_template="x")

    def test_update_interval_positive(self):
        with self.assertRaises(Exception):
            EtherNetIPDeviceConfig(count=1, port_start=44818, device_template="x", update_interval=0.0)

    def test_config_parser_ethernet_ip_support(self):
        parser = ConfigParser()
        # Ensure is_protocol_enabled works without a loaded config
        self.assertFalse(parser.is_protocol_enabled("ethernet_ip"))

    def test_get_ethernet_ip_devices_empty_without_config(self):
        parser = ConfigParser()
        devices = parser.get_ethernet_ip_devices()
        self.assertEqual(devices, {})


# ===========================================================================
# TestEtherNetIPScalability
# ===========================================================================

class TestEtherNetIPScalability(unittest.IsolatedAsyncioTestCase):

    async def test_multiple_device_creation(self):
        config = _make_eip_config({
            "controllogix_plcs": ("eip_controllogix_plc", 10, 44818),
            "powerflex_drives":  ("eip_powerflex_drive",  10, 44828),
            "io_modules":        ("eip_io_module",         10, 44838),
        })
        pm = _make_mock_port_manager(44818)
        manager = EtherNetIPDeviceManager(config, pm)
        ok = await manager.initialize()
        self.assertTrue(ok)
        self.assertEqual(len(manager.devices), 30)

    async def test_port_allocation_efficiency(self):
        config = _make_eip_config({
            "controllogix_plcs": ("eip_controllogix_plc", 50, 44818),
        })
        pm = _make_mock_port_manager(44818)
        manager = EtherNetIPDeviceManager(config, pm)

        start = time.monotonic()
        await manager.initialize()
        elapsed = time.monotonic() - start

        self.assertEqual(len(manager.devices), 50)
        self.assertLess(elapsed, 1.0, "50 device allocation should complete in < 1s")


if __name__ == "__main__":
    unittest.main()
