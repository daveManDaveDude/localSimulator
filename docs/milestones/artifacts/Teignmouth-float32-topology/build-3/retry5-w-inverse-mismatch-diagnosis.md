# Retry-5 W inverse mismatch — exact byte diagnosis

2026-10-25. Read-only Sol diagnosis under disposition 106, SHA-256 `88335d7efd7065d7023e8d0852ef84ab9dc1a8286740417bec297744f2753fb2`. **Exact reconstruction is proven in memory; no source was repaired or written.** Retry-5 remains absent/unconsumed. This report grants no edit, implementation review PASS or invocation.

## Finding

The discrepancy is two unauthorized indentation changes at the two intended W path lines, not a uniform encoding/newline conversion. Current W line 23 has **eight** leading ASCII spaces where the accepted baseline has **four**; line 344 has **zero** where the accepted baseline has **four**. The net file length is unchanged. Reversing only retry-5 paths leaves those whitespace changes and therefore correctly fails the accepted inverse hash.

| Observation / in-memory result | SHA-256 |
| --- | --- |
| Actual unchanged W on disk | `26350581425f4853f25eeac3c05a14c32a94ab1f6e6589d5a5a67dcf3df497af` |
| Current W with only its two exact retry-5 parent literals reversed to retry-4 | `4f0c60e7cebca4048af5d67b409d41a416c91d60dc5c88db1db016800d139116` |
| Independently reconstructed accepted retry-4 W | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| Current inverse with only the two indentation differences corrected in memory | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| Current retry-5 W with only the same two indentation differences corrected in memory | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` |

Current W is 107257 bytes, UTF-8 without BOM, with 1728 bare LF and zero CRLF. Its on-disk hash was checked again after analysis and remained unchanged. A complete ordinal line comparison of the reconstructed baseline against the two-path inverse found **exactly two differing lines**, 23 and 344. No other content difference is required to reproduce the accepted baseline hash. No inference about semantic safety substitutes for this exact preservation proof.

## Git/object evidence and reconstruction

`git status --short -- <W>` reports `??`; `git ls-files --stage -- <W>` and `git log --all --oneline -- <W>` return no tracked entry/history. That does **not** establish absence of source in the object database. `git rev-list --objects --all` identifies available blob **`a742ddc1aea8cf05b8059879d83bcf8230b1f005`** with W's path. `git cat-file --batch-all-objects --batch-check` enumerated 2934 available objects, including this 107254-byte source blob and an older 107143-byte W blob `390dfbd027e07f9e5750ac98fb3eb3071db5e0c9`. The latter predates additional caller validation and is not the recovery basis. Read-only `git fsck --full --no-reflogs --unreachable` also reports historical dangling objects; no lost-found/write option was used. No configured objects/info/alternates file or GIT alternate/object-directory environment override was found.

The useful blob contains retry-1's two parent literals and unsuffixed access literals. Its text was read by `git cat-file blob`, reconstructed **only in memory** as UTF-8/no-BOM/LF with final LF, and validated against Git's own object framing: SHA-1 of `blob 107254` + NUL + reconstructed bytes equals **`a742ddc1aea8cf05b8059879d83bcf8230b1f005`** exactly. Thus native-output line capture/reconstruction did not silently alter these source bytes. Its raw-content SHA-256 is `c8fcd7c3d4ae8b1535f930533c838bd7e1818624c83798961b388f90660ccb74`.

Applying only these documented historical changes to that verified blob, in memory, reproduces the accepted retry-4 W SHA-256 **`6ed89a17…`** exactly:

1. Replace the two `.codex\build3-supervisor-selfcheck-retry-1` parent literals with `.codex\build3-supervisor-selfcheck-retry-4`.
2. Add `u` to the NUL CreateFile access literal `0x80000000` and to the stdout/stderr access literals `0x40000000` (three occurrences total), as specified by accepted `createfile-access-type-plan.md` and later reviews.

There is no guess about whether the resulting source is the accepted baseline: its full SHA-256 matches the recorded independently reviewed hash. The source object is an older W snapshot; the exact accepted baseline is **derived and verified**, not claimed to be a separately saved accepted-baseline file or a newly found Git commit. No candidate baseline was written. Earlier search finding no second W filename did not search decoded Git object content and therefore missed this available recovery basis.

The exact line forms after an eventual retry-5 correction would be:

```powershell
    'self-check' { Join-Path $root '.codex\build3-supervisor-selfcheck-retry-5' }
    $expectedRoot = Join-Path $root '.codex\build3-supervisor-selfcheck-retry-5'
```

Both have four leading U+0020 spaces. These are evidence of the minimal delta, not instructions released for execution. The report does not establish which editor/tool introduced the indentation; no authoritative patch transcript was available to assign cause. Successful AST/Ruff and reported 37/37 evidence checks cannot establish byte-preservation or cure the failed inverse. No new evidence check was run here.

## Current other sources and preservation

Rehashed actual current S/H/P:

| File | Current SHA-256 |
| --- | --- |
| S | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Disposition 106 records S/H's exact one-span inverses matching accepted baselines; this diagnosis does not edit/revert them. Retry-5 absence was observed with Test-Path; no root/record was created. Old evidence contents were not opened, rehashed or modified. All consumed roots remain immutable/non-PASS. Candidate stays NO-GO/unservable, build 3 unreserved. Outer exit1/internal2 and historical unsaved `957157…` S remain separate unresolved facts; recovering W proves nothing about that S history.

## Minimum next decision and acceptance

The preservation blocker is now localized with an exact recoverable baseline. Coordinator must explicitly release a bounded **W-only two-indentation-span recovery**, retaining both intended retry-5 literals and freezing every other W byte and S/H/P. Disposition 106 currently forbids repair; this diagnosis does not override that stop. There is no need to normalize whole-file encoding/line endings, rewrite W from an inferred template, revert S/H, select a new root, relax the inverse or adopt a new baseline.

Any separately released correction must produce W `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`, whose exact two retry-5 path inverses restore `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`. Require a full byte comparison to the in-memory verified reconstruction with retry-5 paths, counts 2/1/1, unchanged S/H/P, original plan's protected-evidence/static/path gates, independent non-implementing Sol review and a separate coordinator one-use gate before any invocation. Root must remain absent through correction/review. Stop on any differing byte, hash/count mismatch, unavailable object, changed source/evidence, unexpected alias or need for additional edits. No attempt is reserved or authorized here.

If the coordinator declines this proven two-span recovery, leave current bytes frozen and the issue stopped. No user decision to replace or weaken the accepted baseline is technically necessary given the exact match; authorization to make the narrow repair is still required. Do not treat a diagnosis or projected hash as a completed correction/review.

## Work log and limitations

Work used read-only Git metadata/object commands, source/document reads/searches and in-memory encoding/hash/string comparisons. LF/CRLF × BOM/no-BOM × final-newline variants of the two historical text objects were hashed; none alone matched the accepted baseline, as expected before historical path/type edits. The successful proof above also validates the selected blob reconstruction by its Git object ID.

Preliminary command issues: an rg Windows wildcard-path invocation was rejected and corrected to directory-plus-glob filtering; piping first-two-line Git previews caused downstream-closed-pipe `unable to stream` messages, resolved by full in-memory source reads; one in-memory analysis command had a PowerShell expression-spacing ParserError and was corrected before any computation. These were analysis-command errors, not wrapper/source parse or object-corruption findings. No W invocation, source parser/linter/compiler/test/import, operational script, runtime repro, process inspection/probe, old-evidence access, manifest/preflight/collection/GIS/numerical/build/browser action, source/checkpoint/disposition edit or candidate-baseline file occurred. Only this requested diagnosis artifact was written. Return its SHA-256 and stop for coordinator decision.
