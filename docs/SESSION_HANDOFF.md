---
date: 2026-05-29T09:04:21+01:00
researcher: ayush.sharma@keploy.io
git_commit: 4a83c80
branch: main
repository: ayush3160/keploy-sample-python-asyncpg-tls
companion_pr: https://github.com/keploy/enterprise/pull/2049
topic: "Keploy low-latency (proxyless) TLS-uprobe attach for sibling-container topologies — ns_pid plumbing + recorder-side desync"
tags: [keploy, enterprise, proxyless, ebpf, tls-uprobe, ns_pid, postgres_v3, recorder, integrations]
status: in_progress
last_updated: 2026-05-29
last_updated_by: ayush.sharma@keploy.io (with Claude Opus 4.7)
type: implementation_strategy
---

# Handoff: Keploy low-latency TLS uprobe attach in sibling-container Docker topologies

## Context for the next agent

This document is the session handoff for a multi-day debugging arc that started with "why doesn't `keploy record --low-latency` produce any mocks for a TLS-on-Postgres FastAPI app" and ended with:
- a feature PR landed in `keploy/enterprise#2049` that plumbs `ns_pid` through BPF + userland to make TLS uprobe attach work across PID-namespace boundaries
- a reproducible sample app committed to **this** repo (`ayush3160/keploy-sample-python-asyncpg-tls`)
- a remaining recorder-side desync in `keploy/integrations` postgres_v3 that breaks replay (recorded mocks have ParamOIDs paired with the wrong SQL)

If you're picking this up cold, **read `companion_pr` (keploy/enterprise#2049) first** — its description is the cleanest single explanation of the architecture. Then come back here for the "what's still broken" pointer and the recorder-side fix sketch.

## Task(s)

### 1. Reproduce + understand the original bundle — COMPLETED
Started from `provider-engagem-provider-engagement-serv-ts-08173f93-217936e4/` (a Keploy debug bundle for Globality's `provider-engagement-service`). Identified stack:
- Python 3.13, gunicorn + `uvicorn.workers.UvicornWorker`
- FastAPI + pydantic with camelCase aliases
- SQLAlchemy[asyncio] + asyncpg against TLS Postgres (CA-pinned, hostname-verified)
- boto3 SNS outbox (event-factory pattern, media-types like `application/vnd.globality.pubsub._.created.*`)

### 2. Build sample app matching the stack — COMPLETED
Created the 10-module FastAPI app under `app/`, gunicorn + uvicorn worker config, Postgres+TLS docker-compose, entrypoint that waits for DB + runs schema init ONCE (to avoid the gunicorn-worker race on `pg_type_typname_nsp_index`), and seed data for the recorded UUIDs. See `app/`, `docker-compose.yml`, `scripts/entrypoint.sh`, `app/seed.py`.

### 3. Diagnose the empty-mocks bug — COMPLETED
Traced through THREE distinct failure modes, each fixed in turn:
- **Mocks written to wrong path** — proxyless agent wrote to `/test-set-0/` inside its container instead of the `/keploy-host` bind-mount because `sockmap_proxy.go::persistTestCases/persistMocks` used a relative path against `s.conf.Path` which was empty for the `agent` command (the OSS `case "agent":` in `keploy/cli/provider/cmd.go:1301` doesn't set `c.cfg.Path`).
- **Channel routing — proxyless never streamed to the host CLI** — old code drained locally via `persistTestCases`/`persistMocks` goroutines. Refactored `afterStartProxyless` to route TCs through `ipMgr.TCChan()` and defer mock-channel wiring to the recorder's `Proxy.Record` call. Local-YAML fallback retained for embedder-without-recorder case. (See `enterprise/pkg/agent/proxy/sockmap_proxy.go` afterStartProxyless region in PR.)
- **TLS uprobe attach ENOENT** — `tls_loader.go:792` readlinks `/proc/<host_pid>/exe` but agent is in its own PID NS and host PID doesn't resolve. **Tried `pid: host`** — broke OSS BPF sys_socket_entry auto-register (every host process became a target, including curl). **Final fix: emit `ns_pid` from BPF** via `bpf_get_ns_current_pid_tgid()`.

### 4. Make DNS/nscd/resolved captures uniform — COMPLETED
Refactored DNS / nscd / resolved capture pipelines onto a `MocksSink` closure that resolves `p.session.MC` at emit time (matches what `routeEgressToParser` already does for egress parsers). Previously they captured `sess.MC` at lazy-bind time and dropped events whenever the recorder session bound later than the first event.

### 5. Land the ns_pid feature in keploy/enterprise — COMPLETED
PR https://github.com/keploy/enterprise/pull/2049 — 3 commits:
- `feat(proxyless): emit ns_pid in capture events for cross-NS uprobe attach`
- `chore(bpf): regenerate proxyless BPF objects after ns_pid layout change`
- `test(proxyless): regression tests for CaptureEventHdr wire layout`

### 6. Replay-side recorder desync — IDENTIFIED, NOT FIXED
`keploy record --low-latency` produces mocks now, but `keploy test` fails on replay with:
```
BuildIndex: query mock "mock-9" has 2 ParamOIDs but 0 BindValues
— every v3 query cohort with partial ParamOIDs must have len==binds
```
This is a recorder-side bug in `keploy/integrations/pkg/postgres/v3/recorder/query_capture.go` — the `pending` FIFO desyncs when consuming SSL-event-framed plaintext instead of a continuous TCP stream. Fix is the next PR; **not in scope of PR#2049**.

## Critical References

- **`keploy/enterprise#2049`** — the feature PR that fixes the record-side problem end-to-end. Body has full behaviour matrix + commit layout.
- **`keploy/integrations/pkg/postgres/v3/recorder/query_capture.go:280-298`** — the `captureState.pending` FIFO whose invariant tears under SSL-event framing. Sibling `integrations/pkg/postgres/v3/types/index_loader.go:200-208` is the replay-side validator that catches the corruption.
- **`keploy/enterprise/pkg/agent/proxy/tls_loader.go:932-939`** — `hostVisiblePath` uses `/proc/<pid>/root%s`, the kernel-provided cross-mount-NS bridge. Existing and correct; the problem was that `<pid>` was wrong before ns_pid.

## Recent changes

In `keploy/enterprise` (branch `feat/proxyless-ns-pid-uprobe-attach`, merged-or-pending via PR#2049):

**BPF C source**
- `pkg/agent/proxy/bpf/proxyless.c` — added `struct keploy_agent_info_min`, `keploy_agent_registration_map` declaration, `agent_pid_ns_inode()` and `resolve_ns_tgid()` helpers (mirror of OSS `keploy_ebpf.c:55-67`). Widened `proxyless_sock_meta_t` and `capture_event_hdr` by 4 bytes for `ns_pid`. HDR_SIZE 52→56.
- `pkg/agent/proxy/bpf/proxyless_ktls.c` — mirrors the same struct widening (both BPF programs emit into the SAME pinned ringbuf so layouts must be lockstep).

**Go layout + parser**
- `pkg/agent/proxy/proxyless_types.go:28-46` — `CaptureEventHdr.NsPid uint32`, `CaptureEventHdrSize = 56`.
- `pkg/agent/proxy/proxyless_ringbuf.go:1438-1462` — parser pulls `NsPid` from raw[52:56].
- `pkg/agent/proxy/proxyless_ringbuf.go:670-705` — TLS-detect path prefers `hdr.NsPid` with fallback to `hdr.KernelPid`. `onTLSDetected` signature widened from `func(pid uint32)` to `func(nsPid, hostPid uint32)`.

**Loader**
- `pkg/agent/proxy/proxyless_loader.go::populateAgentRegistration` (new) — `syscall.Stat("/proc/self/ns/pid")` and writes `keployAgentInfoForBPF{KeployAgentInode: st.Ino}` into the map at key 0. Called immediately after every `LoadAndAssign` success.
- Same file's three fallback branches (proxyless→legacy, noshards modern, noshards legacy) now propagate `KeployAgentRegistrationMap` from the variant `objs` into the canonical objs, mirroring how `TargetNamespacePids` and `TargetCgroupIds` are already propagated.

**sockmap_proxy.go**
- `afterStartProxyless` (region ~lines 783-850) — refactored channel wiring: tcChan uses `ipMgr.TCChan()` when IngressProxyManager is available, mock channel wiring is deferred to the recorder's `Proxy.Record` call. Local-YAML persisters kept as embedder-without-recorder fallback.
- TLS-detect callback registration — calls BOTH `attachTLSUprobesForPIDs([nsPid])` AND `primeTLSHostPIDFilter(hostPid)` to (a) attach userland uprobes against `/proc/<nsPid>/exe` and (b) populate `ssl_target_pids` so the BPF uprobe handler emits instead of filter-dropping.
- DoT (`dotCapture`) and JSSE (`jsseDNS`) capture constructions use the session-aware `MocksSink` closure.

**MocksSink refactor**
- `pkg/agent/proxy/dns_capture.go`, `nscd_capture.go`, `resolved_capture.go` — constructor signature changed from `chan<- *models.Mock` to `MocksSink func() chan<- *models.Mock`. Static-channel call sites use new `new{DNS,Nscd,Resolved}CaptureFromChan` helpers.

**Tests**
- `pkg/agent/proxy/proxyless_types_test.go` (new) — three guards: header size 56, NsPid parsed from offset 52, zero-fallback contract.

In `ayush3160/keploy-sample-python-asyncpg-tls` (this repo, `main`):
- Initial commit `4a83c80` — full FastAPI app + Postgres-TLS docker-compose + 10 recorded test sets + their mocks.yaml + record/replay logs.

## Learnings

### Why `pid: host` was wrong even though it "fixed" the readlink

Putting the agent in init_pid_ns lets `/proc/<host_pid>/exe` resolve, BUT the OSS BPF program at `keploy_ebpf.c:53-94` auto-registers ANY process whose PID NS matches the agent's into `target_namespace_pids` on the first `socket()` syscall. With `pid: host`, every host process — curl, dockerd, host system services — gets auto-registered. The very first call we made to test the app showed up as a `HTTP_CLIENT` *outgoing* mock from curl's perspective, instead of as an *ingress* test case to the app.

Tradeoff matrix that locked in the ns_pid fix:

| Goal | Requires |
|---|---|
| (A) `/proc/<host_pid>/exe` resolves | agent in host PID NS *or* host /proc bind-mounted *or* BPF emits namespaced PID |
| (B) IngressProxyManager observes app's `:bind()` events | agent shares app's PID NS |
| (C) BPF auto-register doesn't pull in random host processes | agent NOT in host PID NS |

`pid: host` satisfies (A) but breaks (B) and (C). `ns_pid` emitted from BPF satisfies (A) without touching the PID-NS topology — (B) and (C) keep working under the OSS default `pid: service:keploy-agent` pattern.

### How resolve_ns_tgid sources the inode

OSS keploy never pins `keploy_agent_registration_map` to bpffs — it just lives in the OSS BPF collection's memory. Enterprise's proxyless BPF collection is a *separate* collection; same map name does NOT share state. The fix: enterprise owns its own copy of the map and populates it from userland via `populateAgentRegistration` (reads `/proc/self/ns/pid` inode). proxyless.c's `resolve_ns_tgid` reads from that.

### Why BOTH ns_pid AND host_pid have to flow through the TLS-detect callback

- `ns_pid` is what `/proc/<pid>/exe` resolves to inside the agent's pid_ns view — what `tls_loader.AttachToProcess` needs.
- `host_pid` is what BPF programs see via `bpf_get_current_pid_tgid() >> 32` — what `ssl_target_pids` is keyed on.

If you only pass `ns_pid` and call `primeTLSHostPIDFilter(ns_pid)`, the BPF handler looks up the host_pid (which is different from ns_pid) in `ssl_target_pids`, misses, and drops the event. The proxyless callback now does both — see the dual-PID prime change in `sockmap_proxy.go::SetTLSDetectedCallback` registration.

### Recorder-side desync (the still-unfixed bit)

Recorded `mocks.yaml` (test-set-9) shows responses shifted by one slot relative to requests, and a `BEGIN` mock carries `paramOIDs:[2950,2950]` (UUID OIDs that actually belong to a later `SELECT ... IN ($1::UUID, $2::UUID)`).

Hypothesis: OpenSSL BIO may coalesce multiple Postgres protocol messages into a single SSL_write, or split one Postgres message across two SSL_writes. The recorder's `query_capture.go::captureQueries` reads from `pair.ClientConn` / `pair.ServerConn` (`SimulatedConn` fed by `pushTLSData`) and assumes byte-stream framing. When two `Parse` messages arrive in the same SSL event, the recorder's `psMap`/`portalMap` state machine attaches the second Parse's `paramOIDs` to the first invocation that hasn't been flushed by a `Sync` yet.

**Fix sketch** (in `keploy/integrations/pkg/postgres/v3/recorder/query_capture.go`):
1. Detect when an SSL event delivers more than one Postgres message at once. The decoded length-prefix already tells us where each message ends.
2. Drain the entire decoded event into a parser that walks per-message and only advances `pending` once per `Execute` (or simple-query `Q`). Today's per-Read loop conflates them.
3. **OR** add a defensive guard at line 727/754: if the next message arriving in the same SSL event would land a `Parse` while `pending[0]` is still a simple-query (BEGIN/COMMIT/ROLLBACK/SHOW…) without an Execute yet, that combination is wire-protocol-impossible — drop the mock instead of emitting cross-contaminated data.

### Pre-existing BPF compile issue worth knowing

`proxylesslegacy*` variants (kernel 5.10-5.16 fallback, `#pragma unroll for (i < MAX_IOVECS=8)`) hit a clang-14 unroller-exhaustion error on `emit_from_iov`. **Reproduces on pristine `main` before any of my changes** — confirmed by stashing the diff and running compile.sh; same error at the same code path, just line numbers shifted. Workaround: build legacy variants with clang-19, modern variants with clang-14. Documented in PR#2049's commit message for `chore(bpf): regenerate proxyless BPF objects`.

### vmlinux.h is host-specific

`enterprise/pkg/agent/proxy/bpf/vmlinux.h` is a 41-line stub in git. The build pipeline regenerates the real one (~127k lines) via `bpftool btf dump file /sys/kernel/btf/vmlinux format c`. Never commit the regenerated one; reviewers would reject 127k LoC of host-kernel BTF.

## Artifacts

In **this repo** (`ayush3160/keploy-sample-python-asyncpg-tls`):
- `app/` — the FastAPI sample. Routers per endpoint family, schemas with camelCase aliases, sns publisher mirroring the outbox-event-factory shape.
- `scripts/entrypoint.sh` — wait-for-DB + one-shot schema init + optional seed + exec gunicorn. Honors `REQUIRE_SSL` / `SSL_CA_FILE` env vars for the asyncpg probe.
- `tls/generate.sh` — local CA + server cert. OpenSSL 3 friendly (keyCertSign on CA, SAN on server). Run via `docker run --rm -v "$PWD/tls/certs:/certs" alpine:3.20 sh /generate.sh`.
- `keploy/test-set-{0..9}/` — recorded mocks and tests across the journey. test-set-1 is the proxy-mode reference; test-set-9 is the working low-latency capture. test-set-5 is the broken `pid: host` attempt (curl-as-HTTP_CLIENT).
- `record.log`, `replay.log`, `replay-test-set-1.log` — agent traces. Grep for `populated keploy_agent_registration_map`, `TLS uprobes attached for PID`, `BuildIndex` to find the diagnostic moments.
- `docker-compose.yml` — TLS on Postgres by default, app pinned to `REQUIRE_SSL=true` and CA-pinned + hostname-verified.

In **`keploy/enterprise`**:
- PR https://github.com/keploy/enterprise/pull/2049 (branch `feat/proxyless-ns-pid-uprobe-attach`).
- `pkg/agent/proxy/bpf/proxyless.c` lines ~155-250 — keploy_agent_registration_map decl + resolve_ns_tgid + meta widening.
- `pkg/agent/proxy/proxyless_loader.go` — `populateAgentRegistration` helper + three fallback-branch propagations + import of `syscall`.
- `pkg/agent/proxy/sockmap_proxy.go::afterStartProxyless` — channel wiring + SetTLSDetectedCallback dual-PID registration.
- `pkg/agent/proxy/proxyless_types_test.go` — regression tests.

In **`keploy/integrations`** (NOT YET MODIFIED — this is the next agent's first task):
- `pkg/postgres/v3/recorder/query_capture.go` — `captureState` struct + `captureQueries` loop. The desync lives here.
- `pkg/postgres/v3/types/index_loader.go:200-208` — the replay-side validator. Don't relax this; relaxing it just makes the corruption silent at replay time.

## Action Items & Next Steps

For the next agent picking this up:

1. **First: read PR keploy/enterprise#2049 description in full.** It's the single best-organized explanation of the architecture decisions and why each piece is shaped the way it is.

2. **Fix the recorder-side desync in `keploy/integrations`**:
   - Reproduce: in this repo, run `keploy record -c "docker compose up --build" --container-name=provider_engagement_service --low-latency`, then `keploy test`. Replay will fail at mock-9 in test-set-9 (or similar).
   - Read `pkg/postgres/v3/recorder/query_capture.go::captureQueries` and trace what happens when a single SSL event delivers `Parse + Bind + Execute + Sync` for SQL #1 followed by `Parse + Bind + Execute + Sync` for SQL #2 back-to-back. The current per-Read assumption is that each Read returns one Postgres message. Under SSL framing it can return many.
   - Easiest first cut: defensive guard at line 727/754 that drops a mock whose `pending[0]` is a simple-query AND `paramOIDs > 0` — those are wire-protocol-impossible and are the smoking-gun shape we see in test-set-9.
   - Proper fix: rewrite the read loop to walk all Postgres messages in a decoded SSL event in one pass, only advancing `pending` once per `Execute`/`Q`.

3. **DNS capture early-startup race (lower priority)**: test-set-9 has 0 DNS mocks where test-set-1 (proxy mode) has 4. DNS pipeline is session-aware now via `MocksSink`, but early DNS responses arrive as `DNS response with no matching pending query` because the request was missed before the agent's eBPF DNS tap was attached. The current code lazy-attaches the DNS pipeline on the first DNS event — that misses anything before. Bind it eagerly at agent boot, not on first event.

4. **Add a CI gate**: the BPF compile matrix should be CI-driven so reviewers don't have to trust hand-rolled `compile.sh` runs. The clang-14/clang-19 split for modern vs. legacy variants needs codifying.

5. **Cross-link the sample repo from the enterprise PR description** (if not already done): add a "Reproducible sample: `ayush3160/keploy-sample-python-asyncpg-tls`" line to the PR description so future contributors land here.

## Other Notes

### Pointers worth knowing

- **OSS keploy's `keploy/cli/provider/cmd.go:1301-1410`** is the `case "agent":` validate branch. It sets a LOT of fields but does NOT set `c.cfg.Path`. That omission was the original "writes-inside-agent-container" symptom. We worked around it in PR#2049 without touching OSS; if you want a more principled fix, add `c.cfg.Path = absPath + "/keploy"` here mirroring what `case "record":` does at line 1044.

- **OSS BPF auto-register**: `keploy_ebpf.c:53-94` is the `sys_socket_entry` hook. It calls `bpf_get_ns_current_pid_tgid(dev, agent_inode, …)` and if the NS matches, inserts the TGID into `target_namespace_pids`. This is what bites under `pid: host`. Don't go back to `pid: host` without disabling that auto-register first.

- **`tlsEventTargetsClientConn` at `ssl_capture.go:210-215`** is the connType×direction → ClientConn/ServerConn decision. It's correct — the SSL uprobe path has been delivering events to the right side of the pair for a while. The bug is one layer up: what the recorder does with those bytes after framing.

- **`proxyless_sock_meta_t` is shared between `proxyless.c` and `proxyless_ktls.c`** — both BPF programs declare `keploy_proxyless_meta` with this value type. The struct layout MUST stay in lockstep across the two C files; the PR ensures it does.

### Environment notes

- Kernel 6.12 (the host): all modern BPF variants load; legacy variants are the kernel-5.10-fallback flavour.
- Docker engine 27.x with `containerd` snapshotter: PID namespaces behave as documented above.
- Python 3.13 in the app container: links libssl.so.3 dynamically. SSL uprobe attach has been verified working with 16 probes (SSL_write/SSL_read entry+exit pairs + SSL_set_fd + SSL_connect + SSL_accept + SSL_shutdown + their _ex variants).
- The recorded artifacts in `keploy/test-set-{0..9}/` correspond to specific moments in the debugging journey — they're not all "good" recordings, but they're useful as fixtures showing what each fix changed. test-set-1 = proxy-mode reference; test-set-9 = working low-latency capture; test-set-5 = the broken `pid: host` attempt.

### What this handoff is NOT

- It's not a full transcript. The session was ~30 user turns over several days. This document captures the destination, the route taken, and the decisions; it doesn't reproduce every dead end. If you need the verbatim turns, ask the human — they may have a Claude Code transcript export from their side.
- It's not authoritative on the integrations-side fix. The recorder desync hypothesis is well-supported by the test-set-9 evidence, but the actual fix requires running the recorder code against SSL-framed plaintext and confirming the desync mechanism is exactly what I described. Don't skip that verification step.
