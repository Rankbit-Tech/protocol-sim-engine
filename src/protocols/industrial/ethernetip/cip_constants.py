"""
CIP (Common Industrial Protocol) Constants for EtherNet/IP Simulation

Covers the encapsulation layer commands, CIP service codes, data type codes,
status codes, and identity object defaults following the CIP specification.
"""

import struct


# ---------------------------------------------------------------------------
# Encapsulation Layer Command Codes (TCP port 44818)
# ---------------------------------------------------------------------------

class CIPCommand:
    """CIP Encapsulation Layer command codes."""
    LIST_SERVICES      = 0x0004  # List available services
    LIST_IDENTITY      = 0x0063  # Device discovery / identity
    LIST_INTERFACES    = 0x0064  # List communication interfaces
    REGISTER_SESSION   = 0x0065  # Establish a session
    UNREGISTER_SESSION = 0x0066  # Tear down a session
    SEND_RR_DATA       = 0x006F  # Explicit messaging (request-response)
    SEND_UNIT_DATA     = 0x0070  # Implicit messaging (I/O data)


# ---------------------------------------------------------------------------
# CIP Service Codes (inside SendRRData payload)
# ---------------------------------------------------------------------------

class CIPService:
    """CIP service codes for explicit messaging."""
    GET_ATTR_ALL    = 0x01  # Get all attributes of an object
    SET_ATTR_ALL    = 0x02  # Set all attributes of an object
    GET_ATTR_LIST   = 0x03  # Get selected attributes
    SET_ATTR_LIST   = 0x04  # Set selected attributes
    RESET           = 0x05  # Reset object
    START           = 0x06  # Start object
    STOP            = 0x07  # Stop object
    MULTI_SERVICE   = 0x0A  # Multiple Service Packet (bundle of requests)
    GET_ATTR_SINGLE = 0x0E  # Get single attribute
    SET_ATTR_SINGLE = 0x10  # Set single attribute
    READ_TAG        = 0x4C  # ControlLogix: read tag by symbolic name
    WRITE_TAG       = 0x4D  # ControlLogix: write tag by symbolic name
    READ_TAG_FRAG   = 0x52  # ControlLogix: read tag fragmented (large data)
    WRITE_TAG_FRAG  = 0x53  # ControlLogix: write tag fragmented

    # Response flag: OR'd with request service code
    RESPONSE_FLAG   = 0x80


# ---------------------------------------------------------------------------
# CIP Data Type Codes (EPATH type codes and tag type codes)
# ---------------------------------------------------------------------------

class CIPDataType:
    """CIP data type codes (from CIP spec Volume 1, Appendix C)."""
    BOOL   = 0xC1   # 1 byte  (bit 0)
    SINT   = 0xC2   # 1 byte  signed integer
    INT    = 0xC3   # 2 bytes signed integer
    DINT   = 0xC4   # 4 bytes signed integer
    LINT   = 0xC5   # 8 bytes signed integer
    USINT  = 0xC6   # 1 byte  unsigned integer
    UINT   = 0xC7   # 2 bytes unsigned integer
    UDINT  = 0xC8   # 4 bytes unsigned integer
    REAL   = 0xCA   # 4 bytes IEEE 754 float
    LREAL  = 0xCB   # 8 bytes IEEE 754 double
    STRING = 0xD0   # variable length string (2-byte length + chars)

    # Map type code -> (struct format char, byte size)
    # Used by pack/unpack helpers
    _FORMAT_MAP = {
        0xC1: ('B', 1),   # BOOL  - treated as unsigned byte
        0xC2: ('b', 1),   # SINT
        0xC3: ('h', 2),   # INT
        0xC4: ('i', 4),   # DINT
        0xC5: ('q', 8),   # LINT
        0xC6: ('B', 1),   # USINT
        0xC7: ('H', 2),   # UINT
        0xC8: ('I', 4),   # UDINT
        0xCA: ('f', 4),   # REAL
        0xCB: ('d', 8),   # LREAL
    }

    # Canonical type name strings for API display
    _NAME_MAP = {
        0xC1: 'BOOL',
        0xC2: 'SINT',
        0xC3: 'INT',
        0xC4: 'DINT',
        0xC5: 'LINT',
        0xC6: 'USINT',
        0xC7: 'UINT',
        0xC8: 'UDINT',
        0xCA: 'REAL',
        0xCB: 'LREAL',
        0xD0: 'STRING',
    }

    @classmethod
    def format_char(cls, type_code: int) -> str:
        """Return struct format character for a scalar type."""
        entry = cls._FORMAT_MAP.get(type_code)
        if entry is None:
            raise ValueError(f"Unsupported CIP data type: 0x{type_code:02X}")
        return entry[0]

    @classmethod
    def byte_size(cls, type_code: int) -> int:
        """Return byte size for a scalar type."""
        entry = cls._FORMAT_MAP.get(type_code)
        if entry is None:
            raise ValueError(f"Unsupported CIP data type: 0x{type_code:02X}")
        return entry[1]

    @classmethod
    def type_name(cls, type_code: int) -> str:
        """Return human-readable type name."""
        return cls._NAME_MAP.get(type_code, f"UNKNOWN(0x{type_code:02X})")


# ---------------------------------------------------------------------------
# CIP General Status Codes
# ---------------------------------------------------------------------------

class CIPStatus:
    """CIP general status codes."""
    SUCCESS              = 0x00
    CONNECTION_FAILURE   = 0x01
    RESOURCE_UNAVAILABLE = 0x02
    INVALID_PARAM_VALUE  = 0x03
    PATH_SEGMENT_ERROR   = 0x04
    PATH_UNKNOWN         = 0x05
    PARTIAL_TRANSFER     = 0x06
    CONNECTION_LOST      = 0x07
    FAILURE              = 0x08
    INVALID_ATTR_VALUE   = 0x09
    ATTR_LIST_ERROR      = 0x0A
    ALREADY_IN_STATE     = 0x0B
    OBJECT_STATE_CONFLICT= 0x0C
    OBJECT_ALREADY_EXISTS= 0x0D
    ATTR_NOT_SETTABLE    = 0x0E
    PRIVILEGE_VIOLATION  = 0x0F
    DEVICE_STATE_CONFLICT= 0x10
    REPLY_DATA_TOO_LARGE = 0x11
    FRAGMENTATION_NEEDED = 0x12
    NOT_ENOUGH_DATA      = 0x13
    ATTR_NOT_SUPPORTED   = 0x14
    TOO_MUCH_DATA        = 0x15
    OBJECT_NOT_EXIST     = 0x16
    INVALID_SESSION      = 0x0065  # Encapsulation-level: unregistered session


# ---------------------------------------------------------------------------
# Encapsulation Header Format
# ---------------------------------------------------------------------------

# Fixed 24-byte encapsulation header format (little-endian):
#   cmd (uint16), length (uint16), session_handle (uint32),
#   status (uint32), sender_context (8 bytes), options (uint32)
ENCAP_HEADER_SIZE   = 24
ENCAP_HEADER_FORMAT = "<HHII8sI"
# sender_context is 8 raw bytes (not split further)


# ---------------------------------------------------------------------------
# CPF (Common Packet Format) Item Type IDs
# ---------------------------------------------------------------------------

class CPFItemType:
    """Common Packet Format item type identifiers."""
    NULL              = 0x0000  # Address item with no data (unconnected)
    CONNECTED_ADDR    = 0x00A1  # Connected transport packet address
    CONNECTED_DATA    = 0x00B1  # Connected transport packet data
    UNCONNECTED_DATA  = 0x00B2  # Unconnected message data (explicit msg)
    SOCKET_ADDR_O2T   = 0x8000  # Socket address (originator-to-target)
    SOCKET_ADDR_T2O   = 0x8001  # Socket address (target-to-originator)
    SEQUENCED_ADDR    = 0x8002  # Sequenced address item


# ---------------------------------------------------------------------------
# EPATH Segment Types
# ---------------------------------------------------------------------------

class EPATHSegment:
    """EPATH segment type codes."""
    PORT            = 0x01  # Port segment
    LOGICAL_CLASS   = 0x20  # Logical: class ID
    LOGICAL_INST    = 0x24  # Logical: instance ID
    LOGICAL_MEMBER  = 0x28  # Logical: member ID
    LOGICAL_ATTR    = 0x30  # Logical: attribute ID
    SYMBOLIC        = 0x91  # Symbolic segment (tag name)
    DATA_SIMPLE     = 0x80  # Data segment
    DATA_ANSI_EXT   = 0x91  # ANSI extended symbolic (same byte value as SYMBOLIC)


# ---------------------------------------------------------------------------
# Identity Object Defaults (Class 0x01, Instance 0x01)
# ---------------------------------------------------------------------------

VENDOR_ID      = 0x0001   # Rockwell Automation
DEVICE_TYPE    = 0x000E   # Programmable Logic Controller
PRODUCT_CODE   = 0x0014   # Generic simulation device
REVISION_MAJOR = 1
REVISION_MINOR = 1
PROTOCOL_VERSION = 1      # CIP over Ethernet/IP protocol version

# ListIdentity response: identity item type
IDENTITY_ITEM_TYPE = 0x000C


# ---------------------------------------------------------------------------
# Default Port
# ---------------------------------------------------------------------------

DEFAULT_EIP_PORT = 44818  # Standard EtherNet/IP TCP port
