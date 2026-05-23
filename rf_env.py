from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

DEFAULT_ENV: Dict[str, Any] = {
    "tx_power_dbm": 30.0,
    "tx_gain_dbi": 15.0,
    "rx_gain_dbi": 15.0,
    "frequency_mhz": 2400.0,
    "distance_km": 1.0,
    "bandwidth_mhz": 20.0,
    "tx_loss_db": 2.0,
    "rx_loss_db": 2.0,
    "system_loss_db": 0.0,
    "noise_figure_db": 5.0,
    "required_snr_db": 10.0,
    "temperature_k": 290.0,
    "fading_margin_db": 10.0,
    "atmospheric_attenuation_db_per_km": 0.0,
    "ducting_gain_db": 0.0,
    "diffraction_loss_db": 0.0,
    "loop_area_m2": 1e-4,
    "loop_turns": 10,
    "reference_impedance_ohm": 50.0,
    "rx_sensitivity_dbm": -90.0,
}


@dataclass
class LinkBudgetEnvironment:
    tx_power_dbm: float = DEFAULT_ENV["tx_power_dbm"]
    tx_gain_dbi: float = DEFAULT_ENV["tx_gain_dbi"]
    rx_gain_dbi: float = DEFAULT_ENV["rx_gain_dbi"]
    frequency_mhz: float = DEFAULT_ENV["frequency_mhz"]
    distance_km: float = DEFAULT_ENV["distance_km"]
    bandwidth_mhz: float = DEFAULT_ENV["bandwidth_mhz"]
    tx_loss_db: float = DEFAULT_ENV["tx_loss_db"]
    rx_loss_db: float = DEFAULT_ENV["rx_loss_db"]
    system_loss_db: float = DEFAULT_ENV["system_loss_db"]
    noise_figure_db: float = DEFAULT_ENV["noise_figure_db"]
    required_snr_db: float = DEFAULT_ENV["required_snr_db"]
    temperature_k: float = DEFAULT_ENV["temperature_k"]
    fading_margin_db: float = DEFAULT_ENV["fading_margin_db"]
    atmospheric_attenuation_db_per_km: float = DEFAULT_ENV["atmospheric_attenuation_db_per_km"]
    ducting_gain_db: float = DEFAULT_ENV["ducting_gain_db"]
    diffraction_loss_db: float = DEFAULT_ENV["diffraction_loss_db"]
    loop_area_m2: float = DEFAULT_ENV["loop_area_m2"]
    loop_turns: int = DEFAULT_ENV["loop_turns"]
    reference_impedance_ohm: float = DEFAULT_ENV["reference_impedance_ohm"]
    rx_sensitivity_dbm: float = DEFAULT_ENV["rx_sensitivity_dbm"]

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "LinkBudgetEnvironment":
        values = {
            field.name: config.get(field.name, getattr(cls(), field.name))
            for field in cls.__dataclass_fields__.values()
        }
        return cls(**values)


def load_environment_from_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
