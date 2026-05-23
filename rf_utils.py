import math

from rf_env import LinkBudgetEnvironment


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
    return 20.0 * math.log10(4.0 * math.pi * distance_m / wavelength_m)


def thermal_noise_dbm_hz(temperature_k: float = 290.0) -> float:
    k_boltzmann = 1.380649e-23
    noise_watts_per_hz = k_boltzmann * temperature_k
    return watts_to_dbm(noise_watts_per_hz)


def noise_floor_dbm(bandwidth_mhz: float, temperature_k: float = 290.0) -> float:
    if bandwidth_mhz <= 0:
        raise ValueError("bandwidth_mhz must be positive")
    bandwidth_hz = bandwidth_mhz * 1_000_000.0
    return thermal_noise_dbm_hz(temperature_k) + 10.0 * math.log10(bandwidth_hz)


def atmospheric_attenuation_db(env: LinkBudgetEnvironment) -> float:
    return env.atmospheric_attenuation_db_per_km * env.distance_km


def effective_path_loss_db(env: LinkBudgetEnvironment, fspl_db: float) -> float:
    return (
        fspl_db
        + atmospheric_attenuation_db(env)
        + env.diffraction_loss_db
        + env.fading_margin_db
        - env.ducting_gain_db
    )


def plane_wave_e_field_from_tx(env: LinkBudgetEnvironment) -> float:
    power_watts = dbm_to_watts(env.tx_power_dbm)
    gain_linear = 10 ** (env.tx_gain_dbi / 10)
    distance_m = env.distance_km * 1_000.0
    power_density = power_watts * gain_linear / (4.0 * math.pi * distance_m**2)
    return math.sqrt(377.0 * power_density)


def plane_wave_b_field_from_tx(env: LinkBudgetEnvironment) -> float:
    e_field = plane_wave_e_field_from_tx(env)
    speed_of_light = 299_792_458.0
    return e_field / speed_of_light


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
