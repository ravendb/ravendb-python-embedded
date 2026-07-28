"""Assert the installed .NET runtime matches what the bundled RavenDB server requires.

Reads the bundled server's runtimeconfig and checks that a matching Microsoft.NETCore.App
major runtime is installed. This turns the otherwise hidden server-to-.NET coupling (which
silently jumped from .NET 8 to .NET 10 between 7.1 and 7.2) into an enforced invariant, so CI
fails loudly instead of passing by luck on a preinstalled runtime.

Run after fetching the bundled server (`python setup.py sdist`):
    python scripts/check_dotnet_requirement.py
"""

import json
import subprocess
import sys
from pathlib import Path

RUNTIME_CONFIG = Path(
    "ravendb_embedded/target/nuget/contentFiles/any/any/RavenDBServer/Raven.Server.runtimeconfig.json"
)


def required_dotnet_major(runtime_config: Path) -> str:
    options = json.loads(runtime_config.read_text(encoding="utf-8"))["runtimeOptions"]
    frameworks = list(options.get("frameworks") or options.get("includedFrameworks") or [])
    if isinstance(options.get("framework"), dict):
        frameworks.insert(0, options["framework"])
    for framework in frameworks:
        if framework.get("name") == "Microsoft.NETCore.App" and framework.get("version"):
            return framework["version"].split(".")[0]
    return options.get("tfm", "").removeprefix("net").split(".")[0]  # e.g. "net10.0" -> "10"


def main() -> int:
    if not RUNTIME_CONFIG.exists():
        print(f"Server runtimeconfig not found at {RUNTIME_CONFIG}; fetch the server first (python setup.py sdist).")
        return 1

    major = required_dotnet_major(RUNTIME_CONFIG)
    if not major:
        print(f"Could not determine the required .NET version from {RUNTIME_CONFIG}.")
        return 1

    try:
        installed = subprocess.run(["dotnet", "--list-runtimes"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        print(f"No 'dotnet' found on PATH; the bundled server requires .NET major {major}.")
        return 1

    matched = f"Microsoft.NETCore.App {major}." in installed
    print(f"Bundled server requires .NET major {major}; matching runtime installed: {matched}")
    if not matched:
        print(f"Installed .NET runtimes do not include major {major}, which the bundled server requires.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
