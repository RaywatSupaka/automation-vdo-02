"""Bounded native protocol for pairing/status only; never provider dispatch."""

import argparse
import json
import os
import re
import struct
import sys
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

MAX_MESSAGE_BYTES = 64 * 1024
PROTOCOL_VERSION = 1
HELPER_VERSION = "0.1.1"


class Hello(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol_version: Literal[1]
    message_id: UUID
    kind: Literal["hello", "pair"]
    extension_version: Literal["0.1.1"]
    code: str | None = None


class ProtocolError(Exception):
    pass


def read_exact(reader, size):
    chunks = bytearray()
    while len(chunks) < size:
        chunk = reader.read(size - len(chunks))
        if not chunk:
            raise ProtocolError("FRAME_TRUNCATED")
        chunks.extend(chunk)
    return bytes(chunks)


def read_message(reader):
    first = reader.read(1)
    if not first:
        return None
    size = struct.unpack("=I", first + read_exact(reader, 3))[0]
    if not 0 < size <= MAX_MESSAGE_BYTES:
        raise ProtocolError("FRAME_SIZE_INVALID")
    try:
        payload = json.loads(read_exact(reader, size).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("object required")
        return payload
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ProtocolError("FRAME_JSON_INVALID") from exc


def write_message(writer, payload):
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ProtocolError("FRAME_SIZE_INVALID")
    writer.write(struct.pack("=I", len(encoded)) + encoded)
    writer.flush()


def handle(payload, client=None):
    try:
        message = Hello.model_validate(payload)
        # bool is an int in Python; do not let True impersonate protocol version 1.
        if type(payload["protocol_version"]) is not int:
            raise ValueError("protocol type")
        if message.kind == "pair" and (
            not message.code or not re.fullmatch(r"[A-Za-z0-9_-]{43}", message.code)
        ):
            raise ValueError("pairing code required")
        if message.kind == "hello" and message.code is not None:
            raise ValueError("unexpected pairing code")
    except (ValidationError, ValueError, TypeError) as exc:
        raise ProtocolError("PROTOCOL_INVALID") from exc
    return {
        "protocol_version": PROTOCOL_VERSION,
        "message_id": str(message.message_id),
        "kind": "bridge.result",
        "helper_version": HELPER_VERSION,
        "state": client.execute(message) if client else "unpaired",
        "capabilities": [],
    }


def serve(reader, writer, origin, extension_id, client=None):
    if not re.fullmatch(r"[a-p]{32}", extension_id) or origin != f"chrome-extension://{extension_id}/":
        raise ProtocolError("EXTENSION_ORIGIN_REJECTED")
    while (message := read_message(reader)) is not None:
        write_message(writer, handle(message, client))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extension-id", help="Exact ID for isolated framing tests")
    parser.add_argument("origin")
    parser.add_argument("--parent-window")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    client = None
    extension_id = args.extension_id
    config_path = args.config or Path(sys.executable).with_suffix(".json")
    if not extension_id:
        from smartflow.native_client import NativeClient

        config = json.loads(config_path.read_text())
        extension_id = config["extension_id"]
        client = NativeClient(config)
    if os.name == "nt":
        import msvcrt

        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    try:
        serve(sys.stdin.buffer, sys.stdout.buffer, args.origin, extension_id, client)
    except (ProtocolError, OSError):
        # Never emit raw message/exception/credential to stdout or stderr.
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
