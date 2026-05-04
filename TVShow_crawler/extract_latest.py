import re
import json

with open('test_output.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all occurrences of "]["
splits = list(re.finditer(r'\]\[', content))
print(f"Found {len(splits)} array boundaries")

if splits:
    # Get the last split
    last_split = splits[-1].start()
    # Extract from after the last "]["
    latest = content[last_split+1:]  # Keep the [
    print(f"Extracting from position {last_split+1}")
    
    # Verify it's valid JSON
    try:
        data = json.loads(latest)
        print(f"Successfully parsed! {len(data)} items")
        if data:
            print(f"First show: {data[0]['showname']}")
            print(f"Last show: {data[-1]['showname']}")
        
        # Save the clean version
        with open('test_output.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)
        print("File cleaned and saved!")
    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")
        print(f"Last 200 chars: {latest[-200:]}")
