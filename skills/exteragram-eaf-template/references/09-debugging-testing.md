# Debugging and Testing

Use this reference to reproduce failures, validate EAF packaging, diagnose Python/JVM hooks and
plan device tests.

## Debug in layers

Do not jump straight from code edit to "it should work on device". Identify the lowest layer
that can prove or disprove the suspected contract.

Recommended ladder:

1. metadata/identity validation;
2. syntax/static validation;
3. builder/unit/smoke tests;
4. archive/refmap inspection;
5. real Gradle → R8/D8 → DEX build;
6. final-Dex runtime type-surface validation;
7. DEX asset resolution/read;
8. JVM class-load/linkage;
9. bridge method resolution/inject;
10. EAF installation/load;
11. feature callback/hook behavior;
12. unload/reload/re-enable behavior;
13. host-version regression.

A green lower layer does not prove the layers above it, but a red lower layer gives a faster,
more precise diagnosis.

## First-cause rule

Always preserve and diagnose the earliest startup failure.

A message such as:

```text
cannot call invokeSettingsActionCallback: JVM plugin is not loaded
```

is usually secondary. It tells you only that `klass` was never established. Search earlier logs
for asset resolution, DEX read/magic, class loader, `loadClass`, linkage, or inject failure.

Do not start by changing the callback unless the earlier bridge stages are proven successful.

For a required JVM backend, do not silently register UI that can only emit secondary errors.
Fail initialization at the required stage or explicitly disable dependent UI/actions.

## Python validation

At minimum:

- parse/compile Python tooling and plugin modules;
- run the repository's configured linter/type checks when available;
- ensure local imports match the EAF archive layout;
- detect shadowed stdlib/SDK module names;
- validate generated/release metadata;
- verify required bootstrap does not assume `__file__` exists under Elyx.

Desktop import failures for Android/Java modules can be expected when only stubs are present;
distinguish environment limitations from actual syntax/type errors.

## Metadata/identity validation

Before expensive Gradle work, compare all identity/version surfaces that the repository still
supports.

Typical template checks:

```text
metainfo.id == Python __id__ == JVM Plugin.ID/equivalent
metainfo.version == Python __version__ == pyproject version
```

Artifact naming should derive from the canonical structured id.

Do not treat author as a fixed template invariant. It should be freely changeable by plugin
forks unless a product-specific policy explicitly says otherwise.

## EAF smoke build

The template CI can test packaging with a small synthetic DEX when host JARs are unavailable.
This should prove the builder contract, not JVM semantics.

Useful assertions:

- exactly one `.eaf` output expected;
- `refmap.yml`, `metainfo.yml`, `main.py` present;
- required `assets/`/`src/` entries exist as real ZIP directory entries when declared;
- required `src/` modules present;
- `assets/classes.dex` present;
- DEX payload equals builder input;
- `main.py` equals source entry for the EAF path;
- no embedded DEX hex payload in EAF `main.py`;
- ZIP has no corrupt entry;
- no duplicate, absolute or traversal paths;
- `refmap` paths point to archive entries.

A child entry like `assets/classes.dex` is not enough to prove the archive has an explicit
`assets/` directory entry. Test the exact installer contract.

Add a regression assertion whenever a packaging bug is fixed.

## Real DEX build

Synthetic bytes do not test:

- Kotlin compilation;
- host API compatibility;
- Gradle transforms/relocation;
- R8 consumer-rule behavior;
- D8 output;
- final-Dex unresolved type references;
- JVM class loading;
- bridge signatures.

When `Telegram.jar`/`Telegram-compile.jar` exist, CI should run the real release DEX task and
package that result.

If full CI is optional because JARs are absent, make the skip explicit and visible. Do not call
the pipeline a full integration test when the DEX build was skipped.

## Final-Dex runtime surface

For independently loaded/shaded DEX, inspect unresolved type descriptors after the final
R8/D8 output.

Unexpected types can reveal:

- compile-only annotations retained into runtime metadata;
- missing embedded runtime dependencies;
- relocation mistakes;
- host classes accidentally treated as bundled or vice versa.

A real example is `Landroidx/annotation/AnyThread;` surviving into release DEX. A successful
R8 run alone does not prove that ART can link the class.

Do not solve unexpected types by blindly widening an allowlist. Establish who is supposed to
provide each type.

## Host JAR failure

If Gradle fails after upgrading the host APK:

1. confirm JARs were regenerated from the intended APK;
2. identify the first real compile error, not downstream noise;
3. inspect the changed target class in old/new decompile;
4. decide whether to update code, add compatibility probing, or raise min app version;
5. rebuild before touching unrelated code.

If R8 fails after shading/relocation, additionally check:

- original dependency JARs still available on R8 classpath where needed;
- stale `META-INF` R8/ProGuard consumer rules from relocated dependencies;
- semantic rules that must be translated to relocated packages;
- dex2jar synthetic descriptor mismatches such as `Foo-IA` vs `Foo_IA`;
- broad warning suppression hiding the real cause.

## Bridge diagnostics

Log the bridge as explicit stages rather than one generic load operation:

```text
resolve DEX
read DEX
validate DEX magic
construct InMemoryDexClassLoader
load JVM entry class
resolve/invoke inject
register Python UI
resolve/invoke finalizeInject
invoke feature callback
```

### DEX not found/read

Log candidate path/asset availability and build/archive evidence. Do not continue to method
invocation.

For Elyx, do not assume `__file__` exists. Prefer the public asset facade or a documented/imported
runtime helper for early bootstrap. Log every attempted candidate if multiple fallbacks exist.

### Invalid DEX

Record source/path and byte count, then fail before class-loader creation. Validate DEX magic.

### DEX class-load/linkage failure

Capture:

- exact class name;
- loader parent choice;
- DEX source/path and build identity;
- complete exception/cause.

Check that the entry class exists in the final DEX and that its unresolved dependencies are
provided by the intended parent or bundled DEX.

Distinguish `ClassNotFoundException` for the entry class from `NoClassDefFoundError`/linkage of a
dependency.

### Method lookup failure

Capture declaring class, method name and exact Java parameter types. Compare Python and Kotlin
bridge definitions.

### Invocation failure

Separate reflection wrapper exceptions from the underlying exception thrown by Kotlin/Java.
Preserve the useful cause/trace when possible.

### Inject/finalize failure

Class load success does not prove plugin initialization. Log `inject`, Python UI registration
and `finalizeInject` separately so a hook failure is not confused with class loading.

## Hook diagnostics

For a hook that does not fire:

1. did plugin load reach registration/finalize?
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
plugin id/version
artifact/build/head identity when known
app version/build if available
SDK version if available
account/screen when relevant
DEX source/path for bridge failures
JVM entry/method target when relevant
exception
short recent plugin log
```

Do not include auth tokens, cookies, private message content or unrelated user data by default.

## Device install test

For release-critical EAF/JVM changes:

1. build a clean EAF from exact current head;
2. inspect archive locally;
3. install the exact CI/artifact build through the host-supported installer;
4. verify displayed id/version/author are expected;
5. enable it;
6. verify Python entry loads;
7. verify DEX bytes resolve/read;
8. verify JVM entry class loads and inject succeeds;
9. run at least one Python → JVM bridge method;
10. exercise the changed feature;
11. verify a representative hook when hook/finalize code changed;
12. disable and re-enable;
13. restart app and test cold restore.

A live-reload-only test can miss archive/install metadata problems.

A successful feature log such as a Kotlin context-menu callback is strong evidence that
installation, Python bridge, DEX loading, class linking, inject and that callback path work.
It does not prove unrelated lifecycle/hooks that were not exercised.

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
- missing explicit declared asset directory entry;
- `__file__` absent during Elyx entry execution;
- missing optional asset;
- malformed settings value;
- no visible Fragment;
- network unavailable;
- Telegram member missing on unsupported host version;
- background account event;
- plugin disabled during running job;
- duplicate reload;
- invalid EAF wrapper directory/id;
- unexpected unresolved compile-only type in final DEX.

The plugin should fail with a diagnosable message, not half-load silently.

## CI result reporting

When reviewing GitHub Actions, report what actually ran and on which head.

Good:

```text
EAF smoke build: pass
binary DEX archive assertions: pass
real Gradle/R8 DEX: pass
final DEX runtime surface: pass
device runtime: not yet tested
```

Bad:

```text
CI green, therefore full plugin is tested
```

For PR workflows, remember `github.sha` can be the synthetic merge SHA. Correlate a device
artifact with the PR head SHA/run/artifact metadata rather than assuming the displayed SHA is
the source head.

## Debugging checklist

- Reproduction exact and repeatable?
- Earliest failing layer identified?
- Secondary errors separated from primary cause?
- App/SDK/build version recorded?
- Exact artifact/head/run recorded for device test?
- Current workflow/HEAD verified?
- Full DEX actually ran or clearly marked skipped?
- Final-Dex runtime type surface checked for standalone/shaded DEX changes?
- Required asset bootstrap works without `__file__`?
- Hook signature proven from target source?
- Logs preserve underlying Java/Chaquopy cause?
- Fix has a regression check for the broken external contract?
- Device Python → JVM callback tested for bridge/runtime changes?
- Device reload/disable path tested when lifecycle changed?
