# Implementation Recipes

Use these recipes as procedures, not copy-paste API guarantees. Verify current repository and
host signatures before applying them.

## Recipe: create a new plugin from the template

1. Start from a clean branch based on the current template release/HEAD.
2. Choose a structured Elyx id using 2–32 ASCII letters/digits/`_` only.
3. Run the repository rename/init command if it is valid for current EAF rules.
4. Verify changes to:
   - `metainfo.yml`;
   - legacy dunder metadata while legacy build remains supported;
   - Gradle namespace/root project name;
   - Kotlin package declarations;
   - JVM bridge class path and JVM-side plugin id;
   - Python entry filename/workflow assumptions;
   - artifact naming.
5. Verify id/version surfaces are synchronized; author must remain freely editable.
6. Generate host JARs from the exact target APK.
7. Run debug DEX build.
8. Run full release `just build`.
9. Inspect the EAF including explicit `assets/`/`src/` directory entries.
10. Install it once through the host UI and invoke one real Python → JVM callback when DEX is
    part of the plugin.

Do not call initialization complete until the generated `metainfo.yml` id passes current Elyx
validation and the structured artifact installs.

## Recipe: add a Python module

Repository:

```text
plugin_src/
├── __init__.py
└── feature.py
```

EAF:

```text
src/
├── __init__.py
└── feature.py
```

Import from entry module:

```python
from src.feature import Feature
```

Then:

1. keep Android/Java imports local if they make desktop analysis unnecessarily fragile;
2. validate syntax;
3. build EAF with synthetic or real DEX;
4. assert explicit `src/` directory entry and `src/feature.py` both exist in archive;
5. install/live-reload and verify local import isolation.

## Recipe: add a static asset

1. Add file under repository `assets/`.
2. Never use source path `assets/classes.dex`; that name is reserved for generated DEX.
3. Ensure `refmap.yml` declares/discovers `assets`.
4. Access ordinary assets through `from elyx import assets`.
5. Treat bundled asset content as read-only.
6. Add archive assertion when the asset is release-critical.
7. If the installer validates directories strictly, assert the explicit `assets/` ZIP entry,
   not only child asset paths.

## Recipe: add a Python BasePlugin request hook

1. Find the exact public hook contract in current docs.
2. Register it during `on_plugin_load`.
3. Implement callback with exact current signature.
4. Use callback `account` for follow-up work.
5. Return the correct `HookResult` strategy/field.
6. Keep callback non-blocking.
7. Add logs around feature decisions during development.
8. Test background-account behavior if applicable.

## Recipe: add an outgoing command

1. Register outgoing-message hook.
2. Validate `params.message` is a string.
3. Parse only the intended prefix/command.
4. If command text must not be sent, return/capture `CANCEL` before launching async work.
5. Carry `account` and dialog identifiers into background task.
6. Perform network/file work on plugin queue.
7. Return to UI thread only for UI feedback.
8. Handle plugin unload while the task is running.

## Recipe: add a public menu action

1. Check current `MenuItemType` values.
2. Choose the supported placement.
3. Register `MenuItemData` during load or through the host-managed lifecycle.
4. Treat callback context fields as optional unless documented for that menu.
5. Use context `account`/`dialog_id` instead of re-deriving selected state.
6. Remove item explicitly on unload if the SDK/current template requires ownership.
7. If the action requires JVM state, do not register/leave it active after required JVM bridge
   initialization failed.

If the public API cannot express the location/visibility, document why before using a Telegram
UI hook.

## Recipe: add a Java method hook from Python

1. Inspect exact target source/decompile.
2. Record class + exact signature.
3. Resolve reflection objects outside hot callback.
4. Choose before/after/replacement based on semantics.
5. Install hook and keep unhook handle.
6. Make callback minimal.
7. If callback modifies Views, use UI thread.
8. Unhook on unload/eject.
9. Test repeated reload for duplicate callbacks.

## Recipe: migrate a hot Python hook into Kotlin/DEX

Use this only when there is a reason such as high call frequency or complex JVM work.

1. Measure/characterize current Python hot path.
2. Keep Python lifecycle/settings as owner unless migration requires otherwise.
3. Define one narrow new bridge method or configuration callback.
4. Implement hook registration in Kotlin inject phase.
5. Cache reflected members outside callback.
6. Retain unhook handles/static state needed for eject.
7. Implement Kotlin `eject` cleanup before enabling feature.
8. Update Python bridge exact Java signature.
9. Run full Gradle/R8/DEX build and final-Dex runtime-surface validation.
10. Install the exact EAF artifact and invoke a real Python → JVM callback.
11. Test reload several times and compare behavior/performance.

## Recipe: add a Python ↔ Kotlin bridge method

Before coding write the contract:

```text
Python caller:
JVM class:
method:
static/instance:
parameters:
return:
exceptions/failure:
lifecycle:
```

Then:

1. implement JVM method;
2. use `@JvmStatic` or otherwise match reflection ownership deliberately;
3. update Python reflection lookup exact types;
4. build real DEX;
5. validate final-Dex runtime type surface;
6. invoke method on device from the exact EAF artifact;
7. test failure path;
8. add cleanup if callback/reference crosses generations.

## Recipe: use a temporary global host hook

For a narrow operation requiring an invasive replacement:

```python
handle = install_hook()
try:
    perform_operation()
finally:
    if handle is not None:
        unhook(handle)
```

Keep the hook window as short as possible. Do not leave broad security/path/URI bypasses
installed for the whole plugin lifetime unless the feature truly requires it and risk is
understood.

## Recipe: hook a recycled message/UI cell

1. Inspect actual cell bind method in target build.
2. Make feature decision from the newly bound model every time.
3. Apply plugin state idempotently.
4. Reset everything the plugin previously changed when current model does not match.
5. Never start duplicate network/background work on every rebind.
6. Use stable message/plugin state to deduplicate work.
7. Request UI refresh through a supported host mechanism when background result arrives.

## Recipe: add structured localization

1. Add `strings:` path to `refmap.yml` if not already present.
2. Create locale files using current Elyx naming/format rules.
3. Use stable semantic keys.
4. Ensure English fallback exists.
5. Replace user-facing embedded dictionaries incrementally.
6. Test missing locale/missing key.
7. Keep core startup independent of optional translation content where possible.

## Recipe: update target exteraGram/AyuGram APK

1. Pin/record the new APK version/build/checksum/source.
2. Run `just update-apk` (or the repository's current manual-APK workflow) to regenerate host
   JARs from that exact APK.
3. Verify CI sees real JAR bytes, not missing LFS objects/pointers.
4. Compare important host classes used by hooks/bridge.
5. Run full release DEX build.
6. Fix compilation/R8 issues first by cause.
7. Run final-Dex runtime-surface validation.
8. Run hook/reflection smoke tests on device.
9. Run feature regression.
10. Decide compatibility policy:
   - keep old host support with probes;
   - or increase `app_version` minimum.
11. Update docs/release notes for intentionally dropped compatibility.

## Recipe: convert a legacy single-file plugin into this EAF template

1. Extract static metadata into `metainfo.yml`.
2. Pick an Elyx-safe id; do not blindly reuse a hyphenated legacy id.
3. Synchronize Python/JVM identity surfaces with that id.
4. Move helper classes/functions into thematic Python modules.
5. Move static resources into `assets/`.
6. Move large localization dictionaries into Elyx strings where useful.
7. Keep one `BasePlugin` entry class in `main.py`.
8. If DEX exists, package binary DEX as `assets/classes.dex` rather than encoded comments.
9. Do not make EAF DEX loading depend only on Python `__file__`.
10. Preserve legacy build only when there is a real compatibility need.
11. Add EAF archive tests, including explicit declared directory entries.
12. Test clean install, not only source reload.
13. If DEX exists, invoke one bridge callback on device before calling migration complete.

## Recipe: debug `Assets directory not found!`

1. Inspect the exact EAF ZIP directory, not the repository tree.
2. Confirm `refmap.yml` is at archive root and declares the expected `assets` path.
3. Confirm the archive contains an explicit `assets/` entry, not only
   `assets/classes.dex`/other children.
4. Check `ZipInfo.is_dir()` or equivalent directory semantics.
5. Check there is no wrapper root such as `plugin/assets/`.
6. Add a regression assertion for explicit `assets/` (and `src/` if declared).
7. Rebuild and install the exact new artifact.

Do not "fix" this by removing the assets declaration when the plugin really needs assets.

## Recipe: debug `__file__ is unavailable`

1. Treat absence of `__file__` as valid Elyx runtime behavior, not an exotic Python failure.
2. Replace required `dirname(__file__)` asset discovery with the public `elyx.assets` facade when
   possible.
3. If very-early bootstrap requires a filesystem path, use a documented/imported runtime helper
   and centralize the installed-layout assumption in one bridge function.
4. Keep `__file__` only as an optional fallback candidate.
5. Verify every fallback symbol is actually imported/defined; do not use a nonexistent
   `globals().get(...)` fallback.
6. Log attempted candidates and exact reason each failed.
7. Add a negative/runtime test path that works with `__file__` missing.

## Recipe: debug `JVM plugin is not loaded`

Do **not** start by editing the failing settings/menu callback.

1. Search earlier startup logs for the first bridge failure.
2. Confirm DEX asset resolved and was read.
3. Confirm DEX magic/size is valid.
4. Confirm `InMemoryDexClassLoader` was constructed with intended parent.
5. Confirm JVM entry class exists in final DEX and `loadClass` succeeded.
6. Check for `NoClassDefFoundError`/linkage of entry dependencies.
7. Confirm `inject` completed.
8. Confirm Python UI was registered only after required bridge readiness.
9. Confirm `finalizeInject` completed when the action depends on hook/finalize state.
10. Preserve/report the earliest exception; treat `JVM plugin is not loaded` as secondary.

## Recipe: debug unexpected compile-only type in release DEX

Example symptom from this template:

```text
Landroidx/annotation/AnyThread;
```

1. Inspect final release DEX, not only compiled class/JAR inputs.
2. Determine whether the unresolved type is host-provided, bundled-runtime, compile-only, or a
   relocation bug.
3. If compile-only metadata, inspect R8 `-keepattributes` and annotation retention.
4. Avoid broad `-ignorewarnings`/allowlist expansion.
5. Remove/strip unnecessary CLASS-retention metadata or narrow kept annotation attributes.
6. Re-run runtime-surface validator and real build.
7. Install on device and cross the actual Python → JVM bridge.

## Recipe: debug R8 missing class after relocation

1. Identify the first missing class and which dependency should provide it.
2. Check whether the original dependency JAR is still on R8 classpath even if a relocated copy
   is program input.
3. Inspect packaged dependency consumer rules under `META-INF` for stale original package names.
4. Strip stale rules from relocated inputs when appropriate.
5. Translate semantically required rules to relocated packages instead of discarding them.
6. For dex2jar names such as `Foo-IA`, check whether `Foo_IA.class` is the real sanitized class
   and normalize only when that exact candidate exists.
7. Keep diagnostics strict; do not add global warning suppression.

## Recipe: debug `ClassNotFoundException` after DEX change

1. Confirm the expected bridge class exists in compiled output and final DEX.
2. Confirm package/relocation settings did not rename/remove it unexpectedly.
3. Confirm correct DEX was packaged byte-for-byte.
4. Confirm parent loader choice can resolve host dependencies.
5. Confirm target device installed/reloaded the exact new DEX rather than an old generation.
6. Check shrinker rules/removal.
7. Log class name and DEX/plugin version at load.

## Recipe: debug `NoSuchMethodException`

1. Determine whether failure is bridge method or host Telegram method.
2. Inspect exact target class and overload.
3. Verify primitive vs boxed Java types.
4. Verify static/instance assumption.
5. Compare host APK/JAR version used at compile time with runtime app.
6. Add a version-specific probe only if supporting multiple known signatures deliberately.

## Recipe: make CI prove a bug is fixed

1. Reproduce the bug locally/in a failing run if possible.
2. Identify smallest machine-verifiable **external contract** invariant.
3. Add assertion before/with fix.
4. Observe it fail on old behavior when practical.
5. Apply fix.
6. Re-run current-head CI.
7. Report which integration stages ran vs skipped.
8. For runtime-only failures, complement CI with an exact-artifact device gate.

Examples:

- DEX was accidentally hex-embedded: assert EAF `main.py` equals source and binary DEX equals
  input.
- wrapper/directory layout broke install: assert `refmap.yml` at root and explicit declared
  directory entries.
- invalid id shipped: parse `metainfo.yml` and enforce structured Elyx id grammar.
- metadata drifted: compare id/version surfaces before Gradle.
- compile-only type leaked: validate final-Dex unresolved runtime surface.
- R8 warning hidden: fail on warning/unmatched rules rather than suppress globally.
- test build unavailable: upload/publish the exact EAF artifact from full CI.

## Recipe: prepare a release

1. Resolve exact branch/head.
2. Ensure real host JARs are present and from target APK.
3. Ensure current-head CI passes.
4. Stamp and validate version across all supported metadata surfaces.
5. Keep author freely editable; do not restore a template-author constant.
6. Run real release DEX build with strict R8 diagnostics.
7. Validate final-Dex runtime surface.
8. Build deterministic EAF with explicit declared directory entries.
9. Validate archive.
10. Install/test the exact release artifact on target client for runtime architecture changes.
11. Attest exact artifact if provenance is enabled.
12. Tag source commit and publish that exact `.eaf`.
