#!/usr/bin/env python3
"""
TCAD Deck Generator 
"""

import json
import os
from pathlib import Path
from jinja2 import Template

class GaNDeckGenerator:
    def __init__(self, template_file):
        with open(template_file, 'r') as f:
            self.template_content = f.read()
        self.template = Template(self.template_content)
    
    def generate_single_deck(self, variant, base_params, output_dir):
        config = {**base_params, **variant}
        
        # Extracted parameters
        lgd = float(config.get('Lgd', 15.0))
        substrate = config.get('substrate_material', 'sapphire').lower()
        
        # Format strings to prevent ".0" decimals from breaking regex parsers
        buf_val = float(config.get('buffer_thickness', 5.0))
        buf_thk_str = f"{int(buf_val)}" if buf_val.is_integer() else f"{buf_val}"
        
        sub_val = float(config.get('substrate_thickness', 50.0))
        sub_thk_str = f"{int(sub_val)}" if sub_val.is_integer() else f"{sub_val}"
        
        temp = int(config.get('temp', 300))
        gate_fp = config.get('gate_fp', False)
        source_fp = config.get('source_fp', False)
        
        # ── EXACT RTO NAMING CONVENTION ──
        fp_suffix = "_gate_source_FP" if (gate_fp and source_fp) else ""
        deck_name = f"A_GaN_Lgd{int(lgd)}_Buffer_{buf_thk_str}um_Substrate_{substrate}_{sub_thk_str}um{fp_suffix}"
        
        # Horizontal Geometry
        drain_start = float(config.get('Lg', 2.0)) + lgd
        drain_end = drain_start + float(config.get('drain_length', 1.0))
        
        # ── VERTICAL STACK MATHEMATICS ──
        buf_start = 0.025
        buf_end = buf_val
        
        # AlN Nucleation logic explicitly for Silicon
        has_aln = (substrate == 'silicon')
        if has_aln:
            aln_start = buf_end
            aln_end = buf_end + 0.1
            sub_start = aln_end
        else:
            aln_start = None
            aln_end = None
            sub_start = buf_end
            
        sub_end = sub_start + sub_val
        
        template_vars = {
            'deck_name': deck_name,
            'drain_start': drain_start,
            'drain_end': drain_end,
            'substrate_material': substrate,
            'temp': temp,
            'gate_fp': gate_fp,
            'source_fp': source_fp,
            'buf_end': buf_end,
            'has_aln': has_aln,
            'aln_start': aln_start,
            'aln_end': aln_end,
            'sub_start': sub_start,
            'sub_end': sub_end
        }
        
        deck_content = self.template.render(template_vars)
        
        output_filename = f"{deck_name}.in"
        output_path = Path(output_dir) / output_filename
        
        with open(output_path, 'w') as f:
            f.write(deck_content)
        
        return str(output_path)
    
    def batch_generate(self, config_file, output_dir='./generated_decks'):
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        base_params = config_data.get('base', {})
        variants = config_data.get('design_variants', [])
        
        os.makedirs(output_dir, exist_ok=True)
        
        generated_files = []
        for variant in variants:
            output_file = self.generate_single_deck(variant, base_params, output_dir)
            generated_files.append(output_file)
        
        return generated_files

def main():
    template_file = 'template_deck.in'
    config_file = 'gan_parameters.json'
    output_dir = './generated_decks'
    
    if not os.path.exists(template_file) or not os.path.exists(config_file):
        print("Required template or JSON configuration missing.")
        return
    
    generator = GaNDeckGenerator(template_file)
    files = generator.batch_generate(config_file, output_dir)
    print(f"Successfully generated {len(files)} TCAD decks.")

if __name__ == "__main__":
    main()