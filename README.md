# Scaling GaN HEMTs beyond 1200V

This repository is a research + build + documentation workspace for exploring device, layout/termination, packaging, and test strategies for scaling GaN HEMTs beyond 1200 V.

## What this repo is for
- **Research**: literature notes, hypotheses, and design decisions with sources.
- **Build**: schematics/layout, fixtures, gate driver concepts, test plans.
- **Document**: lab notes, experiment logs, results, and postmortems.

## Suggested structure
- `docs/` – background notes, writeups, figures
- `lab-notes/` – dated logs (one file per day/week)
- `sim/` – TCAD/SPICE, field-plate/termination studies
- `hardware/` – schematics, PCB, mechanical
- `firmware/` – control, automation, data acquisition
- `data/` – raw + processed measurement data
- `scripts/` – analysis and plotting

## Safety / high-voltage note
Work above 1 kV can be lethal. Treat every build/test plan as needing a safety review (clearances/creepage, interlocks, PPE, one-hand rule, discharge procedures, isolation, instrumentation ratings).
