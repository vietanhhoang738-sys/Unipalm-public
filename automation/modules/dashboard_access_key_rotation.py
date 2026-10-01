"""Rotate the encryption key for an existing Unipalm dashboard artifact.

This module intentionally works from the already-encrypted ``index.html`` and
never needs to query production data sources.  It decrypts the two embedded UI
artifacts with the current dashboard key, then re-encrypts the exact plaintext
HTML with a new high-entropy key, fresh salt and fresh IV.

No key material, key hashes, plaintext dashboard HTML, or business payload is
printed by the CLI.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


PBKDF2_ITERATIONS = 210_000
MIN_NEXT_KEY_LENGTH = 48
MIN_DISTINCT_CHARACTERS = 16

_META_RE = re.compile(
    r"const META=\{v2:(\{[^{}]*\}),v1:(\{[^{}]*\})\};"
)
_PAYLOAD_RE = {
    "v2": re.compile(
        r'(<script id="p-v2" type="application/octet-stream">)(.*?)(</script>)',
        re.S,
    ),
    "v1": re.compile(
        r'(<script id="p-v1" type="application/octet-stream">)(.*?)(</script>)',
        re.S,
    ),
}


def validate_next_key(key: str) -> None:
    """Fail closed unless the replacement key is suitable for public ciphertext."""
    if len(key) < MIN_NEXT_KEY_LENGTH:
        raise ValueError(
            f"replacement dashboard key must be at least {MIN_NEXT_KEY_LENGTH} characters"
        )
    if len(set(key)) < MIN_DISTINCT_CHARACTERS:
        raise ValueError(
            "replacement dashboard key does not contain enough distinct characters"
        )


def _derive_key(access_key: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", access_key.encode("utf-8"), salt, int(iterations), 32
    )


def _decrypt_html(ciphertext_b64: str, meta: Dict[str, Any], access_key: str) -> str:
    salt = base64.b64decode(meta["s"])
    iv = base64.b64decode(meta["i"])
    aad = str(meta["a"]).encode("utf-8")
    iterations = int(meta["n"])
    key = _derive_key(access_key, salt, iterations)
    compressed = AESGCM(key).decrypt(iv, base64.b64decode(ciphertext_b64), aad)
    return gzip.decompress(compressed).decode("utf-8")


def _encrypt_html(html: str, access_key: str, aad_text: str) -> Dict[str, Any]:
    salt = os.urandom(16)
    iv = os.urandom(12)
    aad = aad_text.encode("utf-8")
    key = _derive_key(access_key, salt, PBKDF2_ITERATIONS)
    cipher = AESGCM(key).encrypt(
        iv, gzip.compress(html.encode("utf-8"), 9), aad
    )
    encode = lambda value: base64.b64encode(value).decode("ascii")
    return {
        "s": encode(salt),
        "i": encode(iv),
        "n": PBKDF2_ITERATIONS,
        "a": aad_text,
        "p": encode(cipher),
    }


def _parse_wrapper(wrapper: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    meta_match = _META_RE.search(wrapper)
    if not meta_match:
        raise ValueError("dashboard wrapper META block not found or has unexpected shape")

    metadata = {
        "v2": json.loads(meta_match.group(1)),
        "v1": json.loads(meta_match.group(2)),
    }
    payloads: Dict[str, str] = {}
    for ui, pattern in _PAYLOAD_RE.items():
        match = pattern.search(wrapper)
        if not match:
            raise ValueError(f"dashboard wrapper {ui} encrypted payload not found")
        payloads[ui] = match.group(2).strip()
    return metadata, payloads


def rotate_wrapper_text(
    wrapper: str,
    *,
    current_key: str,
    next_key: str,
) -> Tuple[str, Dict[str, Any]]:
    """Return a wrapper encrypted with ``next_key`` and sanitized metadata."""
    if not current_key:
        raise ValueError("current dashboard key is blank")
    validate_next_key(next_key)
    if current_key == next_key:
        raise ValueError("replacement dashboard key must differ from the current key")

    metadata, payloads = _parse_wrapper(wrapper)
    plaintext: Dict[str, str] = {
        ui: _decrypt_html(payloads[ui], metadata[ui], current_key)
        for ui in ("v2", "v1")
    }
    rotated = {
        ui: _encrypt_html(plaintext[ui], next_key, str(metadata[ui]["a"]))
        for ui in ("v2", "v1")
    }

    output = wrapper
    for ui in ("v2", "v1"):
        pattern = _PAYLOAD_RE[ui]
        output, count = pattern.subn(
            lambda match, value=rotated[ui]["p"]: match.group(1)
            + value
            + match.group(3),
            output,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"expected to replace exactly one {ui} payload")

    replacement_meta = (
        "const META={v2:"
        + json.dumps(
            {k: rotated["v2"][k] for k in ("s", "i", "n", "a")},
            separators=(",", ":"),
        )
        + ",v1:"
        + json.dumps(
            {k: rotated["v1"][k] for k in ("s", "i", "n", "a")},
            separators=(",", ":"),
        )
        + "};"
    )
    output, count = _META_RE.subn(replacement_meta, output, count=1)
    if count != 1:
        raise RuntimeError("expected to replace exactly one META block")

    check_meta, check_payloads = _parse_wrapper(output)
    for ui in ("v2", "v1"):
        recovered = _decrypt_html(check_payloads[ui], check_meta[ui], next_key)
        if recovered != plaintext[ui]:
            raise RuntimeError(f"rotated {ui} plaintext verification failed")
        try:
            _decrypt_html(check_payloads[ui], check_meta[ui], current_key)
        except Exception:
            pass
        else:
            raise RuntimeError(f"current key unexpectedly decrypts rotated {ui} artifact")

    audit = {
        "status": "PASS",
        "rotationVersion": "dashboard-access-key-rotation-v1",
        "uiArtifacts": ["v2", "v1"],
        "pbkdf2Iterations": PBKDF2_ITERATIONS,
        "nextKeyLengthGate": MIN_NEXT_KEY_LENGTH,
        "plaintextPreserved": True,
        "currentKeyRejectedAfterRotation": True,
    }
    return output, audit


def rotate_file(input_path: Path, output_path: Path, current_key: str, next_key: str) -> Dict[str, Any]:
    wrapper = input_path.read_text(encoding="utf-8")
    rotated, audit = rotate_wrapper_text(
        wrapper, current_key=current_key, next_key=next_key
    )
    output_path.write_text(rotated, encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="index.html")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    current_key = os.environ.get("UNIPALM_DASHBOARD_ACCESS_KEY", "")
    next_key = os.environ.get("UNIPALM_DASHBOARD_ACCESS_KEY_NEXT", "")
    audit = rotate_file(
        Path(args.input), Path(args.output), current_key=current_key, next_key=next_key
    )
    print(json.dumps(audit, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
