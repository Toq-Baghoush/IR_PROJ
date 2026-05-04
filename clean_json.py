import json

with open('test_output.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the last occurrence of "][" to locate the latest run
pos = content.rfind('][')
if pos != -1:
    # Extract from the second array (after "][")
    latest = content[pos+1:]  # Skip the first "]"
else:
    # No duplicate found, use everything
    latest = content

# Ensure it's valid JSON
if not latest.endswith(']'):
    latest += ']'

# Verify it's valid
try:
    data = json.loads(latest)
    print(f"Successfully parsed latest run with {len(data)} items")
    print(f"First show: {data[0]['showname']}")
    print(f"Last show: {data[-1]['showname']}")
    
    # Save the clean version (with no indentation for compact format)
    with open('test_output.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
    print("File cleaned and saved!")
except json.JSONDecodeError as e:
    print(f"Error: {e}")
