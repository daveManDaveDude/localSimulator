# Teignmouth bootstrap memory amendment

24 October 2026. User-directed material scope change. Requested implementation
role gpt-6.1-sol / medium; actual runtime model/effort unknown.

## Authority and implementation boundary

The user explicitly authorized removal of the fixed 64 MiB construction/transfer
acceptance cap. The reviewed plan also replaces the fixed 16 MiB envelope cap
with request-specific typed bounds. The approved bootstrap proposal (SHA-256
`63cc4ca3a01906b71514d10590da4692399e91aa4e8ecefbc955cad627f2640f`)
and its original approval remain unchanged historical records. This amendment
supersedes their construction/transport cap provisions only, conditional on
safe admission. It does not authorize dropping allocation accounting.

Implementation is staged: assessment containment and typed admission first;
transaction integration only if a defensible complete full-tree ledger exists.
The existing live transaction caps remain during this first stage. Their continued
presence is an incomplete integration, not a claim that cap removal is ready.
An incomplete ledger must reject execution without a permit or trial.

## Two admissions

Assessment: freshly read `GlobalMemoryStatusEx` available physical bytes and
`ullAvailPageFile` (current-process commit availability, not system-wide free
commit or virtual address space). Set L0=floor(min(values)/2); round the effective
Job limit DOWN to a 4096-byte page boundary. This reserves half the observed
availability by policy; it does not reserve memory in Windows. The assessment
does not require P in advance. Its outer deadline is 30 seconds, including cleanup;
work cutoff is 25 seconds to leave cleanup time. Allocation failures fail closed.

Execution: B is inclusive supervisor+worker commit after imports and before source
materialization; P is additional simultaneous full-tree allocation above B;
H=max(B,ceil(P/2)) is disclosed contingency, not a proof. Requery availability,
calculate Lavailable=floor(min(values)/2), and admit only if
Lrequired=B+P+H <= Lavailable. Native limits must respect page granularity without
exceeding available allowance. No automatic increase or retry is allowed.

P must include both processes' source/raw/text/JSON graphs, Python/native/GEOS and
import allocation, arrays/indexes, transport, results, assets and finalization.
Existing buffer bounds do not bound RSS. Missing justified components reject;
observed current/peak committed memory supplements but does not prove bounds.
The exact future request cannot be known before its actual topology/constraints
exist; source-only bounds must never be relabelled as complete request bounds.

## Containment and evidence

An outer guardian creates the assessment supervisor suspended, assigns it to a
Job before resume, and queries limit and membership. Breakaway is disabled;
kill-on-close and aggregate Job commit limit are mandatory. The Job limit prevents
further commits; it does NOT automatically terminate the tree. Allocation failure,
abnormal completion or timeout requires explicit termination, confirmed whole-tree
exit and bounded cleanup; unconfirmed ownership stays tracked.

New authorized native pytest coverage checks outer/nested membership, denied
above-limit VirtualAlloc commit, queried settings and explicit complete cleanup.
This is not a standalone probe. Historical probe bytes/results remain unchanged
but cannot validate this amended lifecycle implementation.

The single authorized assessment loads exact hash-bound full sources and computes
the complete ReleaseInputs bound without the former 64 MiB early exit. No request
encoding, topology, solver, trial, worker transport, profile or candidate is allowed.
Its durable record includes commands, hashes, fresh availability, actual process
baseline/peak and Job high water, full source bound and explicit missing ledger parts.
Failure or incomplete execution admission stops Stage A before integration.

## Preserved scope, gates and budget

All twelve gates, numerical/geographic/source constraints and every other resource
limit remain unchanged: 8 MiB assets, 256 KiB manifest, 512 KiB QA, 16 MiB resident
geometry, 250000 triangles, 150000 vertices, four added draws. Preserve 2000 solver
iterations, 120/125/135-second deadlines and both <=125-second projections; all
sources/features, pending AOI/TQ1 4HN, synthetic/default/preview remain unchanged.
No frozen numerical runner or patch module is edited in the assessment stage.

The current initial Sol Stage A submission continues; zero corrections used,
at most one Sol correction, zero Luna corrections. Independent reviewer remains
separate. No old issue budget resets. No receipt, permit, collar-05 dispatch,
profile, candidate, activation, browser, publication or commit in this submission.
Only independent readiness PASS plus genuine exact receipts/coordinator permit
could unlock the previously authorized single write-once collar-05; profiles remain
conditional on its complete success. Ordinary production timing stays unqualified.

Exact before-images: `.codex/history/2026-10-24-unicode-timing/cap-amendment-before/`.
Final assessment/checks/hash-transition evidence is under the bootstrap artifact
directory. Changed extension pins are an explicit metadata transition for this
amendment; historical receipt/evidence identities are never silently re-signed.
