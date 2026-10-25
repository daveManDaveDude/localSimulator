# Review 18 addendum — image-hash stability predicate

2026-10-25. Independent Sol reviewer `/root/sol_review_face_diag`, read-only follow-up to review 18. **Additional FIX_REQUIRED finding: changing image/path observations are not detected as partial.** This qualifies review 18's partial-image-observation assessment; the original close-order finding and overall FIX_REQUIRED disposition remain.

Rehashed actual reviewed S: `81fcdc0b199497d92d17c09c758a62b8861e7fcb7b41bb6a1c1663a1f76256af`, unchanged. Accepted plan `retry3-unexpected-member-evidence-plan.md` requires at line 59: “missing/unsafe/unreadable/changing image observations remain partial diagnostics.”

S **2410–2417** resolves the returned image path once, calls `_sha256(canonical_path, deadline)` and immediately records `imageSha256.status="observed"`. The shared `_sha256` at **806–813** opens the file, reads/hashes chunks and checks time; it performs **no before/after file metadata or file-identity comparison**. The new diagnostic path adds no such comparison, path re-resolution/revalidation or explicit stability-unknown status. Later process creation-time/Job-membership queries concern the same process handle; they do not establish stability of the on-disk file/path being hashed.

Consequently a detectable file-size/mtime/identity or path-target change during observation can still leave the digest marked simply observed and eligible for aggregate `status="observed"` at **2555–2573**. An exception raised by a failed read is handled as partial, but a mutation that does not raise is not. This is an unclosed plan predicate, not evidence that any image actually changed in a run and not a new demand for atomic load confinement or attestation of mapped executable bytes. No metadata check can prove absence of every hostile concurrent same-metadata replacement; that broader guarantee remains outside the accepted trust boundary.

The diagnostic must distinguish verified observable stability from changed/unavailable/unverified stability rather than infer stable image identity from a completed hash alone. Original census/rejection must stay unchanged and sticky BLOCKED; the shared hash helper need not be broadened merely to implement this diagnostic distinction. This addendum implements or authorizes no correction or operation.

Work was limited to static source/plan reads, searches and rehashing S, plus writing this addendum. No code/evidence/metadata was edited; no tests, imports, probes/process inspection, scripts/wrapper/self-check/preflight/runtime, manifests, GIS/numerical/build or browser action ran. Original review 18 remains at SHA-256 `9d4dfa9b32f141b3f5fd2d5775af7b4f8e2d12581b916d766b9fca92a947be7c` and was not rewritten.

No runtime evidence or self-check authorization follows. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**. Outer exit 1 versus recorded exit 2 and the unsaved `957157…` S-history limitation remain unresolved.
