# Sole Sol correction - telemetry cannot suppress cleanup

Status: submitted for independent re-review. Stage A remains stopped; complete
B/P admission is unavailable and live transaction caps remain. No cap-removal
readiness PASS, timing qualification or dependent dispatch is claimed.

Independent finding: an optional memory observation inside the guardian cleanup
try-block could raise before terminate/wait, or after exit before closing handles.
The correction moves cleanup into a dedicated routine: telemetry failures are
recorded separately; termination is attempted unconditionally; bounded exit wait
is attempted even after termination failure; only confirmed-empty trees are closed.
Unconfirmed exit/close failure retains ownership/handles and records failure.
The original absolute finalization deadline is passed unchanged to wait.

Files changed: assessment script, seven synthetic regression cases in its test
module, exact two extension hashes in transition config, handback/checkpoint and
correction evidence. No numerical/process lifecycle module or limits changed.
One pre-existing malformed checkpoint heading byte 0x97 was replaced with ASCII
hyphen after the marker-dependent test exposed invalid UTF-8. Its exact before-image
was saved before correction; no other encoding conversion was performed.

Final focused result: 122 passed, 1 native test deselected in 3.15 seconds
(3.566427600 seconds externally). Initial correction run: 121 passed, 1 failed,
1 deselected; failure was that checkpoint UTF-8 decoding. Full outputs, exact
commands and durations are retained in checks.json. Ruff check/format and diff
passed. Current pins/preservation are recorded in preservation.json.

No source-only assessment, native lifecycle test, standalone probe, profile,
solver, trial, candidate, receipt, permit or activation ran in this correction.
The original assessment records remain byte-identical and bind the initial script,
not a rerun of the corrected guardian. Existing native Job tests are reused only
for unchanged process module and unchanged native-test function; new cleanup
failure behavior is covered by seven synthetic regression cases.

Requested model/effort: gpt-6.1-sol / medium. Actual settings unknown. This is the
one completed Sol correction; zero remain, zero Luna corrections. Independent
reviewer remains separate. Next action is independent re-review only; if FIX
REQUIRED, stop with user decision, without any further correction or execution.
