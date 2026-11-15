import subprocess
import time
from pathlib import Path

ROOT = Path.cwd()
pptx = ROOT / "output" / "presentation" / "TerraLens_Presentation.pptx"
pdf = ROOT / "output" / "presentation" / "TerraLens_Presentation.pdf"

script = f'''
tell application "Keynote"
    activate
    set theDoc to open POSIX file "{pptx}"
    delay 1.5
    export theDoc to POSIX file "{pdf}" as PDF
    close theDoc saving no
    quit
end tell
'''
subprocess.run(["open", "-a", "Keynote"], check=True)
time.sleep(1.5)
res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
print("Returncode:", res.returncode)
print("Stdout:", res.stdout)
print("Stderr:", res.stderr)
