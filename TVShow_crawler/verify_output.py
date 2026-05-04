import json

data = json.load(open('test_output.json'))
print(f'Total items: {len(data)}')

shows_with_seasons = [s for s in data if s.get('seasons')]
print(f'Shows with seasons data: {len(shows_with_seasons)}')

shows_with_episodes = [s for s in data if s.get('episodes')]
print(f'Shows with episodes data: {len(shows_with_episodes)}')

shows_with_both = [s for s in data if s.get('seasons') and s.get('episodes')]
print(f'Shows with both: {len(shows_with_both)}')

print(f'\nFirst 3 shows:')
for s in data[:3]:
    print(f"  - {s['showname']}: {s.get('seasons')} seasons, {s.get('episodes')} episodes")

print(f'\nLast 3 shows:')
for s in data[-3:]:
    print(f"  - {s['showname']}: {s.get('seasons')} seasons, {s.get('episodes')} episodes")
