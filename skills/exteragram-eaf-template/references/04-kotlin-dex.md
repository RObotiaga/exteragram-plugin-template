# Kotlin / DEX Layer

Use this reference for Gradle, host JARs, D8/DEX generation, JVM bridge design and
performance-sensitive hooks.

## Build model

The template compiles Kotlin/Android code and produces a release/debug `classes.dex` which is
packaged into EAF as binary `assets/classes.dex`.

Conceptually:

```text
Kotlin sources
  -> Kotlin/Java compilation against host stubs/JARs
  -> shrink/relocate/transform steps defined by build.gradle.kts
  -> D8 / Android build-tools
  -> classes.dex
  -> tools/build_eaf.py
  -> assets/classes.dex inside plugin.eaf
```

Do not replace the actual Gradle pipeline with a generic DEX recipe from another project.
Read the current `build.gradle.kts` tasks and workflow.

## Host JARs

Kotlin must compile against classes from the target Telegram/exteraGram/AyuGram build.
In this template those inputs are expected under `libs/`, currently including:

```text
libs/Telegram.jar
libs/Telegram-compile.jar
```

Generate them from the APK you actually target, using the repository's `just update-apk`
workflow or an explicitly verified replacement.

Why exact-version host JARs matter:

- private Telegram classes change frequently;
- method signatures and field types can move;
- exteraGram/AyuGram patches are not guaranteed to match upstream Telegram;
- compiling against an older JAR can succeed but fail at runtime;
- compiling against a newer JAR can introduce calls missing on older clients.

Do not download a random `Telegram.jar` and treat it as interchangeable.

Generated host JAR storage is a repository concern, but the bytes are an ABI input. Git LFS is
only useful when the actual fork and CI can restore its objects reliably. Whatever storage
strategy is chosen, CI must prove the real non-pointer JAR bytes are present before calling a
run a full DEX build.

## Updating the host baseline

When moving to a new target APK:

1. Record the app/version/build being targeted.
2. Regenerate both host JARs from that APK.
3. Diff/inspect important classes touched by the plugin.
4. Run full Gradle build.
5. Resolve compile errors deliberately; do not blanket-cast around API changes.
6. Re-run device tests for every private hook/bridge path.
7. Update minimum app constraints only after deciding compatibility policy.

If supporting several host versions, prefer explicit compatibility branches/probes rather than
silently relying on reflection failures.

## DEX integrity

The packager/CI should verify at minimum:

- input DEX exists and is non-empty;
- bytes start with DEX magic (`dex\n` plus version bytes);
- archive `assets/classes.dex` equals the selected input byte-for-byte;
- only one canonical DEX entry is present unless multidex is deliberately designed;
- Python entry source is not being used as a binary transport.

A synthetic DEX smoke payload can test archive plumbing, but it does not replace a real D8
build and runtime class-load test.

## Final DEX runtime type surface

Compilation and R8 success do not prove that a standalone plugin DEX can link on ART. The final
DEX can retain descriptors for classes that existed only on the compile classpath.

A concrete failure class is a compile-only annotation such as:

```text
Landroidx/annotation/AnyThread;
```

remaining in the release DEX even though that annotation class is not bundled and is not
provided by the host loader.

Validate the **final release DEX** after R8/D8:

1. enumerate classes defined in the DEX;
2. enumerate referenced type descriptors;
3. subtract defined types;
4. allow only known runtime providers (Android/Java and exact host-provided Telegram/extera/
   hook APIs);
5. fail on unexpected compile-only or missing-runtime packages.

Do not expand the allowlist automatically. Determine whether each unresolved type is intended
host API, leaked compile-only metadata, missing embedded dependency, or relocation bug.

## Annotation retention in standalone DEX

Broad rules such as:

```proguard
-keepattributes *Annotation*
```

can preserve runtime-invisible/CLASS-retention annotations that are useful only to tools.
Those descriptors can become runtime linkage liabilities in an independently loaded DEX.

Keep only annotation attributes genuinely required at runtime, or explicitly strip known
compile-time marker metadata. Re-run final-Dex runtime-surface validation after changing
retention.

## R8 and relocation discipline

### No broad warning suppression

Do not use broad `-ignorewarnings` to get a green build. Missing classes and unmatched rules
must be understood by cause. A narrow `-dontwarn` is acceptable only for a class proven to be
an irrelevant compile-time marker.

### Consumer rules can become stale after relocation

Dependency JARs may contain R8/ProGuard consumer resources written for their original package
names. Once classes are relocated, blindly copying those resources can produce unmatched rules
or preserve the wrong things.

Strip stale packaged rules from relocated program inputs when appropriate, but preserve their
semantics when they are required. For example, kotlinx-coroutines rules that retain volatile
fields used by field updaters must be translated to the relocated coroutine namespace rather
than discarded. The same applies to relocated `SafeContinuation` volatile fields.

### Original dependencies can still belong on the R8 classpath

Embedded dependencies may be relocated as program input while their original JARs remain on
R8's classpath to resolve original/unrelocated signatures. If R8 reports a basic type such as
`kotlin.Unit` missing after shading, inspect classpath construction before adding keep rules.

### dex2jar synthetic class descriptors need precise normalization

A dex2jar host JAR can contain a class file like `Foo_IA.class` while another descriptor still
references `Foo-IA`. Normalize to the sanitized underscore name only when that exact candidate
class is known to exist. Do not globally rewrite all hyphens.

### Strict diagnostics should be machine-gated

If the repository intentionally treats R8 `Warning:` or unmatched ProGuard-rule diagnostics as
errors, keep that gate explicit in the build/CI. A warning-free run should be meaningful, not
the result of global suppression.

## Class loading

The template uses a Python bridge to load a JVM entry class. `InMemoryDexClassLoader` is useful
when DEX bytes are already available in memory and avoids managing an optimized output path.

Typical responsibilities:

```text
read DEX bytes
-> ByteBuffer
-> InMemoryDexClassLoader(parent=host class loader)
-> load stable entry class
-> resolve known methods
-> invoke
```

Use the host/application class loader as the parent unless a tested architecture requires
another loader. Class-loader choice affects resolution of Telegram, Android, Xposed and plugin
classes.

Do not change the parent loader to compensate for an unrelated packaging or missing-dependency
bug. First prove which type is missing and which loader/input is supposed to provide it.

Do not cache a class or class loader across plugin generations unless lifecycle semantics are
explicitly designed for it.

## JVM entry facade

Prefer one stable bridge class, for example conceptually:

```kotlin
object PluginBridge {
    @JvmStatic fun inject(version: String, logger: ValueCallback<Any?>) { ... }
    @JvmStatic fun finalizeInject() { ... }
    @JvmStatic fun eject() { ... }
    @JvmStatic fun invokeAction(key: String, dialogId: Long) { ... }
}
```

The exact class and methods in the repository are authoritative.

Advantages of a narrow facade:

- fewer reflection strings/signatures in Python;
- easier compatibility tests;
- Kotlin internals can refactor without changing Python;
- lifecycle cleanup has one obvious owner;
- errors can be wrapped/logged consistently.

Keep the entry class name stable through shrinking/relocation or explicitly keep it. Confirm it
exists in the final DEX before blaming the class loader.

## Exact reflection types

Python reflection into JVM methods must specify Java parameter types exactly where required.
A Python `int` is not a sufficient description of whether Java expects `int`, `long`, boxed
`Integer`, boxed `Long`, etc.

When changing a bridge signature, change and review both sides in one patch. Add a smoke check
or explicit source assertion when feasible.

## Core bridge failure semantics

Treat these as distinct startup failures:

```text
DEX asset missing/read failure
invalid DEX magic
class loader construction failure
entry class not found/linkage failure
bridge method lookup mismatch
inject exception
finalize/hook exception
```

Preserve the earliest exception. `JVM plugin is not loaded` is usually a later consequence,
not a sufficient root-cause report.

If the JVM backend is required for registered UI/actions, do not leave those actions active
after bridge load failure. Fail initialization explicitly or degrade only features proven to
be optional.

## Hooks in Kotlin/DEX

DEX is a good place for high-frequency or JVM-heavy Xposed hooks because it avoids repeated
Python/Java crossing in hot paths.

Rules:

- resolve the exact target member for the exact host version;
- register hooks during a controlled inject phase;
- retain unhook handles when the API provides them;
- unregister/eject on plugin unload;
- do not perform network/file I/O inside hot hook callbacks;
- bound caches and clear them on eject;
- catch/log failures at the hook boundary so one optional integration does not crash the whole
  app where graceful degradation is possible.

## Static state

Kotlin `object`, companion/static fields and hook-framework registrations can survive longer
than the Python object that caused them to exist.

On `eject` clear or invalidate:

- unhook handles;
- listener/observer registrations;
- callbacks into Python;
- static references to Activity/View/Fragment objects;
- caches of host objects;
- executor jobs/timers owned by the DEX layer;
- generation-specific state.

Avoid static references to Android UI objects unless there is a deliberate weak/lifecycle
strategy; they can leak entire activities.

## Python callback lifetime

If Kotlin stores a Python-created Java callback/proxy, define its lifetime. On reload an old
callback may point at an obsolete Python plugin object.

Safer pattern:

```text
inject(new callback)
-> mark generation active
...
eject()
-> unregister hooks
-> drop callback
-> invalidate generation
```

Never keep an old Python callback as a process-global fallback after eject.

## Kotlin errors

For startup, distinguish:

- DEX missing/corrupt;
- class not found;
- missing runtime dependency / `NoClassDefFoundError`;
- bridge method not found/signature mismatch;
- hook target missing;
- hook callback exception;
- host-version incompatibility.

Log enough detail to diagnose the layer. A generic `Failed to load plugin` is insufficient.

For optional host features, consider degrading only that feature. For a required core bridge
failure, fail plugin initialization rather than leaving half-registered state.

## Gradle/toolchain discipline

Use versions from the current repository and CI, including JDK and Android build-tools. Older
third-party DEX guides may name Java 17/SDK 35 or other combinations; do not copy those values
into this template without a reason.

Changes to:

- Kotlin version;
- Android Gradle Plugin/build tools;
- desugaring;
- D8/R8;
- relocation/shading;
- Java target;

can change runtime compatibility. Treat toolchain upgrades as engineering changes with a real
DEX build and device validation.

## DEX review checklist

- Host JAR generated from target APK?
- Current Gradle task used?
- Release/debug DEX path correct?
- DEX magic/content validated?
- EAF contains binary DEX once?
- Final DEX external/runtime type surface validated?
- Compile-only annotations absent unless intentionally runtime-provided?
- R8 warnings strict rather than globally suppressed?
- Relocated dependency rules translated where semantically required?
- Bridge class name stable/correct and present in final DEX?
- Exact Java method signatures synchronized?
- Hook targets verified against target host?
- No blocking work in hot hooks?
- Unhook/eject implemented?
- Static/callback references cleared?
- Real device class-load and Python → JVM callback test performed for release-critical changes?
