# Source Priority and Verification Rules

Use this file when sources disagree, an API appears undocumented, or a task targets a
specific exteraGram/AyuGram build.

## Authority order

For this template, use this order instead of treating every document as equally true.

### 1. Current repository state

For behavior implemented by this template, the checked-out code and CI are the first
source of truth. Read the current branch/PR, not only `master` and not a remembered
snapshot.

Examples:

- `tools/build_eaf.py` defines what the template actually packages today.
- `refmap.yml` defines the archive paths expected by this repository.
- `build.gradle.kts` defines the actual Kotlin/DEX toolchain and task names.
- `.github/workflows/*.yml` defines what CI and release really execute.
- the Python entry module defines the real JVM bridge and fallback logic.

If documentation in this skill conflicts with a newer repository implementation, update
the skill after verifying the change rather than forcing the code back to stale guidance.

### 2. Current official exteraGram plugin documentation

For public SDK and Elyx behavior, prefer the live documentation at
`https://plugins.exteragram.app/docs`.

This includes:

- `BasePlugin`, HookResult/HookStrategy and menu contracts;
- current SDK baseline and Python runtime;
- Elyx `refmap`, metadata, module isolation, assets and live reload;
- public `elyx` API;
- settings, client utilities, file utilities, reflection helpers and class proxy.

The live docs win over copied/mirrored documentation in third-party skills when the two
have drifted.

### 3. Exact target APK / decompiled target / matching source revision

For Telegram internals and private methods, documentation is not enough. Use the exact
host build whenever possible.

Preferred evidence:

1. classes and signatures extracted from the APK being targeted;
2. a decompile of that exact build;
3. a known matching source revision;
4. only then a nearby upstream Telegram revision as an approximation.

A method existing in upstream Telegram does not prove that exteraGram/AyuGram has the
same signature or behavior.

### 4. Working plugin examples and device observations

Real plugins are valuable for patterns the public docs do not cover well: custom Telegram
UI, unusual hooks, lifecycle workarounds and host-specific reflection behavior.

Useful material includes `corerudo/for-vibecoders` analyses and known working plugins.
Treat these as evidence tied to a version, not universal API documentation.

A device observation that contradicts docs should be recorded with:

- app version/build;
- plugin SDK version if known;
- architecture/device API level when relevant;
- exact failing call and exception;
- working fallback.

Do not rewrite general guidance around an unexplained single-device anomaly.

### 5. Synthesized third-party skills

The skills from `fossSquad/exteraSkill`, `makarworld/exteragram-plugin-skill` and
`faustyu1/exteragram-plugins-skill` are navigation aids and collections of patterns.
They are not authoritative by themselves.

Known characteristics:

- `fossSquad/exteraSkill`: broadest coverage, especially DEX, Telegram internals, UI and
  Elyx references. Some material is a mirror/snapshot and may age.
- `makarworld/exteragram-plugin-skill`: strong structure and practical public-SDK workflow.
- `faustyu1/exteragram-plugins-skill`: useful older examples, but it contains outdated or
  mutually incompatible claims; verify every nontrivial rule before adopting it.
- `corerudo/for-vibecoders`: not a replacement SDK spec; valuable as real-plugin case
  studies and explanations of why certain implementation choices worked.

## Resolve conflicts by domain

### Packaging conflict

Use current Elyx docs + this repository's packager. Legacy `.plugin` behavior does not
override `.eaf` rules.

Example: legacy top-level `__id__` documentation may allow `-`, while current Elyx
`metainfo.yml` requires only ASCII letters, digits and `_`. For the EAF artifact, obey the
Elyx rule.

### Reflection conflict

Use the exact runtime behavior and exact host classes. A helper returning a class-like
Chaquopy object on one SDK build does not guarantee it exposes Java reflection methods on
another build.

When necessary, feature-detect or use an explicit `java.lang.Class` path rather than
assuming one representation.

### Telegram internals conflict

Exact target decompile wins. If a working plugin uses a private field that no longer
exists, migrate the plugin; do not preserve the old field because a skill says so.

### Build-tool conflict

The installed Gradle/Android SDK/JDK configuration and repository tasks win. Do not copy
Java 17/SDK 35 instructions from an older DEX guide into a template that currently builds
with a different toolchain unless a compatibility test proves that change is intended.

## Verification before writing code

For public APIs, search the current docs when any of these are uncertain:

- symbol spelling;
- callback signature;
- enum values;
- version where the API appeared;
- metadata grammar;
- Elyx archive/runtime behavior.

For private/internal APIs, inspect source/decompile when any of these are uncertain:

- declaring class;
- overload and parameter types;
- constructor signature;
- static vs instance member;
- private field name/type;
- threading assumptions;
- lifecycle and ownership.

## Documentation policy for this skill

This skill intentionally contains original distilled guidance, not large copied passages
from source skills. When updating it:

- prefer paraphrase and small original examples;
- link the source in `SOURCES.md`;
- retain source/license notes;
- remove stale claims instead of preserving them for completeness;
- add version qualifiers to empirical workarounds.
