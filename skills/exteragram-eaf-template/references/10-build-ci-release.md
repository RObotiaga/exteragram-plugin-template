# Build, CI and Release Workflow

Use this reference for local `just` commands, host JAR preparation, EAF packaging, GitHub
Actions and releases.

Always read the current `justfile`, `build.gradle.kts`, `tools/build_eaf.py` and workflows
before changing command names or paths.

## Current build stages

Conceptual release path:

```text
target APK
  -> Telegram.jar / Telegram-compile.jar
  -> Gradle Kotlin build
  -> release classes.dex
  -> deterministic EAF packager
  -> <plugin-id>.eaf
  -> archive validation
  -> provenance attestation
  -> Git tag + GitHub Release
```

Python-only development should not require running every stage unless integration needs it.

## `just` command intent

The current template exposes commands along these lines. Confirm names in the actual branch.

### `just update-apk <apk>`

Generate/update host JARs from the target exteraGram/AyuGram APK.

Use when:

- starting on a clean clone without `libs/Telegram*.jar`;
- changing target host version;
- compile errors suggest host classes no longer match.

After generation, inspect what the command commits/copies. Do not accidentally treat generated
host JARs from one app build as universal.

### `just dex`

Build debug DEX for development.

### `just ci`

Build release DEX or perform the repository's release-oriented Gradle step. Read the recipe;
its exact side effects can evolve.

### `just eaf`

Package an already-built DEX with Python/refmap/metainfo/assets into `.eaf`.

This should not rebuild Kotlin if the DEX input already exists.

### `just build`

Full release build: Kotlin/DEX followed by EAF packaging.

### `just embed`

Legacy compatibility output where DEX is embedded into a single Python artifact. Treat this as
legacy while the repository says so.

### `just watch`

Do not assume the existing watcher is structured Elyx live reload. The template may still use
a legacy single-file development path. Verify before documenting or extending it.

## Deterministic EAF packaging

The custom builder is preferable to a generic `zip` command when it enforces template-specific
invariants.

Good properties:

- stable archive ordering;
- fixed timestamps/metadata where practical;
- explicit archive paths;
- Python AST validation;
- duplicate/path traversal rejection;
- `refmap` validation;
- DEX magic/content validation;
- atomic write via temporary output;
- ZIP integrity check before replacing final artifact.

Do not put an extra root folder inside the archive.

## Generated DEX path

The Gradle task defines the actual DEX output. Do not duplicate a hard-coded path in several
scripts without tests.

If a path changes:

- update `justfile`;
- update CI;
- update Release workflow;
- update local docs/skill;
- add failure messages that say which path was expected.

## CI layers

A strong CI separates always-available checks from host-JAR-dependent integration.

### Always run

- Python tooling syntax/compile checks;
- resolve plugin entry/id;
- build EAF using a controlled synthetic DEX;
- assert archive layout/integrity;
- assert `assets/classes.dex` bytes;
- assert EAF `main.py` is not DEX-expanded;
- check `refmap`/metadata invariants.

### Run when host JARs are available

- Java/JDK/Android SDK setup;
- real Gradle release DEX build;
- package the real DEX;
- run the same archive checks on the real artifact.

A skipped real-Dex stage should emit a clear notice, not disappear silently.

## CI should fail on invalid structured ids

The EAF metadata validator should reject ids outside the structured Elyx grammar:

```text
2–32 chars; ASCII letters/digits/_ only
```

This is a useful template-specific regression guard because legacy metadata accepts a wider
set on some plugin paths.

## Host JAR storage strategy

If JARs are committed:

- use Git LFS only if the repository/fork reliably carries the LFS objects;
- ensure CI checkout actually restores them;
- record how they were generated and from which APK/version.

If JARs are generated in CI:

- obtain the APK from a trusted/pinned source;
- pin version/checksum;
- cache derived JARs if useful;
- avoid silently following `latest` for release reproducibility.

Do not download arbitrary unofficial host binaries in a privileged release workflow.

## Release metadata

The release script/workflow should update every metadata surface still supported.

For structured EAF:

- `metainfo.yml` version is canonical.

While legacy compatibility remains:

- top-level Python `__version__` may also need synchronization.

Project packaging metadata such as `pyproject.toml` can be synchronized if the repository uses
it as a version source/tooling contract.

After stamping, verify the values agree before building the release.

## Release version input

Validate release version input before doing expensive build work. If the repository supports
only `x.y.z`, enforce that explicitly. If prereleases become supported, update both parser and
metadata tests rather than weakening validation ad hoc.

## Release workflow ordering

Recommended order:

1. checkout exact ref with required history/LFS;
2. validate requested version;
3. resolve plugin id/source;
4. verify required host inputs;
5. set up JDK/Android/Python;
6. stamp metadata;
7. build release DEX;
8. package EAF;
9. inspect/validate artifact;
10. attest artifact;
11. commit release metadata if repository policy requires it;
12. tag exact commit;
13. publish release with exact EAF.

Do not tag/publish before artifact validation succeeds.

## Provenance

If GitHub build provenance attestation is enabled, the attested subject must be the exact
`.eaf` uploaded to the release.

Avoid modifying/repacking the artifact after attestation.

## Revision safety

For implementation or review tasks, resolve current base/head first.

Before merge/release:

- compare branch against intended base;
- ensure it is not unexpectedly behind;
- ensure CI result belongs to current head, not an older commit;
- if a revision gate is specified, compare exact SHA character-for-character.

Never report a previous green run as proof for a newer head.

## CI changes require tests of the test

When editing workflow conditions, inspect the resulting run steps. A YAML-valid workflow can
still skip the important build because of a bad condition/output.

If a required stage is unexpectedly skipped, treat that as a CI bug even when the job is green.

## Artifact validation script

Prefer one reusable validation function/script over duplicated snippets in CI and Release when
the checks grow substantial. It should be callable locally.

Potential checks:

```text
archive extension
zip integrity
required entries
no duplicate entries
no absolute/traversal paths
no wrapper dir
metainfo/refmap parse
structured id grammar
main.py syntax
local module syntax
assets/classes.dex magic
DEX bytes match expected build input when provided
legacy embedded markers absent/payload empty in EAF main
```

## Release checklist

- Current HEAD/base confirmed?
- Required host JARs exact and available?
- Release DEX built, not synthetic?
- EAF validator green?
- Structured id valid?
- Metadata versions synchronized?
- No secrets/local logs/caches in archive?
- Device install/load test performed for architecture changes?
- Attestation subject equals uploaded EAF?
- Tag points to metadata/artifact source commit?
- Release contains `.eaf`, not stale `.plugin` artifact?
