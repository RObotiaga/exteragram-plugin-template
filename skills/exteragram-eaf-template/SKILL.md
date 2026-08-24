---
name: exteragram-eaf-template-dev
description: >-
  Develop, debug, review, test and release plugins based on the
  RObotiaga/exteragram-plugin-template architecture: structured Elyx/EAF,
  multi-file Python/BasePlugin code, Kotlin compiled to classes.dex,
  binary DEX packaging, Telegram internals, Xposed-style hooks, UI integration,
  live reload, CI and GitHub releases. Use for changes to this template or
  plugins forked from it.
---

# exteraGram EAF + DEX Template Development

This skill is optimized for the multi-file EAF template, not for generic legacy
single-file `.plugin` development. Treat the checked-out repository and current
official exteraGram documentation as live sources of truth.

## First actions for every task

1. Resolve the exact repository, branch/PR and current HEAD. Do not work from a
   remembered SHA when GitHub can provide the current one.
2. Inspect the files that define the relevant contract before editing them.
   For this template those usually include `refmap.yml`, `metainfo.yml`, the
   root plugin entry `.py`, `plugin_src/`, `assets/`, `justfile`,
   `tools/build_eaf.py`, `build.gradle.kts`, and the relevant workflow.
3. Classify the requested change before choosing an implementation layer:
   - Python/BasePlugin or Elyx only;
   - Kotlin/DEX only;
   - Python ↔ JVM bridge contract;
   - Telegram/internal Java hook;
   - UI/settings;
   - build, CI, packaging or release;
   - host-version migration.
4. Read only the reference files needed for that class of work. Do not load the
   whole skill into context by default.
5. When an API, class name, method signature or packaging rule can vary by
   version, verify it against the current docs or the exact target APK/source.

## Template invariants

Unless a task explicitly changes the architecture, preserve these rules:

- The primary distributable is a structured `.eaf` archive.
- `refmap.yml` is at archive root; there is no wrapper directory around it.
- Structured metadata lives in `metainfo.yml`.
- `main.py` is the Python entry module in the EAF.
- Additional Python modules are packaged as normal Elyx-local modules. In the
  current template, repository `plugin_src/` is packaged under archive `src/`.
- Release DEX is binary `assets/classes.dex`; do not hex/base64-expand it into
  `main.py` for the EAF path.
- `assets/classes.dex` is generated from the selected build output and is a
  reserved archive path.
- The legacy embedded-DEX path (`tools/embed_dex.py` / `just embed`) is a
  compatibility path, not the canonical EAF design.
- Python ↔ Kotlin/JVM integration should use a small explicit bridge surface.
- Telegram internal methods are never guessed when source, decompile or runtime
  inspection can establish the exact signature.
- High-frequency hooks must be minimal, bounded and non-blocking.
- Every custom thread, observer, listener, socket, cache or JVM static resource
  that can outlive a reload needs explicit cleanup.

## Important EAF identifier rule

Structured Elyx metadata currently requires `id` to be 2–32 ASCII letters,
digits or `_`. A hyphen is invalid for an Elyx `metainfo.yml` id even though
legacy top-level plugin metadata may accept `-`.

When adapting this template, validate the structured EAF id separately from
legacy compatibility. If the repository still contains a hyphenated EAF id,
report it as a release blocker rather than silently copying the value.

## Reference routing

| Task | Read first |
|---|---|
| Decide which source is authoritative | `references/00-source-priority.md` |
| Understand this repository layout and bridge | `references/01-template-architecture.md` |
| EAF/refmap/metainfo/modules/assets/live reload | `references/02-elyx-eaf.md` |
| BasePlugin/hooks/accounts/client utils | `references/03-python-baseplugin.md` |
| Gradle/Kotlin/D8/DEX/JAR/bridge | `references/04-kotlin-dex.md` |
| Java/Xposed/reflection/private members | `references/05-hooks-reflection.md` |
| Telegram classes/controllers/messages/TLRPC | `references/06-telegram-internals.md` |
| Settings/menu/dialog/bulletin/custom UI | `references/07-ui-settings.md` |
| Threads/reload/eject/cleanup/races | `references/08-lifecycle-concurrency.md` |
| Reproduce, diagnose and test failures | `references/09-debugging-testing.md` |
| `just`, GitHub Actions, releases and provenance | `references/10-build-ci-release.md` |
| Common implementation procedures | `references/11-recipes.md` |
| Known traps, version conflicts, migration hazards | `references/12-pitfalls-compatibility.md` |
| Upstream material and license notes | `references/SOURCES.md` |

## Layer selection

Prefer the highest-level stable API that satisfies the requirement:

1. Elyx/BasePlugin/public SDK helper.
2. Telegram public/internal Java API reached through normal interop.
3. Python Xposed-style hook/reflection.
4. Kotlin/DEX hook for performance, complexity or capabilities that justify it.

Do not move logic into Kotlin merely because Kotlin is available. Keep orchestration,
configuration and plugin-facing behavior in Python when practical; use DEX for
performance-sensitive hooks, complex Java interop, reusable JVM code, or behavior
that is substantially clearer on the JVM side.

## Change discipline

Before modifying code, state the contract being changed. Examples:

- archive contract: `refmap -> main/metainfo/assets`;
- bridge contract: method name + Java parameter/return types;
- hook contract: exact declaring class + method/constructor signature;
- lifecycle contract: who owns registration and who owns cleanup;
- release contract: which metadata is stamped and which artifact is attested.

After modifying code, verify the same contract at the lowest useful level and then
at least one level above it. For example, a packager change should be checked both
as ZIP contents and via CI; a hook change should be checked for reflection resolution
and on-device behavior.

## Rules against hallucinated API

- Do not invent `BasePlugin` methods from names that sound plausible.
- Distinguish TL/request hooks (`add_hook`) from arbitrary Java method hooks
  (`hook_method`).
- Do not invent Telegram method signatures. Read the target source/decompile.
- Do not assume a third-party skill is newer than the official docs.
- Do not assume upstream Telegram source is byte-for-byte identical to the
  target exteraGram/AyuGram build.
- Treat real-device deviations as version-specific evidence: record app/SDK
  versions and keep the documented API as the general baseline unless verified
  otherwise.

## Completion standard

A change is not complete merely because code was written. Depending on scope,
completion should include the relevant subset of:

- Python syntax/static checks;
- deterministic EAF smoke build;
- archive path/integrity/content assertions;
- real Gradle → DEX build when host JARs are present;
- exact bridge/reflection signature validation;
- cleanup/reload verification;
- device install/enable/disable/reload test;
- regression check for legacy `just embed` if compatibility is still promised;
- updated documentation/skill notes when architecture or workflow changed.
