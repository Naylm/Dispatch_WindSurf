import os

def clean_quill_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove header
    if '---' in content:
        actual_content = content.split('---', 1)[1].strip()
    else:
        actual_content = content
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(actual_content)

# Paths
base_path = r'C:\Users\nayso\.gemini\antigravity\brain\d461d519-126b-46d5-b51f-92e34d871ea9\.system_generated\steps'
js_input = os.path.join(base_path, '1470', 'content.md')
css_input = os.path.join(base_path, '1473', 'content.md')

js_output = r'c:\Users\nayso\Desktop\dispatch_antigravity\DispatchFresh\app\static\vendor\quill\quill.min.js'
css_output = r'c:\Users\nayso\Desktop\dispatch_antigravity\DispatchFresh\app\static\vendor\quill\quill.snow.css'

try:
    clean_quill_file(js_input, js_output)
    clean_quill_file(css_input, css_output)
    print("Files cleaned and saved successfully.")
except Exception as e:
    print(f"Error: {e}")
