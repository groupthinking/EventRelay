"""Log-injection (CWE-117) sanitization helpers."""

# Characters that can forge or corrupt log records: CR/LF and the other
# Unicode line boundaries, plus terminal control chars (ESC) usable for
# ANSI-escape spoofing. Mapped to ``None`` so ``str.translate`` drops them.
_UNSAFE_LOG_CHARS = {
    ord("\r"): None,  # carriage return
    ord("\n"): None,  # line feed
    0x0B: None,  # vertical tab
    0x0C: None,  # form feed
    0x1B: None,  # ESC (ANSI escape / terminal injection)
    0x85: None,  # NEL (next line)
    0x2028: None,  # line separator
    0x2029: None,  # paragraph separator
}


def safe_log(value: object) -> str:
    """Return ``value`` as a string with log-forging characters removed.

    Guards against log injection (CWE-117): user-controlled inputs — path
    params, request fields, URLs, and the text of exceptions raised from
    them — can smuggle newlines or terminal control sequences to forge or
    corrupt log records. Apply to every dynamic value (including exception
    objects) interpolated into a log message.
    """
    return str(value).translate(_UNSAFE_LOG_CHARS)
