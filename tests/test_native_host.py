import io
import struct
import subprocess
import sys
from uuid import uuid4

import pytest
from smartflow.native_host import MAX_MESSAGE_BYTES, ProtocolError, handle, read_message, serve, write_message

EXTENSION_ID = "a" * 32


def hello(**changes):
    return {
        "protocol_version": 1,
        "message_id": str(uuid4()),
        "kind": "hello",
        "extension_version": "0.1.0",
        **changes,
    }


def frame(payload):
    stream = io.BytesIO()
    write_message(stream, payload)
    return stream.getvalue()


def test_hello_roundtrip_and_clean_eof_never_claims_pairing():
    request = hello()
    target = io.BytesIO()
    serve(io.BytesIO(frame(request)), target, f"chrome-extension://{EXTENSION_ID}/", EXTENSION_ID)
    result = read_message(io.BytesIO(target.getvalue()))
    assert result["message_id"] == request["message_id"]
    assert result["state"] == "unpaired" and result["capabilities"] == []
    assert read_message(io.BytesIO()) is None


@pytest.mark.parametrize(
    "data",
    [
        b"\x10",
        struct.pack("=I", 20) + b"{}",
        struct.pack("=I", 0),
        struct.pack("=I", MAX_MESSAGE_BYTES + 1),
        struct.pack("=I", 1) + b"\xff",
        frame(None),
    ],
)
def test_bad_frames_are_bounded_and_rejected(data):
    with pytest.raises(ProtocolError):
        read_message(io.BytesIO(data))


@pytest.mark.parametrize(
    "changes",
    [
        {"protocol_version": 2},
        {"protocol_version": True},
        {"extension_version": "9.0.0"},
        {"kind": "dispatch"},
        {"shell": "anything"},
        {"message_id": "bad"},
    ],
)
def test_unknown_privileged_commands_and_version_mismatch_fail_closed(changes):
    with pytest.raises(ProtocolError):
        handle(hello(**changes))


def test_partial_reads_and_utf8_framing():
    class Split(io.BytesIO):
        def read(self, size=-1):
            return super().read(min(size, 2))

    payload = {"text": "ทดสอบภาษาไทย"}
    assert read_message(Split(frame(payload))) == payload


def test_wrong_extension_origin_is_rejected_before_reading():
    output = io.BytesIO()
    with pytest.raises(ProtocolError):
        serve(io.BytesIO(frame(hello())), output, "https://untrusted.example", EXTENSION_ID)
    assert output.getvalue() == b""


def test_native_host_subprocess_stdout_is_binary_protocol_only():
    request = hello()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "smartflow.native_host",
            "--extension-id",
            EXTENSION_ID,
            f"chrome-extension://{EXTENSION_ID}/",
        ],
        input=frame(request),
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0 and result.stderr == b""
    assert read_message(io.BytesIO(result.stdout))["message_id"] == request["message_id"]
