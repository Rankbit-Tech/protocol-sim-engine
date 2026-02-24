"""
CIPServer — Asyncio TCP Server for EtherNet/IP Simulation

Implements the EtherNet/IP encapsulation layer on TCP port 44818
(or any allocated port). Real clients such as pycomm3 can connect,
register sessions, and read/write ControlLogix-style symbolic tags.

Supported services:
    0x0063  ListIdentity
    0x0065  RegisterSession
    0x0066  UnregisterSession
    0x006F  SendRRData
        0x4C  ReadTag
        0x4D  WriteTag
        0x0A  MultipleServicePacket
"""

import asyncio
import random
import struct
import time
from typing import Any, Dict, List, Optional

import structlog

from .cip_constants import (
    CIPCommand, CIPService, CIPDataType, CIPStatus, CPFItemType,
    ENCAP_HEADER_SIZE,
)
from .cip_protocol import (
    decode_encap_header,
    encode_encap_header,
    encode_list_identity_response,
    encode_register_session_response,
    encode_unregister_session_response,
    encode_send_rr_data_response,
    encode_cip_read_tag_response,
    encode_cip_write_tag_response,
    encode_cip_error_response,
    encode_cip_multi_service_response,
    parse_send_rr_data_payload,
    parse_cip_service_request,
    parse_epath_symbolic,
    pack_cip_value,
    unpack_cip_value,
)

logger = structlog.get_logger(__name__)


class CIPServer:
    """
    Asyncio TCP server implementing the EtherNet/IP encapsulation protocol.

    The server is owned by one EtherNetIPDevice. It shares a mutable
    `tag_store` dict with the device's data-update loop. Because asyncio
    is single-threaded, no locking is required.

    tag_store format:
        {
            "TagName": {
                "type_code":     int,   # CIPDataType constant
                "value":         Any,   # scalar or list for arrays
                "element_count": int,   # 1 for scalars, >1 for arrays
            },
            ...
        }
    """

    def __init__(
        self,
        host: str,
        port: int,
        device_info: Dict[str, Any],
        tag_store: Dict[str, Dict[str, Any]],
    ):
        """
        Args:
            host:        Bind address, typically "0.0.0.0".
            port:        TCP port to listen on (44818 standard, or offset).
            device_info: Identity object fields:
                            vendor_id, device_type, product_code,
                            revision_major, revision_minor,
                            serial_number, product_name.
            tag_store:   Mutable dict shared with EtherNetIPDevice.
        """
        self.host = host
        self.port = port
        self.device_info = device_info
        self.tag_store = tag_store

        self.sessions: Dict[int, Dict[str, Any]] = {}
        self._server: Optional[asyncio.Server] = None
        self.error_count: int = 0
        self._connection_count: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> bool:
        """
        Start the asyncio TCP server.

        Returns True on success, False if the port cannot be bound
        (e.g. already in use).
        """
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port,
            )
            logger.info(
                "CIP server started",
                host=self.host,
                port=self.port,
                product_name=self.device_info.get("product_name"),
            )
            return True
        except OSError as exc:
            logger.error(
                "CIP server failed to bind",
                host=self.host,
                port=self.port,
                error=str(exc),
            )
            return False

    async def stop(self) -> None:
        """Close the server and all active sessions."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self.sessions.clear()
        logger.debug("CIP server stopped", port=self.port)

    # ------------------------------------------------------------------
    # Connection handler
    # ------------------------------------------------------------------

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Coroutine that handles one TCP connection for its full lifetime.

        Reads the 24-byte encapsulation header, reads the payload,
        dispatches to the appropriate handler, and writes the response.
        Loops until the client disconnects or an error occurs.
        """
        peer = writer.get_extra_info("peername", ("unknown", 0))
        self._connection_count += 1
        logger.debug("EtherNet/IP client connected", peer=peer, port=self.port)

        try:
            while True:
                # ── Read encapsulation header ──────────────────────────
                try:
                    raw_header = await reader.readexactly(ENCAP_HEADER_SIZE)
                except asyncio.IncompleteReadError:
                    break  # Client closed connection cleanly

                try:
                    hdr = decode_encap_header(raw_header)
                except ValueError as exc:
                    logger.warning("Bad CIP header", peer=peer, error=str(exc))
                    break

                # ── Read payload ───────────────────────────────────────
                payload = b""
                if hdr["length"] > 0:
                    try:
                        payload = await reader.readexactly(hdr["length"])
                    except asyncio.IncompleteReadError:
                        break

                # ── Dispatch and respond ───────────────────────────────
                try:
                    response = self._dispatch_command(
                        hdr["command"],
                        hdr["session_handle"],
                        hdr["sender_context"],
                        payload,
                    )
                    if response:
                        writer.write(response)
                        await writer.drain()
                except Exception as exc:
                    logger.error(
                        "CIP dispatch error",
                        peer=peer,
                        command=hex(hdr["command"]),
                        error=str(exc),
                    )
                    self.error_count += 1

        except ConnectionResetError:
            pass
        except Exception as exc:
            logger.error("CIP client handler error", peer=peer, error=str(exc))
            self.error_count += 1
        finally:
            # Clean up any sessions registered on this connection
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            logger.debug("EtherNet/IP client disconnected", peer=peer, port=self.port)

    # ------------------------------------------------------------------
    # Command dispatcher
    # ------------------------------------------------------------------

    def _dispatch_command(
        self,
        command: int,
        session_handle: int,
        sender_context: bytes,
        payload: bytes,
    ) -> bytes:
        """
        Route an encapsulation command to the appropriate handler.

        Returns complete response bytes (header + payload).
        Unknown commands return an error response.
        """
        if command == CIPCommand.LIST_IDENTITY:
            return self._handle_list_identity(sender_context)

        elif command == CIPCommand.REGISTER_SESSION:
            return self._handle_register_session(sender_context, payload)

        elif command == CIPCommand.UNREGISTER_SESSION:
            return self._handle_unregister_session(session_handle, sender_context)

        elif command == CIPCommand.SEND_RR_DATA:
            return self._handle_send_rr_data(session_handle, sender_context, payload)

        else:
            logger.debug("Unknown CIP command", command=hex(command))
            # Return header with non-zero status
            return encode_encap_header(
                command, 0, session_handle=0, status=0x0001,
                sender_context=sender_context,
            )

    # ------------------------------------------------------------------
    # ListIdentity (0x0063)
    # ------------------------------------------------------------------

    def _handle_list_identity(self, sender_context: bytes) -> bytes:
        """Respond to ListIdentity — no session required."""
        return encode_list_identity_response(self.device_info, sender_context)

    # ------------------------------------------------------------------
    # RegisterSession (0x0065)
    # ------------------------------------------------------------------

    def _handle_register_session(
        self, sender_context: bytes, payload: bytes
    ) -> bytes:
        """
        Assign a new session handle and register the session.

        The request payload must contain: protocol_version (uint16) + options (uint16).
        We validate protocol_version == 1.
        """
        if len(payload) >= 2:
            protocol_version = struct.unpack_from("<H", payload, 0)[0]
            if protocol_version != 1:
                logger.warning("RegisterSession: unsupported protocol version", version=protocol_version)

        handle = self._new_session_handle()
        self.sessions[handle] = {
            "created_at": time.time(),
        }
        logger.debug("Session registered", handle=hex(handle), total=len(self.sessions))
        return encode_register_session_response(handle, sender_context)

    # ------------------------------------------------------------------
    # UnregisterSession (0x0066)
    # ------------------------------------------------------------------

    def _handle_unregister_session(
        self, session_handle: int, sender_context: bytes
    ) -> bytes:
        """Remove session and respond."""
        removed = self.sessions.pop(session_handle, None)
        if removed:
            logger.debug("Session unregistered", handle=hex(session_handle))
        return encode_unregister_session_response(sender_context)

    # ------------------------------------------------------------------
    # SendRRData (0x006F)
    # ------------------------------------------------------------------

    def _handle_send_rr_data(
        self,
        session_handle: int,
        sender_context: bytes,
        payload: bytes,
    ) -> bytes:
        """
        Handle explicit messaging (request-response).

        1. Validate session handle.
        2. Parse CPF to extract raw CIP bytes.
        3. Dispatch to CIP service handler.
        4. Wrap response in SendRRData frame.
        """
        # Validate session
        if session_handle not in self.sessions:
            logger.warning("SendRRData: invalid session handle", handle=hex(session_handle))
            return encode_encap_header(
                CIPCommand.SEND_RR_DATA,
                0,
                session_handle=0,
                status=CIPStatus.INVALID_SESSION,
                sender_context=sender_context,
            )

        try:
            cpf = parse_send_rr_data_payload(payload)
            raw_cip = cpf["data_item"]["data"]
        except (ValueError, KeyError, IndexError) as exc:
            logger.warning("SendRRData: bad CPF payload", error=str(exc))
            cip_resp = encode_cip_error_response(0x00, CIPStatus.FAILURE)
            return encode_send_rr_data_response(session_handle, sender_context, cip_resp)

        try:
            req = parse_cip_service_request(raw_cip)
        except ValueError as exc:
            logger.warning("SendRRData: bad CIP request", error=str(exc))
            cip_resp = encode_cip_error_response(0x00, CIPStatus.FAILURE)
            return encode_send_rr_data_response(session_handle, sender_context, cip_resp)

        cip_resp = self._dispatch_cip_service(
            req["service_code"],
            req["path_bytes"],
            req["request_data"],
        )
        return encode_send_rr_data_response(session_handle, sender_context, cip_resp)

    # ------------------------------------------------------------------
    # CIP Service dispatcher
    # ------------------------------------------------------------------

    def _dispatch_cip_service(
        self,
        service_code: int,
        path_bytes: bytes,
        request_data: bytes,
    ) -> bytes:
        """Route CIP service code to the appropriate handler."""
        if service_code == CIPService.READ_TAG:
            return self._svc_read_tag(path_bytes, request_data)
        elif service_code == CIPService.WRITE_TAG:
            return self._svc_write_tag(path_bytes, request_data)
        elif service_code == CIPService.MULTI_SERVICE:
            return self._svc_multi_service(path_bytes, request_data)
        elif service_code == CIPService.GET_ATTR_ALL:
            return self._svc_get_identity(path_bytes)
        else:
            logger.debug("Unsupported CIP service", service=hex(service_code))
            return encode_cip_error_response(service_code, CIPStatus.FAILURE)

    # ------------------------------------------------------------------
    # ReadTag (0x4C)
    # ------------------------------------------------------------------

    def _svc_read_tag(self, path_bytes: bytes, request_data: bytes) -> bytes:
        """
        Handle ReadTag service.

        Request path:  symbolic EPATH → tag name
        Request data:  element_count (uint16_le, default 1)
        Response:      type_code (uint16) + packed value bytes
        """
        tag_name = parse_epath_symbolic(path_bytes)
        if tag_name is None:
            return encode_cip_error_response(CIPService.READ_TAG, CIPStatus.PATH_UNKNOWN)

        entry = self.tag_store.get(tag_name)
        if entry is None:
            logger.debug("ReadTag: tag not found", tag=tag_name)
            return encode_cip_error_response(CIPService.READ_TAG, CIPStatus.PATH_UNKNOWN)

        # Parse requested element count
        requested = 1
        if len(request_data) >= 2:
            requested = struct.unpack_from("<H", request_data, 0)[0]

        type_code     = entry["type_code"]
        value         = entry["value"]
        element_count = entry["element_count"]
        actual_count  = min(requested, element_count)

        try:
            if element_count > 1:
                # Array: slice to requested count
                slice_val = (value or [])[:actual_count]
                packed = pack_cip_value(type_code, slice_val, actual_count)
            else:
                packed = pack_cip_value(type_code, value, 1)
        except Exception as exc:
            logger.error("ReadTag: pack error", tag=tag_name, error=str(exc))
            return encode_cip_error_response(CIPService.READ_TAG, CIPStatus.FAILURE)

        return encode_cip_read_tag_response(type_code, packed)

    # ------------------------------------------------------------------
    # WriteTag (0x4D)
    # ------------------------------------------------------------------

    def _svc_write_tag(self, path_bytes: bytes, request_data: bytes) -> bytes:
        """
        Handle WriteTag service.

        Request data:  type_code (uint16) + element_count (uint16) + packed value
        """
        tag_name = parse_epath_symbolic(path_bytes)
        if tag_name is None:
            return encode_cip_error_response(CIPService.WRITE_TAG, CIPStatus.PATH_UNKNOWN)

        entry = self.tag_store.get(tag_name)
        if entry is None:
            logger.debug("WriteTag: tag not found", tag=tag_name)
            return encode_cip_error_response(CIPService.WRITE_TAG, CIPStatus.PATH_UNKNOWN)

        if len(request_data) < 4:
            return encode_cip_error_response(CIPService.WRITE_TAG, CIPStatus.NOT_ENOUGH_DATA)

        req_type, element_count = struct.unpack_from("<HH", request_data, 0)
        value_bytes = request_data[4:]

        # Validate type matches stored type
        if req_type != entry["type_code"]:
            logger.debug(
                "WriteTag: type mismatch",
                tag=tag_name,
                expected=hex(entry["type_code"]),
                got=hex(req_type),
            )
            return encode_cip_error_response(CIPService.WRITE_TAG, CIPStatus.INVALID_ATTR_VALUE)

        try:
            new_value = unpack_cip_value(req_type, value_bytes, element_count)
        except Exception as exc:
            logger.error("WriteTag: unpack error", tag=tag_name, error=str(exc))
            return encode_cip_error_response(CIPService.WRITE_TAG, CIPStatus.FAILURE)

        self.tag_store[tag_name]["value"] = new_value
        logger.debug("WriteTag: success", tag=tag_name, value=new_value)
        return encode_cip_write_tag_response(CIPService.WRITE_TAG)

    # ------------------------------------------------------------------
    # MultipleServicePacket (0x0A)
    # ------------------------------------------------------------------

    def _svc_multi_service(self, path_bytes: bytes, request_data: bytes) -> bytes:
        """
        Handle MultipleServicePacket — bundle of read/write requests.

        Request data wire layout:
            service_count (uint16_le)
            offsets[service_count] (uint16_le each)
            sub-request data (concatenated)

        Each offset is relative to the start of the service_count field.
        """
        if len(request_data) < 2:
            return encode_cip_error_response(CIPService.MULTI_SERVICE, CIPStatus.NOT_ENOUGH_DATA)

        service_count = struct.unpack_from("<H", request_data, 0)[0]
        if service_count == 0:
            return encode_cip_multi_service_response([])

        offset_table_start = 2
        if len(request_data) < offset_table_start + service_count * 2:
            return encode_cip_error_response(CIPService.MULTI_SERVICE, CIPStatus.NOT_ENOUGH_DATA)

        offsets = list(struct.unpack_from(f"<{service_count}H", request_data, offset_table_start))

        sub_responses = []
        for i, offset in enumerate(offsets):
            # Offset is from start of service_count field = start of request_data
            start = offset
            end   = offsets[i + 1] if i + 1 < service_count else len(request_data)
            sub_request = request_data[start:end]

            try:
                sub_req = parse_cip_service_request(sub_request)
                sub_resp = self._dispatch_cip_service(
                    sub_req["service_code"],
                    sub_req["path_bytes"],
                    sub_req["request_data"],
                )
            except Exception as exc:
                logger.error("MultiService sub-request error", index=i, error=str(exc))
                sub_resp = encode_cip_error_response(0x00, CIPStatus.FAILURE)

            sub_responses.append(sub_resp)

        return encode_cip_multi_service_response(sub_responses)

    # ------------------------------------------------------------------
    # GetAttributesAll for Identity Object (class 0x01)
    # ------------------------------------------------------------------

    def _svc_get_identity(self, path_bytes: bytes) -> bytes:
        """
        Minimal GetAttributesAll for the identity object.
        Returns key identity fields for clients that probe the device.
        """
        info = self.device_info
        name_bytes = info.get("product_name", "").encode("ascii")[:62]

        data = struct.pack(
            "<HHHBB",
            info.get("vendor_id", 1),
            info.get("device_type", 0x000E),
            info.get("product_code", 0x0014),
            info.get("revision_major", 1),
            info.get("revision_minor", 1),
        ) + struct.pack("HI", 0x0030, info.get("serial_number", 0)) \
          + struct.pack("B", len(name_bytes)) + name_bytes

        response = struct.pack(
            "BBBB",
            CIPService.GET_ATTR_ALL | CIPService.RESPONSE_FLAG,
            0x00,
            CIPStatus.SUCCESS,
            0x00,
        ) + data
        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_session_handle(self) -> int:
        """Generate a unique non-zero uint32 session handle."""
        while True:
            handle = random.randint(1, 0xFFFFFFFF)
            if handle not in self.sessions:
                return handle

    def get_session_count(self) -> int:
        """Return the number of currently active sessions."""
        return len(self.sessions)

    def get_tag_names(self) -> List[str]:
        """Return sorted list of all tag names."""
        return sorted(self.tag_store.keys())
