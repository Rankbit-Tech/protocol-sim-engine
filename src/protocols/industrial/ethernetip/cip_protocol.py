"""
CIP Protocol Codec — Pure Encode/Decode Functions (No I/O)

All functions are pure transformations: bytes in, bytes out.
They can be unit-tested without any network or asyncio setup.

Wire format follows the EtherNet/IP Specification (ODVA) and
the Allen-Bradley ControlLogix tag-access extensions.
"""

import struct
import math
from typing import Any, Dict, List, Optional, Tuple

from .cip_constants import (
    CIPCommand, CIPService, CIPDataType, CIPStatus, CPFItemType,
    ENCAP_HEADER_SIZE, ENCAP_HEADER_FORMAT,
    IDENTITY_ITEM_TYPE, PROTOCOL_VERSION,
    VENDOR_ID, DEVICE_TYPE, PRODUCT_CODE, REVISION_MAJOR, REVISION_MINOR,
)


# ---------------------------------------------------------------------------
# Encapsulation Header
# ---------------------------------------------------------------------------

def encode_encap_header(
    command: int,
    length: int,
    session_handle: int = 0,
    status: int = 0,
    sender_context: bytes = b'\x00' * 8,
    options: int = 0,
) -> bytes:
    """
    Pack a 24-byte CIP encapsulation header (little-endian).

    Args:
        command:        CIPCommand code (uint16)
        length:         Payload length in bytes (uint16)
        session_handle: Session identifier assigned by server (uint32)
        status:         Encapsulation status (uint32) — 0 = success
        sender_context: 8-byte opaque context echoed from request
        options:        Always 0 (uint32)

    Returns:
        24 bytes of packed header.
    """
    ctx = (sender_context + b'\x00' * 8)[:8]
    return struct.pack(
        ENCAP_HEADER_FORMAT,
        command,
        length,
        session_handle,
        status,
        ctx,
        options,
    )


def decode_encap_header(data: bytes) -> Dict[str, Any]:
    """
    Unpack a 24-byte CIP encapsulation header.

    Returns:
        dict with keys: command (int), length (int), session_handle (int),
        status (int), sender_context (bytes[8]), options (int).

    Raises:
        ValueError if len(data) < 24.
    """
    if len(data) < ENCAP_HEADER_SIZE:
        raise ValueError(
            f"CIP encapsulation header requires {ENCAP_HEADER_SIZE} bytes, "
            f"got {len(data)}"
        )
    command, length, session_handle, status, sender_context, options = struct.unpack_from(
        ENCAP_HEADER_FORMAT, data, 0
    )
    return {
        "command": command,
        "length": length,
        "session_handle": session_handle,
        "status": status,
        "sender_context": sender_context,
        "options": options,
    }


# ---------------------------------------------------------------------------
# ListIdentity Response (0x0063)
# ---------------------------------------------------------------------------

def encode_list_identity_response(
    device_info: Dict[str, Any],
    sender_context: bytes,
) -> bytes:
    """
    Build a complete ListIdentity response.

    device_info keys:
        vendor_id (int), device_type (int), product_code (int),
        revision_major (int), revision_minor (int),
        serial_number (int), product_name (str)

    Returns:
        Encap header (24 bytes) + CPF item count (2 bytes) +
        identity item header (4 bytes) + identity item data.
    """
    vendor_id    = device_info.get("vendor_id",    VENDOR_ID)
    device_type  = device_info.get("device_type",  DEVICE_TYPE)
    product_code = device_info.get("product_code", PRODUCT_CODE)
    rev_major    = device_info.get("revision_major", REVISION_MAJOR)
    rev_minor    = device_info.get("revision_minor", REVISION_MINOR)
    serial_num   = device_info.get("serial_number", 0)
    product_name = device_info.get("product_name", "Protocol Sim Engine")

    name_bytes = product_name.encode("ascii")[:62]
    name_len   = len(name_bytes)

    # Identity item data (per CIP spec):
    # protocol_version(2), socket_addr(16), vendor_id(2), device_type(2),
    # product_code(2), revision(1+1), status(2), serial_number(4),
    # product_name_length(1), product_name(n), state(1)
    socket_addr = b'\x00' * 16  # zero socket address
    item_data = struct.pack(
        "<H16sHHHBBHI",
        PROTOCOL_VERSION,  # protocol_version
        socket_addr,       # sin_family(2) + sin_port(2) + sin_addr(4) + zero(8)
        vendor_id,
        device_type,
        product_code,
        rev_major,
        rev_minor,
        0x0030,            # device status (0x0030 = Owned + Configured)
        serial_num,
    ) + struct.pack("B", name_len) + name_bytes + b'\x00'  # state=0

    item_len = len(item_data)

    # CPF: item_count(2) + item_type(2) + item_length(2) + item_data
    cpf = struct.pack("<HHH", 1, IDENTITY_ITEM_TYPE, item_len) + item_data

    header = encode_encap_header(
        CIPCommand.LIST_IDENTITY,
        len(cpf),
        session_handle=0,
        status=0,
        sender_context=sender_context,
    )
    return header + cpf


# ---------------------------------------------------------------------------
# RegisterSession (0x0065)
# ---------------------------------------------------------------------------

def encode_register_session_response(
    session_handle: int,
    sender_context: bytes,
) -> bytes:
    """
    Build a RegisterSession response.

    Payload: protocol_version (uint16=1) + options_flags (uint16=0).
    The session_handle is included in the encap header (assigned by server).
    """
    payload = struct.pack("<HH", PROTOCOL_VERSION, 0)
    header = encode_encap_header(
        CIPCommand.REGISTER_SESSION,
        len(payload),
        session_handle=session_handle,
        status=0,
        sender_context=sender_context,
    )
    return header + payload


# ---------------------------------------------------------------------------
# UnregisterSession (0x0066)
# ---------------------------------------------------------------------------

def encode_unregister_session_response(sender_context: bytes) -> bytes:
    """
    Build an UnregisterSession response.

    No payload. Session is torn down; server closes the connection.
    """
    return encode_encap_header(
        CIPCommand.UNREGISTER_SESSION,
        0,
        session_handle=0,
        status=0,
        sender_context=sender_context,
    )


# ---------------------------------------------------------------------------
# SendRRData (0x006F) — CPF Parsing / Building
# ---------------------------------------------------------------------------

def parse_send_rr_data_payload(payload: bytes) -> Dict[str, Any]:
    """
    Parse the payload of a SendRRData request.

    Wire layout:
        interface_handle (uint32) — always 0
        timeout          (uint16)
        item_count       (uint16) — always 2
        address_item:
            type_id (uint16) — 0x0000 = NULL
            length  (uint16) — 0
        data_item:
            type_id (uint16) — 0x00B2 = Unconnected Data
            length  (uint16)
            data    (bytes)

    Returns dict:
        interface_handle, timeout, item_count,
        address_item: {type_id, length},
        data_item: {type_id, length, data}
    """
    if len(payload) < 16:
        raise ValueError(f"SendRRData payload too short: {len(payload)} bytes")

    offset = 0
    interface_handle, timeout, item_count = struct.unpack_from("<IHH", payload, offset)
    offset += 8

    items = []
    for _ in range(item_count):
        if offset + 4 > len(payload):
            break
        type_id, length = struct.unpack_from("<HH", payload, offset)
        offset += 4
        data = payload[offset: offset + length]
        offset += length
        items.append({"type_id": type_id, "length": length, "data": data})

    address_item = items[0] if len(items) > 0 else {"type_id": 0, "length": 0}
    data_item    = items[1] if len(items) > 1 else {"type_id": 0, "length": 0, "data": b""}

    return {
        "interface_handle": interface_handle,
        "timeout": timeout,
        "item_count": item_count,
        "address_item": address_item,
        "data_item": data_item,
    }


def encode_send_rr_data_response(
    session_handle: int,
    sender_context: bytes,
    cip_response: bytes,
) -> bytes:
    """
    Wrap a raw CIP service response in a SendRRData frame.

    CPF structure:
        interface_handle(4) + timeout(2) + item_count(2=2) +
        NULL address item  (type=0x0000, len=0) +
        Unconnected data item (type=0x00B2, len=N) + cip_response
    """
    cpf = struct.pack(
        "<IHHHHH",
        0,                             # interface_handle
        0,                             # timeout
        2,                             # item_count
        CPFItemType.NULL, 0,           # address item (type, length)
        CPFItemType.UNCONNECTED_DATA,  # data item type
        len(cip_response),             # data item length
    ) + cip_response

    header = encode_encap_header(
        CIPCommand.SEND_RR_DATA,
        len(cpf),
        session_handle=session_handle,
        status=0,
        sender_context=sender_context,
    )
    return header + cpf


# ---------------------------------------------------------------------------
# CIP Service Request Parsing
# ---------------------------------------------------------------------------

def parse_cip_service_request(data: bytes) -> Dict[str, Any]:
    """
    Parse a raw CIP service request (the data_item.data from SendRRData).

    Wire layout:
        service_code   (uint8)
        path_size      (uint8)  — in 16-bit words
        path_bytes     (path_size * 2 bytes)
        request_data   (remaining bytes)

    Returns dict:
        service_code (int), path_size_words (int),
        path_bytes (bytes), request_data (bytes)
    """
    if len(data) < 2:
        raise ValueError(f"CIP request too short: {len(data)} bytes")

    service_code, path_size_words = struct.unpack_from("BB", data, 0)
    path_len = path_size_words * 2
    path_bytes = data[2: 2 + path_len]
    request_data = data[2 + path_len:]

    return {
        "service_code": service_code,
        "path_size_words": path_size_words,
        "path_bytes": path_bytes,
        "request_data": request_data,
    }


def parse_epath_symbolic(path_bytes: bytes) -> Optional[str]:
    """
    Extract a tag name from a symbolic EPATH.

    Symbolic segment format (ANSI Extended Symbolic):
        0x91         (1 byte) — segment type
        name_length  (1 byte) — number of ASCII characters
        name_bytes   (name_length bytes) — ASCII tag name
        padding      (1 byte if name_length is odd, for 16-bit alignment)

    Compound paths (e.g. "Program:Main.Tag") are passed through as-is
    by concatenating all symbolic segments with a dot.

    Returns the tag name string, or None if no symbolic segment found.
    """
    tag_parts = []
    offset = 0
    while offset < len(path_bytes):
        segment_type = path_bytes[offset]
        offset += 1

        if segment_type == 0x91:
            # ANSI Extended Symbolic segment
            if offset >= len(path_bytes):
                break
            name_len = path_bytes[offset]
            offset += 1
            name = path_bytes[offset: offset + name_len].decode("ascii", errors="replace")
            offset += name_len
            if name_len % 2 != 0:
                offset += 1  # pad byte for 16-bit alignment
            tag_parts.append(name)

        elif (segment_type & 0xFC) == 0x20:
            # Logical class segment (1 or 2 extra bytes)
            logical_fmt = (segment_type & 0x03)
            if logical_fmt == 0:
                offset += 1  # 8-bit value
            elif logical_fmt == 1:
                offset += 1  # padding + 16-bit value
                offset += 2
            else:
                break

        elif (segment_type & 0xFC) == 0x24:
            # Logical instance segment
            logical_fmt = (segment_type & 0x03)
            if logical_fmt == 0:
                offset += 1
            elif logical_fmt == 1:
                offset += 1
                offset += 2
            else:
                break

        else:
            # Unknown segment — stop parsing
            break

    return tag_parts[0] if tag_parts else None


# ---------------------------------------------------------------------------
# CIP Service Responses
# ---------------------------------------------------------------------------

def encode_cip_read_tag_response(type_code: int, packed_data: bytes) -> bytes:
    """
    Build a CIP ReadTag (0x4C) success response.

    Wire layout:
        service  (uint8)  = 0x4C | 0x80 = 0xCC
        reserved (uint8)  = 0x00
        status   (uint8)  = 0x00 (success)
        ext_size (uint8)  = 0x00 (no extended status)
        type     (uint16_le) — CIP data type code
        data     (bytes)     — packed tag value(s)
    """
    return struct.pack(
        "<BBBBh",
        CIPService.READ_TAG | CIPService.RESPONSE_FLAG,
        0x00,            # reserved
        CIPStatus.SUCCESS,
        0x00,            # extended status size (words)
        type_code,       # data type code (int16)
    ) + packed_data


def encode_cip_write_tag_response(service_code: int) -> bytes:
    """
    Build a CIP WriteTag (0x4D) success response.

    Wire layout:
        service  (uint8)  = service_code | 0x80
        reserved (uint8)  = 0x00
        status   (uint8)  = 0x00 (success)
        ext_size (uint8)  = 0x00
    """
    return struct.pack(
        "BBBB",
        service_code | CIPService.RESPONSE_FLAG,
        0x00,
        CIPStatus.SUCCESS,
        0x00,
    )


def encode_cip_error_response(service_code: int, status: int) -> bytes:
    """
    Build a CIP error response for any service.

    Wire layout:
        service  (uint8)  = service_code | 0x80
        reserved (uint8)  = 0x00
        status   (uint8)  = error status code
        ext_size (uint8)  = 0x00 (no additional status words)
    """
    return struct.pack(
        "BBBB",
        service_code | CIPService.RESPONSE_FLAG,
        0x00,
        status & 0xFF,
        0x00,
    )


def encode_cip_multi_service_response(sub_responses: List[bytes]) -> bytes:
    """
    Build a MultipleServicePacket (0x0A) response.

    Wire layout:
        service    (uint8)  = 0x0A | 0x80 = 0x8A
        reserved   (uint8)  = 0x00
        status     (uint8)  = 0x00
        ext_size   (uint8)  = 0x00
        svc_count  (uint16_le)
        offsets    (uint16_le each) — relative to start of svc_count field
        sub_responses (concatenated)

    The offset to the first sub-response is:
        2 (svc_count) + 2 * len(sub_responses) (offset table)
    """
    count = len(sub_responses)
    offset_table_size = 2 + count * 2  # svc_count field + one uint16 per entry
    current_offset = offset_table_size
    offsets = []
    for resp in sub_responses:
        offsets.append(current_offset)
        current_offset += len(resp)

    header = struct.pack("BBBBH", 0x8A, 0x00, 0x00, 0x00, count)
    offset_bytes = struct.pack(f"<{count}H", *offsets)
    return header + offset_bytes + b"".join(sub_responses)


# ---------------------------------------------------------------------------
# CIP Value Pack / Unpack
# ---------------------------------------------------------------------------

def pack_cip_value(type_code: int, value: Any, element_count: int = 1) -> bytes:
    """
    Serialize a Python value (scalar or list) to CIP wire bytes.

    For scalar types (element_count == 1):
        BOOL  → 1 byte, 0x00 (False) or 0xFF (True)
        SINT  → struct.pack('<b', value)
        INT   → struct.pack('<h', value)
        DINT  → struct.pack('<i', value)
        REAL  → struct.pack('<f', value)

    For arrays (element_count > 1):
        value must be a list; elements are packed and concatenated.

    Raises:
        ValueError for unsupported type codes or wrong value types.
    """
    if type_code == CIPDataType.BOOL:
        fmt = 'B'
        if element_count == 1:
            v = 0xFF if value else 0x00
            return struct.pack(fmt, v)
        else:
            vals = value if isinstance(value, (list, tuple)) else [value]
            return b"".join(struct.pack(fmt, 0xFF if v else 0x00) for v in vals)

    if type_code not in CIPDataType._FORMAT_MAP:
        raise ValueError(f"Unsupported CIP type code for packing: 0x{type_code:02X}")

    fmt_char = CIPDataType.format_char(type_code)
    fmt = f"<{fmt_char}"

    if element_count == 1:
        return struct.pack(fmt, _coerce(type_code, value))
    else:
        vals = value if isinstance(value, (list, tuple)) else [value] * element_count
        return b"".join(struct.pack(fmt, _coerce(type_code, v)) for v in vals)


def unpack_cip_value(type_code: int, data: bytes, element_count: int = 1) -> Any:
    """
    Deserialize CIP wire bytes to a Python value (scalar or list).

    Returns a scalar for element_count == 1, a list otherwise.

    Raises:
        ValueError for unsupported types or insufficient data.
    """
    if type_code == CIPDataType.BOOL:
        elem_size = 1
        if len(data) < elem_size * element_count:
            raise ValueError("Insufficient data for BOOL unpack")
        if element_count == 1:
            return data[0] != 0x00
        return [data[i] != 0x00 for i in range(element_count)]

    if type_code not in CIPDataType._FORMAT_MAP:
        raise ValueError(f"Unsupported CIP type code for unpacking: 0x{type_code:02X}")

    fmt_char = CIPDataType.format_char(type_code)
    elem_size = CIPDataType.byte_size(type_code)
    fmt = f"<{fmt_char}"

    if len(data) < elem_size * element_count:
        raise ValueError(
            f"Insufficient data for type 0x{type_code:02X}: "
            f"need {elem_size * element_count}, got {len(data)}"
        )

    if element_count == 1:
        return struct.unpack_from(fmt, data, 0)[0]

    return [struct.unpack_from(fmt, data, i * elem_size)[0] for i in range(element_count)]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coerce(type_code: int, value: Any) -> Any:
    """Coerce a Python value to the appropriate numeric type for struct.pack."""
    if type_code in (CIPDataType.SINT, CIPDataType.INT, CIPDataType.DINT):
        return int(round(value))
    if type_code in (CIPDataType.USINT, CIPDataType.UINT, CIPDataType.UDINT):
        return int(round(value))
    if type_code in (CIPDataType.REAL, CIPDataType.LREAL):
        return float(value)
    return value
