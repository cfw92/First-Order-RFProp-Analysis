#!/usr/bin/env python3
"""RFPropSimMain.py

A first-order radio frequency propagation simulator for link-budget closure.

Supports CLI configuration, JSON environment files, and standard RF budget output.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

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
        values = {field.name: config.get(field.name, getattr(cls(), field.name)) for field in dataclass_fields(cls)}
        return cls(**values)


def dataclass_fields(cls):
    return cls.__dataclass_fields__.values()  # type: ignore[return-value]


def dbm_to_watts(dbm: float) -> float:
    return 10 ** ((dbm - 30.0) / 10.0)


def watts_to_dbm(watts: float) -> float:
    return 10.0 * math.log10(watts) + 30.0


def free_space_path_loss_db(frequency_mhz: float, distance_km: float) -> float:
    if frequency_mhz <= 0 or distance_km <= 0:
        raise ValueError("frequency_mhz and distance_km must be positive values")
    distance_m = distance_km * 1_000.0
    frequency_hz = frequency_mhz * 1_000_000.0
    c = 299_792_458.0
    wavelength_m = c / frequency_hz
    fspl_db = 20.0 * math.log10(4.0 * math.pi * distance_m / wavelength_m)
    return fspl_db


def thermal_noise_dbm_hz(temperature_k: float = 290.0) -> float:
    k_boltzmann = 1.380649e-23
    noise_watts_per_hz = k_boltzmann * temperature_k
    return watts_to_dbm(noise_watts_per_hz)


def noise_floor_dbm(bandwidth_mhz: float, temperature_k: float = 290.0) -> float:
    if bandwidth_mhz <= 0:
        raise ValueError("bandwidth_mhz must be positive")
    bandwidth_hz = bandwidth_mhz * 1_000_000.0
    noise_density_dbm_hz = thermal_noise_dbm_hz(temperature_k)
    return noise_density_dbm_hz + 10.0 * math.log10(bandwidth_hz)


def atmospheric_attenuation_db(env: LinkBudgetEnvironment) -> float:
    return env.atmospheric_attenuation_db_per_km * env.distance_km


def effective_path_loss_db(env: LinkBudgetEnvironment, fspl_db: float) -> float:
    atmospheric_loss = atmospheric_attenuation_db(env)
    return fspl_db + atmospheric_loss + env.diffraction_loss_db + env.fading_margin_db - env.ducting_gain_db


def magnetic_field_sensitivity_t_per_sqrt_hz(
    noise_floor_dbm_value: float,
    bandwidth_mhz: float,
    frequency_mhz: float,
    loop_area_m2: float,
    loop_turns: int,
    reference_impedance_ohm: float = 50.0,
) -> float:
    if bandwidth_mhz <= 0:
        raise ValueError("bandwidth_mhz must be positive for sensitivity conversion")
    if loop_area_m2 <= 0 or loop_turns <= 0:
        raise ValueError("loop_area_m2 and loop_turns must be positive")

    bandwidth_hz = bandwidth_mhz * 1_000_000.0
    noise_density_dbm_hz = noise_floor_dbm_value - 10.0 * math.log10(bandwidth_hz)
    noise_watts_per_hz = 10 ** ((noise_density_dbm_hz - 30.0) / 10.0)
    voltage_density = math.sqrt(noise_watts_per_hz * reference_impedance_ohm)
    frequency_hz = frequency_mhz * 1_000_000.0
    omega = 2.0 * math.pi * frequency_hz
    return voltage_density / (loop_turns * loop_area_m2 * omega)


def compute_link_budget(env: LinkBudgetEnvironment) -> Dict[str, float]:
    fspl_db = free_space_path_loss_db(env.frequency_mhz, env.distance_km)
    effective_loss_db = effective_path_loss_db(env, fspl_db)
    rx_power_dbm = (
        env.tx_power_dbm
        + env.tx_gain_dbi
        - env.tx_loss_db
        - effective_loss_db
        + env.rx_gain_dbi
        - env.rx_loss_db
        - env.system_loss_db
    )

    noise_floor_dbm_value = noise_floor_dbm(env.bandwidth_mhz, env.temperature_k)
    noise_floor_with_nf_dbm = noise_floor_dbm_value + env.noise_figure_db
    snr_db = rx_power_dbm - noise_floor_with_nf_dbm
    link_margin_db = rx_power_dbm - env.rx_sensitivity_dbm
    closure_margin_db = snr_db - env.required_snr_db
    magnetic_sensitivity_t = magnetic_field_sensitivity_t_per_sqrt_hz(
        noise_floor_dbm_value,
        env.bandwidth_mhz,
        env.frequency_mhz,
        env.loop_area_m2,
        env.loop_turns,
        env.reference_impedance_ohm,
    )

    return {
        "fspl_db": round(fspl_db, 2),
        "atmospheric_loss_db": round(atmospheric_attenuation_db(env), 2),
        "diffraction_loss_db": round(env.diffraction_loss_db, 2),
        "ducting_gain_db": round(env.ducting_gain_db, 2),
        "effective_path_loss_db": round(effective_loss_db, 2),
        "rx_power_dbm": round(rx_power_dbm, 2),
        "noise_floor_dbm": round(noise_floor_dbm_value, 2),
        "noise_floor_with_nf_dbm": round(noise_floor_with_nf_dbm, 2),
        "noise_density_dbm_hz": round(noise_floor_dbm_value - 10.0 * math.log10(env.bandwidth_mhz * 1_000_000.0), 2),
        "snr_db": round(snr_db, 2),
        "required_snr_db": round(env.required_snr_db, 2),
        "snr_margin_db": round(closure_margin_db, 2),
        "link_margin_db": round(link_margin_db, 2),
        "rx_sensitivity_dbm": round(env.rx_sensitivity_dbm, 2),
        "fading_margin_db": round(env.fading_margin_db, 2),
        "magnetic_field_sensitivity_t_per_sqrt_hz": round(magnetic_sensitivity_t, 12),
    }


def load_environment_from_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_environment(args: argparse.Namespace) -> LinkBudgetEnvironment:
    config_values: Dict[str, Any] = {}
    config_file = args.config
    if config_file:
        config_values = load_environment_from_json(Path(config_file))

    env_dict = {**DEFAULT_ENV, **config_values}
    cli_overrides = {
        key: value
        for key, value in {
            "tx_power_dbm": args.tx_power_dbm,
            "tx_gain_dbi": args.tx_gain_dbi,
            "rx_gain_dbi": args.rx_gain_dbi,
            "frequency_mhz": args.frequency_mhz,
            "distance_km": args.distance_km,
            "bandwidth_mhz": args.bandwidth_mhz,
            "tx_loss_db": args.tx_loss_db,
            "rx_loss_db": args.rx_loss_db,
            "system_loss_db": args.system_loss_db,
            "noise_figure_db": args.noise_figure_db,
            "required_snr_db": args.required_snr_db,
            "temperature_k": args.temperature_k,
            "fading_margin_db": args.fading_margin_db,
            "atmospheric_attenuation_db_per_km": args.atmospheric_attenuation_db_per_km,
            "ducting_gain_db": args.ducting_gain_db,
            "diffraction_loss_db": args.diffraction_loss_db,
            "loop_area_m2": args.loop_area_m2,
            "loop_turns": args.loop_turns,
            "reference_impedance_ohm": args.reference_impedance_ohm,
            "rx_sensitivity_dbm": args.rx_sensitivity_dbm,
        }.items()
        if value is not None
    }
    env_dict.update(cli_overrides)

    for env_key, env_var_name in [
        ("tx_power_dbm", "RFPSIM_TX_POWER_DBM"),
        ("tx_gain_dbi", "RFPSIM_TX_GAIN_DBI"),
        ("rx_gain_dbi", "RFPSIM_RX_GAIN_DBI"),
        ("frequency_mhz", "RFPSIM_FREQUENCY_MHZ"),
        ("distance_km", "RFPSIM_DISTANCE_KM"),
        ("bandwidth_mhz", "RFPSIM_BANDWIDTH_MHZ"),
        ("tx_loss_db", "RFPSIM_TX_LOSS_DB"),
        ("rx_loss_db", "RFPSIM_RX_LOSS_DB"),
        ("system_loss_db", "RFPSIM_SYSTEM_LOSS_DB"),
        ("noise_figure_db", "RFPSIM_NOISE_FIGURE_DB"),
        ("required_snr_db", "RFPSIM_REQUIRED_SNR_DB"),
        ("temperature_k", "RFPSIM_TEMPERATURE_K"),
        ("fading_margin_db", "RFPSIM_FADING_MARGIN_DB"),
        ("atmospheric_attenuation_db_per_km", "RFPSIM_ATMOSPHERIC_ATTENUATION_DB_PER_KM"),
        ("ducting_gain_db", "RFPSIM_DUCTING_GAIN_DB"),
        ("diffraction_loss_db", "RFPSIM_DIFFRACTION_LOSS_DB"),
        ("loop_area_m2", "RFPSIM_LOOP_AREA_M2"),
        ("loop_turns", "RFPSIM_LOOP_TURNS"),
        ("reference_impedance_ohm", "RFPSIM_REFERENCE_IMPEDANCE_OHM"),
        ("rx_sensitivity_dbm", "RFPSIM_RX_SENSITIVITY_DBM"),
    ]:
        env_value = os.environ.get(env_var_name)
        if env_value is not None:
            try:
                env_dict[env_key] = float(env_value)
            except ValueError:
                raise ValueError(f"Invalid numeric environment variable {env_var_name}: {env_value}")

    return LinkBudgetEnvironment.from_dict(env_dict)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RF propagation simulator for first-order link-budget closure analysis"
    )
    parser.add_argument("--config", help="Optional JSON config file path for environment settings")
    parser.add_argument("--tx-power-dbm", type=float, help="Transmit power in dBm")
    parser.add_argument("--tx-gain-dbi", type=float, help="Transmit antenna gain in dBi")
    parser.add_argument("--rx-gain-dbi", type=float, help="Receive antenna gain in dBi")
    parser.add_argument("--frequency-mhz", type=float, help="Carrier frequency in MHz")
    parser.add_argument("--distance-km", type=float, help="Link distance in kilometers")
    parser.add_argument("--bandwidth-mhz", type=float, help="RF bandwidth in MHz")
    parser.add_argument("--tx-loss-db", type=float, help="TX feedline / connector loss in dB")
    parser.add_argument("--rx-loss-db", type=float, help="RX feedline / connector loss in dB")
    parser.add_argument("--system-loss-db", type=float, help="Additional system margin or loss in dB")
    parser.add_argument("--noise-figure-db", type=float, help="Receiver noise figure in dB")
    parser.add_argument("--required-snr-db", type=float, help="Required SNR for the target modulation / coding")
    parser.add_argument("--temperature-k", type=float, help="System noise temperature in Kelvin")
    parser.add_argument("--fading-margin-db", type=float, help="Fading margin to reserve in dB")
    parser.add_argument("--atmospheric-attenuation-db-per-km", type=float, help="Atmospheric attenuation in dB per km")
    parser.add_argument("--ducting-gain-db", type=float, help="Ducting gain (positive value reduces path loss)")
    parser.add_argument("--diffraction-loss-db", type=float, help="Additional diffraction loss in dB")
    parser.add_argument("--loop-area-m2", type=float, help="Loop antenna area in square meters for magnetic field sensitivity")
    parser.add_argument("--loop-turns", type=int, help="Loop antenna turns for magnetic field sensitivity")
    parser.add_argument("--reference-impedance-ohm", type=float, help="Receiver reference impedance for sensitivity conversion")
    parser.add_argument("--rx-sensitivity-dbm", type=float, help="Receiver sensitivity in dBm")
    parser.add_argument("--output-json", action="store_true", help="Print results in JSON format")
    return parser


def format_results(env: LinkBudgetEnvironment, results: Dict[str, float]) -> str:
    lines = ["RF Propagation Link Budget Analysis", "-------------------------------"]
    for key, value in asdict(env).items():
        lines.append(f"{key.replace('_', ' ').title()}: {value}")
    lines.append("")
    lines.append(f"Free-space path loss: {results['fspl_db']} dB")
    lines.append(f"Received power: {results['rx_power_dbm']} dBm")
    lines.append(f"Atmospheric attenuation: {results['atmospheric_loss_db']} dB")
    lines.append(f"Diffraction loss: {results['diffraction_loss_db']} dB")
    lines.append(f"Ducting gain: {results['ducting_gain_db']} dB")
    lines.append(f"Effective path loss: {results['effective_path_loss_db']} dB")
    lines.append(f"Noise floor: {results['noise_floor_dbm']} dBm")
    lines.append(f"Noise density: {results['noise_density_dbm_hz']} dBm/Hz")
    lines.append(f"Noise floor with NF: {results['noise_floor_with_nf_dbm']} dBm")
    lines.append(f"Achieved SNR: {results['snr_db']} dB")
    lines.append(f"Required SNR: {results['required_snr_db']} dB")
    lines.append(f"SNR margin: {results['snr_margin_db']} dB")
    lines.append(f"Link margin over sensitivity: {results['link_margin_db']} dB")
    lines.append(f"Fading margin reserved: {results['fading_margin_db']} dB")
    lines.append(f"Magnetic sensitivity: {results['magnetic_field_sensitivity_t_per_sqrt_hz']} T/sqrt(Hz)")
    lines.append("")
    if results["snr_margin_db"] >= 0 and results["link_margin_db"] >= 0:
        lines.append("Link closure: PASS")
    else:
        lines.append("Link closure: FAIL")
    if results["snr_margin_db"] < 0:
        lines.append(f"  SNR deficit: {abs(results['snr_margin_db']):.2f} dB")
    if results["link_margin_db"] < 0:
        lines.append(f"  Sensitivity deficit: {abs(results['link_margin_db']):.2f} dB")
    return "\n".join(lines)


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    try:
        env = build_environment(args)
        results = compute_link_budget(env)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output_json:
        output = {"environment": asdict(env), "results": results}
        print(json.dumps(output, indent=2))
    else:
        print(format_results(env, results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
