# Refactor RFPropSim into Modular E-Field / B-Field Propagation Framework
## Overview

This PR significantly refactors RFPropSim from a single-file first-order RF link budget calculator into a modular RF propagation analysis framework supporting both electric-field and magnetic-field propagation models.

The architecture has been separated into:

1. environment/configuration handling
2. propagation utilities
3. E-field link analysis
4. B-field sensitivity analysis
5. CLI orchestration

### Implements conventional far-field RF link-budget analysis using:

1. free-space path loss (FSPL)
2. atmospheric attenuation
3. diffraction loss
4. fading margin
5. ducting gain
6. receiver noise figure
7. SNR closure analysis

Outputs include:

1. received power
2. electric field strength
3. SNR margin
4. receiver sensitivity margin
5. pass/fail closure
6. BfieldModel.py

### Implements first-order magnetic-field-based detection analysis.

Features:

1. plane-wave magnetic field estimation
2. magnetic loop sensitivity estimation
3. thermal-noise-derived magnetic noise floor
4. magnetic SNR computation
5. magnetic-field-based link closure analysis

Outputs include:

1. magnetic field at receiver
2. magnetic sensitivity T/sqrt(Hz)
3. total noise-equivalent field
4. required field threshold
5. magnetic SNR
6. pass/fail closure

### Supports:

1. default configurations
2. JSON configuration loading
3. CLI overrides
4. environment variable overrides
5. Added Shared RF Utility Layer
6. rf_utils.py

Refactored shared RF math and propagation utilities into reusable functions:

dBm/Watt conversions
free-space path loss
thermal noise calculations
atmospheric attenuation
effective path loss
plane-wave E-field estimation
plane-wave B-field estimation
magnetic field sensitivity estimation
Refactored Main Entry Point
RFPropSimMain.py

Now acts as a lightweight orchestration layer:

builds simulation environment
selects E-field or B-field model
dispatches computation
formats output
handles JSON serialization

## Architectural Improvements

This PR transitions the repository from a procedural RF calculator toward a modular RF propagation and sensing analysis framework

Current magnetic-field modeling assumes:

far-field plane-wave propagation
plane-wave E/B relationship

The B-field model does not yet implement:

near-field inductive coupling
mutual inductance
reactive-field behavior
full-wave EM analysis

Additionally:

reported E/B field strengths currently do not include effective propagation losses in the field-domain calculation
closure is first-order only and intended for engineering estimation

## Example Usage
E-field analysis
python RFPropSimMain.py --field-type E

B-field analysis
python RFPropSimMain.py --field-type B

JSON output
python RFPropSimMain.py --field-type B --output-json
