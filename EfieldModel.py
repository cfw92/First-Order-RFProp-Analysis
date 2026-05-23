from typing import Dict

from rf_env import LinkBudgetEnvironment
from rf_utils import (
    effective_path_loss_db,
    free_space_path_loss_db,
    noise_floor_dbm,
    plane_wave_e_field_from_tx,
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
    snr_db = rx_power_dbm - noise_floor_with_nf
    link_margin_db = rx_power_dbm - env.rx_sensitivity_dbm
    closure_margin_db = snr_db - env.required_snr_db
    e_field_v_per_m = plane_wave_e_field_from_tx(env)

    return {
        "model": "E-field",
        "fspl_db": round(fspl_db, 2),
        "atmospheric_loss_db": round(env.atmospheric_attenuation_db_per_km * env.distance_km, 2),
        "diffraction_loss_db": round(env.diffraction_loss_db, 2),
        "ducting_gain_db": round(env.ducting_gain_db, 2),
        "effective_path_loss_db": round(effective_loss_db, 2),
        "rx_power_dbm": round(rx_power_dbm, 2),
        "e_field_v_per_m": round(e_field_v_per_m, 6),
        "noise_floor_dbm": round(noise_floor, 2),
        "noise_floor_with_nf_dbm": round(noise_floor_with_nf, 2),
        "snr_db": round(snr_db, 2),
        "required_snr_db": round(env.required_snr_db, 2),
        "snr_margin_db": round(closure_margin_db, 2),
        "link_margin_db": round(link_margin_db, 2),
        "rx_sensitivity_dbm": round(env.rx_sensitivity_dbm, 2),
        "pass": closure_margin_db >= 0 and link_margin_db >= 0,
    }
