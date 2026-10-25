# Coordinator disposition 89 — retry-4 failure reconciliation and diagnosis

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User authorized as many attempts as needed to get the bounded self-check working. This preserves every prior counter and requires serial diagnosis, implementation, independent Sol review and a fresh one-use coordinator gate for each further self-check.

## Retry-4 result

Disposition 88's single W wrapper invocation was executed once. Retry-4 is consumed, immutable and **non-PASS**; it must not be replayed. The outer `pwsh` returned 1 with no console output; the wrapper evidence records its supervisor/native launcher/chosen exit code as 2 and `BLOCKED_SELFCHECK`. `run-1/invocation.json` records `post-wait inner Job snapshot contains an unexpected process`, elapsed approximately 1.3183 seconds. The known normal helper launcher/interpreter exits were both 7. No timeout, tree probe, candidate build, GIS work or runtime collection occurred.

## Bounded observation

The complete post-wait census reports accounting `1/1`, a complete census, and one unexpected PID `33552`. The bounded follow-up against the retained handle recorded image path `C:\Windows\System32\conhost.exe`, SHA-256 `c86146188b78e484f32cc29e2331689659943b47689a85570342044f499938ac`; Job membership true before and after the detail reads; one unchanged process creation time; zero-time wait `WAIT_TIMEOUT`; raw exit value 0; and a changed nonzero exit time on the later query. The same-path metadata tuple matched before hash, after hash, and after path resolution; the image handle was released.

These are later handle observations, not a proven PID-to-handle association at the census instant (`censusIdentityAssociation` is `unproven`). The changing wait/exit observations are consistent with a short-lived process transition during detail collection, but do not establish why it belonged to the Job, whether it is a normal console-host descendant, or whether ignoring it is safe. The unexpected-member rejection remains valid. A later zero-count checkpoint cannot retroactively pass the earlier nonzero census.

## Immutable retry-4 evidence hashes

| Evidence | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `127af0f90b23a5048e72eedf992080016491a3a9590f694ea63d15f3dd244fe9` |
| `self-check-handoff.consumed.json` | `842925a205014286e6d9a5b5cf1822cfe6f41499f4b0bf3a63c5d9831264631d` |
| `supervisor-script-start.json` | `72f9f46afadbd1199b5bffb091ed9dba06a23297c194f6de985f07a27e0d306d` |
| `supervisor.stderr.log` | `18d4873d35189bf11f26f2df45a60574330fde3c27bf02371542b37a4b46fea8` |
| `supervisor.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run-1/invocation.json` | `db81b0941a113733e5661005c5e1f99f89431a36701f5ae7a8b90acc95b720f4` |
| `run-1/nonzero-authorization.consumed.json` | `ca6e9da7f0bc10e4b49160c1d66ceba3fad31097e38548cbc3d0671179ea7627` |
| `run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | `fc551dde8e2be7b93238561092d28e538402b7265e77d1fb2e7ebe6a32957ec2` |
| `run-1/nonzero.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run-1/nonzero.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Next gate

The Sol planner/diagnostician is assigned a read-only diagnosis using only the immutable retry-4 evidence and static source. It must identify what is proven versus unproven, explain the repeated unexpected-member observation, and propose a minimal bounded correction or evidence requirement without relaxing rejection or checking live processes. No code edit or self-check is authorized by this disposition. After its diagnosis, the coordinator will decide the next narrow implementation/review step under the user's continuing authorization. Every self-check needs a new unique root, accepted independent review and fresh coordinator gate; keep the 10-second total QPC deadline and preserve all consumed roots.

## Preserved status

Candidate remains **NO-GO and unservable**; build 3 remains unreserved. No GIS/numerical/candidate build, serving/publication, browser action, commit, push or merge. The outer exit discrepancy and the historical untraceable `957157…` digest remain separate unresolved facts.
