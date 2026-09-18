import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
nb = json.load(open(os.path.join(ROOT, 'analysis', 'eda_shelly.ipynb')))
code_cells = [c['source'] for c in nb['cells'] if c['cell_type'] == 'code']
print('code cells:', len(code_cells))

def run_case(patch, label):
    ns = {}
    for i, src in enumerate(code_cells):
        exec(compile(src, '<cell %d>' % i, 'exec'), ns)
        if 'MAKE_REFERENCE' in src and 'INPUT =' in src:
            ns.update(patch)
    files = sorted(os.listdir(patch['OUTDIR']))
    print('[%s] outputs: %s' % (label, files))

run_case({'INPUT': 'ukdale', 'OUTDIR': '/tmp/nb_check_ukdale',
          'REFERENCE_PATH': None, 'MAKE_REFERENCE': True}, 'ukdale')
run_case({'INPUT': os.path.join(ROOT, 'repo', 'WattWiser', 'data', 'raw', 'synthetic_shelly_data.csv'), 'OUTDIR': '/tmp/nb_check_synthetic',
          'REFERENCE_PATH': os.path.join(ROOT, 'analysis', 'eda_reference_ukdale.json'), 'MAKE_REFERENCE': False}, 'synthetic')
print('BOTH CASES COMPLETED')
