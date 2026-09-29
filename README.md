# Scaling GaN HEMTs beyond 1200 V

This repository contains a TCAD-driven design study for scaling lateral GaN HEMTs beyond 1200 V. The work focuses on how lateral geometry, buffer engineering, substrate choice, and field-plate structures change the key trade-offs in GaN power-device performance.

The project is organized around a repeatable simulation workflow: generate device decks, run TCAD studies, extract electrical metrics from log files, and visualize the resulting breakdown voltage, on-resistance, capacitance, and figure-of-merit trends.

## Research objective

The main question is how to push GaN HEMTs to higher blocking capability without losing the low-loss performance required for high-frequency power conversion. The analysis in this repo compares device variants across:

- Gate-to-drain spacing (Lgd): 10, 15, and 20 µm
- Buffer thickness: 0.5 µm and 5.0 µm
- Substrate material: sapphire and silicon
- Substrate thickness: 5 µm, 50 µm, and 500 µm
- Field-plate layout: standard and gate-source field plate variants

## Repository structure

- `Deck Generator/`  
  TCAD deck generation utilities and parameter files for creating device variants.
  - `GaN_deck_Generator.py` generates the `.in` decks
  - `gan_parameters.json` stores the device parameter set
  - `template_deck.in` is the base TCAD template
  - `generated_decks/` contains example generated decks

- `Breakdown Voltage/`  
  Breakdown-voltage extraction and plotting workflow.
  - `Vbr_Analysis.py` parses the simulation logs and produces breakdown plots
  - `Results/` contains the generated voltage-scaling figures
  - `logs/` holds the raw TCAD log files used for analysis

- `Capacitance/`  
  Capacitance and switching-energy analysis.
  - `compare_cap_energy.py` builds comparative capacitance and energy plots
  - `Results/` contains plots and summary CSV data
  - `logs/` contains the capacitance simulation logs

- `On-Resistance/`  
  Linear-region extraction and comparison of Rds,on versus geometry.
  - `compare_ron_lgd.py` estimates on-resistance from the I-V trace
  - `Results/` stores the extracted comparison plots
  - `logs/` holds the drain-current logs used for extraction

- `FOM/`  
  Combined figure-of-merit analysis for power-device performance.
  - `FOM_comparison.py` computes a combined high-frequency FOM using breakdown voltage, capacitance, and on-resistance
  - `Results/` includes the ranked table and power plot
  - `logs/` contains all supporting input logs

- `Documents/`  
  Research presentation and thesis materials.
  - `Presentation.pptx`
  - `ResearchProjectThesis - VaibhavBalotra.pdf`

## Typical workflow

1. Generate device decks with the deck generator.
2. Run the generated TCAD decks for the selected device and material combinations.
3. Save the simulation outputs in the relevant `logs/` folders.
4. Run the analysis script in each study area to process the logs.
5. Inspect the generated plots under each `Results/` directory.

Example operations:

```bash
cd "Deck Generator"
python GaN_deck_Generator.py

cd ../Breakdown\ Voltage
python Vbr_Analysis.py

cd ../Capacitance
python compare_cap_energy.py

cd ../On-Resistance
python compare_ron_lgd.py

cd ../FOM
python FOM_comparison.py
```

## Interpretation of the study

The repo evaluates how the design space changes the device trade-offs:

- Higher Lgd tends to improve blocking capability but can increase total device footprint and resistance behavior.
- Thinner and more favorable substrates can shift electric-field distribution and impact breakdown strength.
- Buffer thickness has a visible effect on field support, charge distribution, and switching performance.
- The FOM analysis provides a compact way to compare competing design choices for high-frequency power operation.

## Expected outputs

Each study directory contains figures and extracted metrics, including:

- Breakdown voltage trends versus Lgd and substrate conditions
- Capacitance versus substrate and dielectric scaling
- On-resistance trends across GaN lateral geometries
- Ranked FOM table and high-frequency performance plot

## Notes

This is a research repository built around device simulation and analysis, not a turnkey manufacturing or PCB design package. The material and plotting pipeline is intended to support exploration, comparison, and documentation of GaN HEMT scaling strategies.

## License

No explicit license file is present in the repository at this time. If you plan to reuse or redistribute this work, confirm the appropriate licensing terms before sharing or publishing it.
