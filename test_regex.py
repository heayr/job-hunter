import re

custom_stop_phrases = ["Откликаюсь на позицию"]
text = "Привет! Откликаюсь на позицию Senior Frontend."

cliches = []
for p in custom_stop_phrases:
    if len(p) > 2:
        cliches.append(r"(?i)" + re.escape(p))

for c in cliches:
    text = re.sub(c, "", text)

print(f"Result: '{text}'")
