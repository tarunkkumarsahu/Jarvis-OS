# JARVIS Master Engineering Checklist

This document is the single source of truth for the long-term engineering direction of JARVIS.

## North Star

JARVIS should evolve from a conversational assistant into a local-first autonomous personal computer agent that turns a high-level goal into a verified outcome:

`GOAL -> UNDERSTAND -> PLAN -> SELECT TOOLS -> PERMISSION -> EXECUTE -> OBSERVE -> VERIFY -> RECOVER/REPLAN -> REMEMBER -> REPORT`

The model may propose actions, but execution must always pass through controlled tools, permissions, workspace boundaries, and verification.

## Phase 0 - Runtime Stability

- [x] Deterministic commands can boot without the Python `ollama` package.
- [ ] Subsystem health model: HEALTHY / DEGRADED / OFFLINE.
- [ ] Ollama model/server health check.
- [ ] Bounded LLM request timeout.
- [ ] Hung worker cancellation.
- [ ] User-visible degraded/error state instead of silent hangs.
- [ ] Startup dependency self-check.
- [ ] Startup smoke tests.

## Phase 1 - Core Execution Architecture

- [x] Central Brain.
- [x] Event bus.
- [x] Runtime states.
- [x] Tool registry.
- [x] SAFE / CONFIRM / DESTRUCTIVE permissions.
- [x] Session approvals for CONFIRM tools.
- [ ] ToolRegistry becomes the single owner of permission -> started -> finished/error lifecycle.
- [ ] Provider and Brain stop duplicating tool lifecycle events.
- [ ] Legacy deterministic routes execute only through ToolRegistry.

## Phase 2 - Workspace and Files

- [x] Explicit workspace context.
- [x] Path escape protection.
- [x] Bounded directory listing.
- [x] Bounded UTF-8 text reading.
- [ ] Create text file.
- [ ] Create directory.
- [ ] Replace/edit text file.
- [ ] Append text.
- [ ] Copy.
- [ ] Move/rename.
- [ ] File metadata/hash.
- [ ] Delete file/directory as DESTRUCTIVE.
- [ ] No silent overwrite.
- [ ] Post-write verification.

## Phase 3 - Terminal

- [ ] Controlled command execution.
- [ ] Explicit cwd.
- [ ] Timeout and process termination.
- [ ] stdout / stderr / exit code / duration.
- [ ] Bounded output.
- [ ] Prefer shell=False.
- [ ] Workspace scoping.
- [ ] Command risk policy.
- [ ] Dangerous command blocking.
- [ ] Execution verification.

## Phase 4 - Git

- [x] git status.
- [x] Current branch/upstream/ahead/behind inspection.
- [x] git diff for staged and unstaged changes.
- [x] Timeout and bounded output.
- [ ] git log.
- [ ] Branch listing.
- [ ] Create branch as CONFIRM.
- [ ] Checkout/switch as CONFIRM.
- [ ] git add as CONFIRM.
- [ ] git commit as CONFIRM.
- [ ] Commit verification.
- [ ] Guarded push later.
- [ ] Reset/clean remain highly restricted.

## Phase 5 - App and System Control

- [x] Open known apps.
- [x] Open paths/projects.
- [x] Browser URL/search.
- [x] Volume/media controls.
- [x] Settings and lock workstation.
- [x] Shutdown/restart protected by permissions.
- [ ] Split known-app launch from arbitrary executable launch.
- [ ] Safe close application.
- [ ] Window focus/minimize/maximize.
- [ ] Active-window awareness.
- [ ] Clipboard tools.

## Phase 6 - Deterministic Intelligence

- [x] Deterministic routing for obvious commands.
- [x] Basic Hindi/Hinglish normalization.
- [ ] Central structured intent representation.
- [ ] Confidence threshold.
- [ ] Ambiguous requests fall through to planner.
- [ ] No direct execution paths outside ToolRegistry.

## Phase 7 - Planner

- [ ] Goal classifier.
- [ ] Structured TaskPlan / TaskStep output.
- [ ] Planner may choose only registered tools.
- [ ] Schema validation.
- [ ] Initial maximum of about six steps.
- [ ] Dependency ordering.
- [ ] Permission-aware planning.
- [ ] Plan preview in ASSIST mode.
- [ ] Reject hallucinated tools.

## Phase 8 - Task Runtime

- [x] TaskPlan execution foundation.
- [x] Step execution and observations.
- [x] Bounded retries.
- [x] BLOCKED / FAILED / COMPLETED-style states.
- [ ] Real COMMAND / ASSIST / AUTO policies.
- [ ] Dependency-aware steps.
- [ ] Cancellation.
- [ ] Pause/resume.
- [ ] Checkpointing.
- [ ] Task-level success criteria.

## Phase 9 - Verification

- [ ] Dedicated Verifier component.
- [ ] File existence/content/hash verification.
- [ ] Process/app verification.
- [ ] Terminal exit/result verification.
- [ ] Git-state verification.
- [ ] Test-result verification.
- [ ] Browser-state verification later.
- [ ] Distinguish EXECUTED from VERIFIED.
- [ ] PARTIALLY_VERIFIED state.
- [ ] JARVIS never says done without evidence.

## Phase 10 - Recovery and Replanning

- [ ] Error classification.
- [ ] Failure observation.
- [ ] Retry only when appropriate.
- [ ] Adjust arguments after failure.
- [ ] Alternative tool strategy.
- [ ] Replan remaining work.
- [ ] Global step/retry limits.
- [ ] Safe blocked-task report.

## Phase 11 - Context and Computer Awareness

- [ ] Current workspace.
- [ ] Active app/window.
- [ ] Running applications.
- [ ] Clipboard.
- [ ] Current Git project.
- [ ] Battery/power/network state.
- [ ] Audio/media state.
- [ ] Context snapshot for planner.
- [ ] Sensitive-context filtering.

## Phase 12 - Memory

- [x] Basic persistent key-value memory foundation.
- [ ] SQLite-backed memory.
- [ ] User preferences.
- [ ] Task history.
- [ ] Workspace/project memory.
- [ ] Episodic events.
- [ ] Provenance/confidence/timestamps.
- [ ] Goal-aware retrieval.
- [ ] Consolidation later.

## Phase 13 - Voice

- [x] Local STT foundation.
- [x] Wake word.
- [x] TTS foundation.
- [x] Shared single-microphone audio service.
- [x] Ring buffer and wake-to-command handoff foundation.
- [ ] Runtime-owned audio lifecycle.
- [ ] Formal voice state machine.
- [ ] Barge-in/interruption.
- [ ] 10-15 second follow-up conversation window.
- [ ] One-shot wake + command reliability.
- [ ] TTS self-trigger protection verification.
- [ ] Voice acceptance suite.
- [ ] Optional ElevenLabs adapter with local Kokoro fallback.

## Phase 14 - Browser Agent

- [x] Open URL and search browser.
- [ ] Browser automation engine.
- [ ] Read page state.
- [ ] Click/type/forms.
- [ ] Multi-tab state.
- [ ] Downloads.
- [ ] Screenshot/state observation.
- [ ] Outcome verification.
- [ ] Site-specific permissions.

## Phase 15 - Coding Agent

- [ ] Inspect repository.
- [ ] Search code.
- [ ] Read relevant files.
- [ ] Plan changes.
- [ ] Edit source.
- [ ] Run tests.
- [ ] Diagnose failures.
- [ ] Retry/fix.
- [ ] Inspect Git diff.
- [ ] Commit with approval.
- [ ] Isolated branch/worktree.
- [ ] Never modify a protected branch directly.

## Phase 16 - Autonomous Modes

- [ ] COMMAND mode.
- [ ] ASSIST mode.
- [ ] AUTO mode.
- [ ] Mode-specific permission policy.
- [ ] Step/time/model-call budgets.
- [ ] Human checkpoints.
- [ ] Emergency stop.
- [ ] Persistent task status.

## Phase 17 - Scheduling and Overnight Work

- [ ] Internal task queue.
- [ ] Scheduled tasks.
- [ ] Persistent checkpoints.
- [ ] Resume after crash.
- [ ] Isolated execution workspace.
- [ ] Retry limits.
- [ ] Approval queue.
- [ ] Resource limits.
- [ ] Morning report.

## Phase 18 - HUD and Observability

- [x] Desktop dashboard foundation.
- [x] Runtime state display.
- [x] Permission UI foundation.
- [ ] Health panel.
- [ ] Current plan and step.
- [ ] Active tool.
- [ ] Verification state.
- [ ] Error/recovery state.
- [ ] Execution traces.
- [ ] Tool arguments and observations.
- [ ] Latency metrics.
- [ ] Task history.
- [ ] Pause/cancel controls.

## Phase 19 - Testing and Reliability

- [x] Unit tests exist for multiple core components.
- [ ] Full suite proven green.
- [ ] CI workflow.
- [ ] Startup smoke test.
- [ ] Tool-permission tests.
- [ ] Planner golden tests.
- [ ] Natural-language -> expected-tool evals.
- [ ] End-to-end agent tests.
- [ ] Voice acceptance tests.
- [ ] Failure/recovery tests.
- [ ] Security/path-escape tests.
- [ ] Destructive-action denial tests.
- [ ] Regression benchmark.

## Phase 20 - Security

- [x] Permission levels.
- [x] Workspace boundary.
- [x] Destructive-action confirmation foundation.
- [ ] Protected directories.
- [ ] Command allow/deny policy.
- [ ] Secret redaction.
- [ ] Credential handling.
- [ ] Network-action policy.
- [ ] External-message approval.
- [ ] Production/deployment approval.
- [ ] Audit log.
- [ ] Agent sandbox/worktree.
- [ ] Prompt-injection defenses for browser/files.

## Open-Source Strategy

Prefer proven open-source building blocks while keeping JARVIS core orchestration under our control.

- LLM runtime: Ollama + Qwen.
- Wake/STT: openWakeWord + faster-whisper.
- Voice pipeline references: Pipecat.
- TTS: local Kokoro first; ElevenLabs optional adapter.
- Browser automation: Playwright.
- Storage: SQLite/FTS first.
- IoT: Home Assistant / MQTT later.
- Agent architecture references: OpenJarvis, Leon, AgenticSeek.

Before adopting any component, review license, maintenance status, architecture fit, security surface, and dependency cost.

## First Real JARVIS Acceptance Milestone

User says:

`Jarvis, inspect this project and fix the obvious problem.`

JARVIS must then:

- identify the workspace;
- inspect Git status;
- read relevant files;
- create a bounded plan;
- ask permission for modifications;
- edit required files;
- run tests;
- observe failures;
- recover when sensible;
- run tests again;
- inspect the Git diff;
- verify the outcome;
- report exactly what changed;
- never claim success without evidence.

## Current Development Order

`Runtime Stability -> Execution Lifecycle -> Writable Files -> Terminal -> Git Writes -> Planner -> Verifier -> Recovery -> Context/Memory -> Coding Agent -> Autonomous Mode -> Browser -> Scheduling -> IoT`

Development should optimize for coherent architecture, real capabilities, safety, verification, and maintainability rather than commit count or code volume.
