r"""Encoding/decoding of arbitrary ASCII strings into Rucio-safe identifiers.

Rucio identifiers must match ``^[A-Za-z0-9][A-Za-z0-9.\-_]*$``.

Encoding rules:
- Letters (A-Za-z), digits (0-9), dots (.) and underscores (_) pass through unchanged.
- A literal dash (-) is encoded as ``--``.
- Any other ASCII character is encoded as ``-XX-`` where *XX* is the
  upper-case two-digit hex code of the character's ordinal value.

The first character of the input is assumed to be a permitted character
(letter or digit).
"""

import re

# Characters that are allowed to pass through verbatim (excluding dash).
_SAFE_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._"
)


def encode(s: str) -> str:
    r"""Encode an ASCII string into a Rucio-safe identifier.

    Parameters
    ----------
    s : str
        The original ASCII string.

    Returns
    -------
    str
        Encoded string matching ``^[A-Za-z0-9][A-Za-z0-9.\-_]*$``.

    Examples
    --------
    >>> encode("hello_world")
    'hello_world'
    >>> encode("path/to/file")
    'path-2F-to-2F-file'
    >>> encode("a-b")
    'a--b'
    >>> encode("a - b")
    'a-20----20-b'

    """
    parts: list[str] = []
    for ch in s:
        if ch in _SAFE_CHARS:
            parts.append(ch)
        elif ch == "-":
            parts.append("--")
        else:
            parts.append(f"-{ord(ch):02X}-")
    return "".join(parts)


# Pattern that matches a single encoded token:
#   --        -> literal dash
#   -XX-      -> hex-encoded character
#   .         -> any literal safe character
_DECODE_RE = re.compile(r"--|-([0-9A-Fa-f]{2})-|(.)")


def decode(s: str) -> str:
    """Decode a Rucio-safe identifier back into the original ASCII string.

    Parameters
    ----------
    s : str
        A previously encoded string.

    Returns
    -------
    str
        The original ASCII string.

    Examples
    --------
    >>> decode("hello_world")
    'hello_world'
    >>> decode("path-2F-to-2F-file")
    'path/to/file'
    >>> decode("a--b")
    'a-b'
    >>> decode("a-20----20-b")
    'a - b'

    """

    def _replace(m: re.Match) -> str:
        full = m.group(0)
        if full == "--":
            return "-"
        hex_code = m.group(1)
        if hex_code is not None:
            return chr(int(hex_code, 16))
        # Literal safe character
        return m.group(2)

    return _DECODE_RE.sub(_replace, s)
