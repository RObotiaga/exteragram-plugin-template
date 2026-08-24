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
   - JVM bridge class path;
   - Python entry filename/workflow assumptions.
5. Generate host JARs from the exact target APK.
6. Run debug DEX build.
7. Run full release `just build`.
8. Inspect the EAF and install it once through the host UI.

Do not call initialization complete until the generated `metainfo.yml` id passes current Elyx
validation.

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
4. assert `src/feature.py` exists in archive;
5. install/live-reload and verify local import isolation.

## Recipe: add a static asset

1. Add file under repository `assets/`.
2. Never use source path `assets/classes.dex`; that name is reserved for generated DEX.
3. Ensure `refmap.yml` declares/discovers `assets`.
4. Access ordinary assets through `from elyx import assets`.
5. Treat bundled asset content as read-only.
6. Add archive assertion when the asset is release-critical.

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
9. Run full Gradle/DEX build.
10. Test reload several times and compare behavior/performance.

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
5. invoke method on device;
6. test failure path;
7. add cleanup if callback/reference crosses generations.

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
2. Run `just update-apk` to regenerate host JARs.
3. Compare important host classes used by hooks/bridge.
4. Run full release DEX build.
5. Fix compilation first.
6. Run hook/reflection smoke tests on device.
7. Run feature regression.
8. Decide compatibility policy:
   - keep old host support with probes;
   - or increase `app_version` minimum.
9. Update docs/release notes for intentionally dropped compatibility.

## Recipe: convert a legacy single-file plugin into this EAF template

1. Extract static metadata into `metainfo.yml`.
2. Pick an Elyx-safe id; do not blindly reuse a hyphenated legacy id.
3. Move helper classes/functions into thematic Python modules.
4. Move static resources into `assets/`.
5. Move large localization dictionaries into Elyx strings where useful.
6. Keep one `BasePlugin` entry class in `main.py`.
7. If DEX exists, package binary DEX as `assets/classes.dex` rather than encoded comments.
8. Preserve legacy build only when there is a real compatibility need.
9. Add EAF archive tests.
10. Test clean install, not only source reload.

## Recipe: debug `ClassNotFoundException` after DEX change

1. Confirm the expected bridge class exists in compiled output/DEX.
2. Confirm package/relocation settings did not rename/remove it unexpectedly.
3. Confirm correct DEX was packaged byte-for-byte.
4. Confirm parent loader choice can resolve host dependencies.
5. Confirm target device installed/reloaded the new DEX rather than an old generation.
6. Check for shrinker rules/removal.
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
2. Identify smallest machine-verifiable invariant.
3. Add assertion before/with fix.
4. Observe it fail on old behavior when practical.
5. Apply fix.
6. Re-run current-head CI.
7. Report which integration stages ran vs skipped.

Examples:

- DEX was accidentally hex-embedded: assert EAF `main.py` equals source and binary DEX equals
  input.
- wrapper directory broke install: assert `refmap.yml` is archive-root entry.
- invalid id shipped: parse `metainfo.yml` and enforce structured Elyx id grammar.

## Recipe: prepare a release

1. Resolve exact branch/head.
2. Ensure real host JARs are present and from target APK.
3. Ensure current-head CI passes.
4. Stamp version across all supported metadata surfaces.
5. Run real release DEX build.
6. Build deterministic EAF.
7. Validate archive.
8. Install/test release artifact on target client.
9. Attest exact artifact if provenance is enabled.
10. Tag source commit and publish exact `.eaf`.
