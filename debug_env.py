import os

# Show ALL env vars that contain AZURE or OPENAI
for k, v in sorted(os.environ.items()):
    if 'AZURE' in k or 'OPENAI' in k or 'CHAT' in k:
        print(f"{k}={v}")
