#!/usr/bin/env python3
"""RFPropSimMain.py

Entry point for the RF propagation simulator.
Dispatches to either the E-field or B-field model and reports pass/fail
according to required SNR criteria.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from rf_env import LinkBudgetEnvironment, DEFAULT_ENV, load_environment_from_json


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RF propagation simulator for first-order link-budget closure analysis"
    )
    parser.add_argument("--config", help="Optional JSON config file path for environment settings")
    parser.add_argument("--field-type", choices=["E", "B"], default="E", help="Field model type: E for electric field, B for magnetic field")
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


def format_results(env: LinkBudgetEnvironment, results: Dict[str, float], field_type: str) -> str:
    lines = ["RF Propagation Link Budget Analysis", "-------------------------------"]
    lines.append(f"Field type: {field_type}")
    for key, value in asdict(env).items():
        lines.append(f"{key.replace('_', ' ').title()}: {value}")
    lines.append("")
    lines.append(f"Free-space path loss: {results['fspl_db']} dB")
    lines.append(f"Effective path loss: {results['effective_path_loss_db']} dB")
    lines.append(f"Received power: {results['rx_power_dbm']} dBm")
    lines.append(f"Noise floor: {results['noise_floor_dbm']} dBm")
    lines.append(f"Noise floor with NF: {results['noise_floor_with_nf_dbm']} dBm")
    lines.append(f"Required SNR: {results['required_snr_db']} dB")
    if field_type == "E":
        lines.append(f"Electric field at receiver: {results['e_field_v_per_m']} V/m")
        lines.append(f"Achieved SNR: {results['snr_db']} dB")
        lines.append(f"SNR margin: {results['snr_margin_db']} dB")
        lines.append(f"Link margin over sensitivity: {results['link_margin_db']} dB")
    else:
        lines.append(f"Magnetic field at receiver: {results['b_actual_t']} T")
        lines.append(f"Magnetic noise sensitivity: {results['b_noise_t_per_sqrt_hz']} T/sqrt(Hz)")
        lines.append(f"Noise-equivalent field over bandwidth: {results['b_noise_total_t']} T")
        lines.append(f"Required field for SNR: {results['b_required_t']} T")
        lines.append(f"Magnetic SNR: {results['magnetic_snr_db']} dB")
        lines.append(f"SNR margin: {results['snr_margin_db']} dB")
    lines.append("")
    lines.append("Link closure: PASS" if results["pass"] else "Link closure: FAIL")
    if not results["pass"]:
        if field_type == "E":
            if results["snr_margin_db"] < 0:
                lines.append(f"  SNR deficit: {abs(results['snr_margin_db']):.2f} dB")
            if results["link_margin_db"] < 0:
                lines.append(f"  Sensitivity deficit: {abs(results['link_margin_db']):.2f} dB")
        else:
            if results["snr_margin_db"] < 0:
                lines.append(f"  Magnetic SNR deficit: {abs(results['snr_margin_db']):.2f} dB")
    return "\n".join(lines)


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()

    try:
        env = build_environment(args)
        if args.field_type == "B":
            import BfieldModel as field_model
        else:
            import EfieldModel as field_model
        results = field_model.compute_link_budget(env)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output_json:
        output = {"field_type": args.field_type, "environment": asdict(env), "results": results}
        print(json.dumps(output, indent=2))
    else:
        print(format_results(env, results, args.field_type))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
