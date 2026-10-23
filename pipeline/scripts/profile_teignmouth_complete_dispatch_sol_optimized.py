"""One timing-only retained replay using the pinned cached supervisor.

Reuse the complete profiler's body, with separate write-once outputs. The
entrypoint and shared profiler are both explicit runtime-code pins.
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> int:
    source = Path(__file__).with_name("profile_teignmouth_complete_dispatch_sol.py")
    loaded = runpy.run_path(str(source))
    function = loaded["main"]
    namespace = function.__globals__
    evidence = namespace["EVIDENCE"]
    namespace["OUTPUT"] = evidence / "flip-05-complete-traced-profile-sol-optimized.json"
    namespace["REPORT_OUTPUT"] = evidence / "flip-05-complete-traced-report-sol-optimized.json"
    namespace["__file__"] = __file__
    return function()


if __name__ == "__main__":
    raise SystemExit(main())
