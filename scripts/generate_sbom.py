"""Generate an SPDX-like JSON inventory from pinned Python dependencies.

This is a release inventory, not a substitute for a container scanner. The
release pipeline should retain both this artifact and the container scan.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REQ = Path("requirements.txt")
OUT = Path("sbom.spdx.json")

items = []
for line in REQ.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^\s]+)$", line)
    if match:
        items.append({"name": match.group(1), "version": match.group(2)})

sbom = {
    "spdxVersion": "SPDX-2.3",
    "SPDXID": "SPDXRef-DOCUMENT",
    "name": "EOS-Dynamic-Business-Platform",
    "documentNamespace": "https://eos-dbp.com/sbom",
    "creationInfo": {"createdBy": ["Tool: scripts/generate_sbom.py"]},
    "packages": [
        {"SPDXID": f"SPDXRef-Package-{i}", "name": p["name"], "versionInfo": p["version"], "downloadLocation": "NOASSERTION"}
        for i, p in enumerate(items, 1)
    ],
}
OUT.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Generated {OUT} with {len(items)} pinned Python packages")
