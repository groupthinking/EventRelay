"""Safety contracts for the ordinary, offline pytest harness."""

import socket

import pytest


def test_cloud_metadata_hostname_is_not_resolved() -> None:
    """Coverage runs cannot discover ambient Google Cloud credentials."""

    with pytest.raises(RuntimeError, match="cloud instance metadata"):
        socket.getaddrinfo("metadata.google.internal", 80)


def test_cloud_metadata_ip_is_not_connected() -> None:
    """The link-local metadata endpoint is denied before any network I/O."""

    with socket.socket() as client:
        with pytest.raises(RuntimeError, match="cloud instance metadata"):
            client.connect(("169.254.169.254", 80))
