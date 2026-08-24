# Debugging and Testing

Use this reference to reproduce failures, validate EAF packaging, diagnose Python/JVM hooks and
plan device tests.

## Debug in layers

Do not jump straight from code edit to "it should work on device". Identify the lowest layer
that can prove or disprove the suspected contract.

Recommended ladder:

1. syntax/static validation;
2. builder/unit/smoke tests;
3. archive inspection;
4. real Gradle → DEX build;
5. bridge/reflection resolution;
6. EAF installation/load;
7. feature behavior;
8. unload/reload/re-enable behavior;
9. host-version regression.

A green lower layer does not prove the layers above it, but a red lower layer gives a faster,
more precise diagnosis.

## Python validation

At minimum:

- parse/compile Python tooling and plugin modules;
- run the repository's configured linter/type checks when available;
- ensure local imports match the EAF archive layout;
- detect shadowed stdlib/SDK module names;
- validate generated/release metadata.

Desktop import failures for Android/Java modules can be expected when only stubs are present;
distinguish environment limitations from actual syntax/type errors.

## EAF smoke build

The template CI can test packaging with a small synthetic DEX when host JARs are unavailable.
This should prove the builder contract, not JVM semantics.

Useful assertions:

- exactly one `.eaf` output expected;
- `refmap.yml`, `metainfo.yml`, `main.py` present;
- required `src/` entry/modules present;
- `assets/classes.dex` present;
- DEX payload equals builder input;
- `main.py` equals source entry for the EAF path;
- no embedded DEX hex payload in EAF `main.py`;
- ZIP has no corrupt entry;
- no duplicate, absolute or traversal paths;
- `refmap` paths point to archive entries.

Add a regression assertion whenever a packaging bug is fixed.

## Real DEX build

Synthetic bytes do not test:

- Kotlin compilation;
- host API compatibility;
- Gradle transforms/relocation;
- D8 output;
- JVM class loading;
- bridge signatures.

When `Telegram.jar`/`Telegram-compile.jar` exist, CI should run the real release DEX task and
package that result.

If full CI is optional because JARs are absent, make the skip explicit and visible. Do not call
the pipeline a full integration test when the DEX build was skipped.

## Host JAR failure

If Gradle fails after upgrading the host APK:

1. confirm JARs were regenerated from the intended APK;
2. identify the first real compile error, not downstream noise;
3. inspect the changed target class in old/new decompile;
4. decide whether to update code, add compatibility probing, or raise min app version;
5. rebuild before touching unrelated code.

## Bridge diagnostics

Classify bridge failures:

### DEX not found/read

Log candidate path/asset availability and build/archive evidence. Do not continue to method
invocation.

### DEX class-load failure

Capture class name, loader parent choice and exception. Check that the class exists in the DEX
and that dependencies resolve from the parent.

### Method lookup failure

Capture declaring class, method name and exact Java parameter types. Compare Python and Kotlin
bridge definitions.

### Invocation failure

Separate reflection wrapper exceptions from the underlying exception thrown by Kotlin/Java.
Preserve the useful cause/trace when possible.

## Hook diagnostics

For a hook that does not fire:

1. did plugin load reach registration?
2. did class resolve?
3. did exact method/constructor resolve?
4. did `hook_method` return a handle/success?
5. is the target method actually called in this host flow?
6. is another overload used?
7. is a condition filtering every call?
8. is the hook on the correct account/screen/process state?

For a hook that crashes:

- log phase: registration/before/after/replacement;
- log class + signature;
- inspect `param.args` defensively;
- verify thread assumptions;
- reduce callback to a no-op/logging hook to isolate host compatibility from feature logic.

## Log sources

Useful diagnostics can come from:

- `self.log(...)`/plugin copy-logs UI;
- Android Logcat via ADB;
- Python/Chaquopy traceback;
- Xposed/JVM logs;
- custom bridge stage logging;
- GitHub Actions logs.

Example shell approach:

```bash
adb logcat -c
# reproduce
adb logcat -d | grep -iE 'chaquopy|plugin|exteragram|<plugin-id>'
```

Use broader log capture when filtering hides the Java cause.

## User-facing crash reports

A useful copyable report should include:

```text
stage
plugin version
app version/build if available
SDK version if available
account/screen when relevant
exception
short recent plugin log
bridge/hook target when relevant
```

Do not include auth tokens, cookies, private message content or unrelated user data by default.

## Device install test

For release-critical EAF changes:

1. build a clean EAF;
2. inspect archive locally;
3. install through the host-supported plugin installer;
4. enable it;
5. verify Python entry loads;
6. verify DEX class loads;
7. run at least one bridge method;
8. exercise the changed feature;
9. disable and re-enable;
10. restart app and test cold restore.

A live-reload-only test can miss archive/install metadata problems.

## Structured reload test

After initial install:

- Python-only edit: sync changed `.py`; verify reload without DEX rebuild;
- asset edit: sync asset; verify asset resolution after reload;
- DEX edit: rebuild DEX, replace `assets/classes.dex`, verify old generation ejects and new
  class loader activates;
- deleted module: verify stale imported module is not kept;
- moved module: verify imports and sync protocol both handle the move.

## Performance diagnostics

For hot hooks, check:

- calls per user action/frame;
- allocations per call;
- logging volume;
- reflection lookup frequency;
- settings/file/network access in callback;
- cache growth;
- Python↔Java transition count.

If UI jank appears, first make the hook body minimal and reintroduce work in measured steps.

## Negative tests

Test predictable failures rather than only happy path:

- missing/corrupt DEX;
- missing optional asset;
- malformed settings value;
- no visible Fragment;
- network unavailable;
- Telegram member missing on unsupported host version;
- background account event;
- plugin disabled during running job;
- duplicate reload;
- invalid EAF wrapper directory/id.

The plugin should fail with a diagnosable message, not half-load silently.

## CI result reporting

When reviewing GitHub Actions, report what actually ran.

Good:

```text
EAF smoke build: pass
binary DEX archive assertions: pass
Gradle/real DEX: skipped (host JARs absent)
```

Bad:

```text
CI green, therefore full plugin is tested
```

## Debugging checklist

- Reproduction exact and repeatable?
- Lowest failing layer identified?
- App/SDK/build version recorded?
- Current workflow/HEAD verified?
- Full DEX actually ran or clearly marked skipped?
- Hook signature proven from target source?
- Logs preserve underlying cause?
- Fix has a regression check?
- Device reload/disable path tested when lifecycle changed?
