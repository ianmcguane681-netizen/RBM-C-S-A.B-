"""Hosted previews must bind outside container loopback and honour their assigned port."""
import pytest

from backend.__main__ import server_address


def test_server_defaults_are_reachable_from_a_container_preview():
    assert server_address({}) == ("0.0.0.0", 8000)


def test_server_uses_host_platform_port():
    assert server_address({"HOST": "127.0.0.1", "PORT": "4312"}) == ("127.0.0.1", 4312)


@pytest.mark.parametrize("port", ["words", "0", "65536"])
def test_server_refuses_an_invalid_port(port):
    with pytest.raises(SystemExit, match="PORT must"):
        server_address({"PORT": port})
