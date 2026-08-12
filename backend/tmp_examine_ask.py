from pathlib import Path
text = Path('backend/app/routers/ask.py').read_text()
start = text.index('"candidates": [')
print(repr(text[start:start+250]))
