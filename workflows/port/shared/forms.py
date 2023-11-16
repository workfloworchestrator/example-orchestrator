from orchestrator.forms.validators import Choice

from products.product_blocks.port import PortMode


def port_mode_selector() -> list:
    port_modes = [port_mode.value for port_mode in PortMode]
    return Choice("PortModesEnum", zip(port_modes, port_modes))  # type: ignore
