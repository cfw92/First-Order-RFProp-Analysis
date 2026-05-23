import math
from typing import Dict

from rf_env import LinkBudgetEnvironment
from rf_utils import (
    effective_path_loss_db,
    free_space_path_loss_db,
    magnetic_field_sensitivity_t_per_sqrt_hz,
    noise_floor_dbm,
    plane_wave_b_field_from_tx,
)


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

    noise_floor = noise_floor_dbm(env.bandwidth_mhz, env.temperature_k)
    noise_floor_with_nf = noise_floor + env.noise_figure_db
    b_actual_t = plane_wave_b_field_from_tx(env)
    b_sensitivity_t = magnetic_field_sensitivity_t_per_sqrt_hz(
        noise_floor,
        env.bandwidth_mhz,
        env.frequency_mhz,
        env.loop_area_m2,
        env.loop_turns,
        env.reference_impedance_ohm,
    )
    b_noise_total_t = b_sensitivity_t * math.sqrt(env.bandwidth_mhz * 1_000_000.0)
    b_required_t = b_noise_total_t * 10 ** (env.required_snr_db / 20.0)
    if b_actual_t > 0:
        magnetic_snr_db = 20.0 * math.log10(b_actual_t / b_noise_total_t)
    else:
        magnetic_snr_db = float("-inf")
    closure_margin_db = magnetic_snr_db - env.required_snr_db

    return {
        "model": "B-field",
        "fspl_db": round(fspl_db, 2),
        "atmospheric_loss_db": round(env.atmospheric_attenuation_db_per_km * env.distance_km, 2),
        "diffraction_loss_db": round(env.diffraction_loss_db, 2),
        "ducting_gain_db": round(env.ducting_gain_db, 2),
        "effective_path_loss_db": round(effective_loss_db, 2),
        "rx_power_dbm": round(rx_power_dbm, 2),
        "noise_floor_dbm": round(noise_floor, 2),
        "noise_floor_with_nf_dbm": round(noise_floor_with_nf, 2),
        "b_actual_t": round(b_actual_t, 12),
        "b_noise_t_per_sqrt_hz": round(b_sensitivity_t, 12),
        "b_noise_total_t": round(b_noise_total_t, 12),
        "b_required_t": round(b_required_t, 12),
        "magnetic_snr_db": round(magnetic_snr_db, 2) if math.isfinite(magnetic_snr_db) else magnetic_snr_db,
        "required_snr_db": round(env.required_snr_db, 2),
        "snr_margin_db": round(closure_margin_db, 2) if math.isfinite(closure_margin_db) else closure_margin_db,
        "pass": closure_margin_db >= 0,
    }
