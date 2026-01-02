from __future__ import annotations

"""
Default TCP server configuration for the simulator transport layer.

This module defines the host/port used by the simulator TCP publisher server.
These values are imported by the TCP server implementation and can be overridden
by passing explicit arguments when constructing the server.

Attributes
----------
HOST
    Default bind address for the simulator TCP server.
PORT
    Default TCP port for the simulator TCP server.
"""

HOST: str = "127.0.0.1"
PORT: int = 9009
