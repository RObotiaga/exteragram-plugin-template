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

## Exact reflection types

Python reflection into JVM methods must specify Java parameter types exactly where required.
A Python `int` is not a sufficient description of whether Java expects `int`, `long`, boxed
`Integer`, boxed `Long`, etc.

When changing a bridge signature, change and review both sides in one patch. Add a smoke check
or explicit source assertion when feasible.

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
- Bridge class name stable/correct?
- Exact Java method signatures synchronized?
- Hook targets verified against target host?
- No blocking work in hot hooks?
- Unhook/eject implemented?
- Static/callback references cleared?
- Real device class-load test performed for release-critical changes?
