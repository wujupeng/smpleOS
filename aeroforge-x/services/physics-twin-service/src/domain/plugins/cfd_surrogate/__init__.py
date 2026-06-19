"""AeroForge-X v5.0 CFD Surrogate Model Architecture Package"""

from .interfaces import ISurrogateModelArchitecture
from .pinn_architecture import PINNArchitecture, PINNModel
from .deeponet_architecture import DeepONetArchitecture, DeepONetModel
from .transformer_architecture import TransformerArchitecture, TransformerModel

__all__ = [
    "ISurrogateModelArchitecture",
    "PINNArchitecture",
    "PINNModel",
    "DeepONetArchitecture",
    "DeepONetModel",
    "TransformerArchitecture",
    "TransformerModel",
]