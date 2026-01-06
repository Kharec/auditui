from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


try:
    import audible  # noqa: F401
except ModuleNotFoundError:
    audible_stub = ModuleType("audible")

    class Authenticator:  # minimal stub for type usage
        pass

    class Client:  # minimal stub for type usage
        pass

    audible_stub.Authenticator = Authenticator
    audible_stub.Client = Client

    activation_bytes = ModuleType("audible.activation_bytes")

    def get_activation_bytes(_auth: Authenticator | None = None) -> bytes:
        return b""

    activation_bytes.get_activation_bytes = get_activation_bytes

    sys.modules["audible"] = audible_stub
    sys.modules["audible.activation_bytes"] = activation_bytes
