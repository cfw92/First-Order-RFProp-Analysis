# First-Order-RFProp-Analysis

A modular first-order RF propagation and link-budget analysis framework for modeling real-world radio frequency environments.

RFPropSim provides configurable RF link-budget closure analysis with support for:

Free-space path loss (FSPL)
Atmospheric attenuation
Diffraction losses
Ducting gain approximation
Thermal noise modeling
Receiver noise figure
SNR and link margin analysis
Magnetic loop sensitivity estimation
CLI, JSON, and environment-variable configuration

This repository is intended as a flexible foundation for RF engineers, EW engineers, radar analysts, and communications researchers to rapidly prototype and evaluate RF system performance.

Features
Propagation Modeling
Friis free-space propagation
Atmospheric attenuation
Diffraction loss modeling
Ducting gain approximation
Effective path loss calculation
RF Link Budget Analysis
Received power estimation
Noise floor calculation
Noise density estimation
SNR analysis
Link closure determination
Receiver sensitivity margin analysis
Magnetic Field Sensitivity Estimation

Supports first-order magnetic loop receiver sensitivity estimation:

Loop antenna area
Number of turns
Noise-equivalent magnetic field estimation
T/
Hz
	​

 sensitivity output
Configuration Support

Supports:

Command-line configuration
JSON configuration files
Environment variable overrides
Output Modes
Human-readable engineering report
JSON output for automation pipelines
