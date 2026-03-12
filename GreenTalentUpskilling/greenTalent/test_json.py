import json

try:
    with open(r'c:\Users\GENAIMXCDMXUSR16\Pictures\Candiates_profiles.json', 'r') as f:
        data = json.load(f)
    print('✅ JSON file is valid')
    candidates = data.get('candidates', [])
    print(f'Total candidates: {len(candidates)}')
except json.JSONDecodeError as e:
    print(f'❌ JSON Error at line {e.lineno}, column {e.colno}: {e.msg}')
    # Print context
    with open(r'c:\Users\GENAIMXCDMXUSR16\Pictures\Candiates_profiles.json', 'r') as f:
        lines = f.readlines()
        if e.lineno > 0 and e.lineno <= len(lines):
            print(f'Line {e.lineno}: {lines[e.lineno-1][:100]}')
