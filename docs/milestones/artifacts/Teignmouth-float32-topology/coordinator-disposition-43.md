# Coordinator disposition 43 — stop for startup trust-boundary decision

Date: 2026-10-24

**Decision: STOP for user boundary direction. Do not dispatch Luna cycle 2.** The user authorized iterative builds under disposition 40, but the accepted implementation plan explicitly kept the Python command/environment contract fixed and required stopping if startup/import closure needed a changed trust boundary. The bounded Sol diagnosis finds that constraint now blocks a defensible closure claim.

Diagnosis: build-3/supervisor-correction-3-diagnosis.md, SHA-256 cce878af32486a91b21168c82448ea805a3dcffadad7f4e1aa3ecde50830b9bb. The diagnosis identifies:

- Finding A has a bounded P-only correction: distinguish distribution-relative RECORD paths from package-tree ownership; safely normalize parent-relative Scripts entries; derive package/native/data anchors without requiring optional top_level.txt.
- Finding B cannot be universally closed by checking current path containment or hashing a finite initial directory. Startup hooks, import finders, native loading and dynamically selected sources can execute or extend search behavior before/after the checks. Hashes also do not guarantee atomic nonreplacement.

The user must choose one trust boundary before further implementation:

1. Accept a finite trusted startup/import profile: explicitly trust the approved CPython/OS loader and reviewed bootstrap/package code to follow a defined finite profile. The supervisor must bind every on-disk executable/cache/archive candidate in that profile and refuse all unmodelled startup, path or loader configurations. This does not claim to constrain malicious behavior by already trusted code or protect against concurrent replacement. Any run exceeding the existing 30-second deadline fails closed.
2. Authorize a separate Sol design for enforced import/native-load confinement, permitting changes to the fixed launch/environment or implementation boundary. No design or implementation is authorized until the user selects this direction.

No code, tests, runtime modes, self-check, diagnostic, GIS, numerical work or candidate build is authorized while this boundary is unresolved. Luna cycle 1 remains consumed (1/4); cycle 2 is not reserved. Candidate counters remain unchanged; candidate stays NO-GO, build 3 unreserved. The user's build-until-working authorization remains recorded, but it cannot answer this technical trust boundary by inference.
