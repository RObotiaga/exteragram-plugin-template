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
  -> R8/D8 release classes.dex
  -> final-Dex runtime-surface validation
  -> deterministic EAF packager
  -> <plugin-id>.eaf
  -> archive validation
  -> device/runtime gate when architecture changed
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

For reproducibility, prefer an explicitly supplied/pinned target APK over silently downloading
whatever is currently called `latest`.

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
- explicit declared directory entries (`assets/`, `src/`, etc.) where Elyx expects them;
- Python AST validation;
- duplicate/path traversal rejection;
- `refmap` validation;
- DEX magic/content validation;
- atomic write via temporary output;
- ZIP integrity check before replacing final artifact.

Do not put an extra root folder inside the archive.

A child entry such as `assets/classes.dex` is not equivalent to an explicit `assets/` ZIP
directory entry for every installer. CI should test the exact directory contract that caused
real installation failures.

## Generated DEX path

The Gradle task defines the actual DEX output. Do not duplicate a hard-coded path in several
scripts without tests.

If a path changes:

- update `justfile`;
- update CI;
- update Release workflow;
- update local docs/skill;
- add failure messages that say which path was expected.

Runtime asset resolution is a different contract from build-output location. Do not infer the
installed Elyx path from the repository Gradle path, and do not assume runtime `__file__` exists.

## CI layers

A strong CI separates always-available checks from host-JAR-dependent integration.

### Always run

- Python tooling syntax/compile checks;
- resolve plugin entry/id;
- validate synchronized id/version surfaces;
- build EAF using a controlled synthetic DEX;
- assert archive layout/integrity;
- assert explicit declared ZIP directory entries;
- assert `assets/classes.dex` bytes;
- assert EAF `main.py` is not DEX-expanded;
- check `refmap`/metadata invariants.

Author should remain freely changeable by forks; do not fail CI because it differs from the
template author's default.

### Run when host JARs are available

- Java/JDK/Android SDK setup;
- real Gradle release DEX build;
- strict R8 diagnostics;
- final release DEX runtime-surface validation;
- package the real DEX;
- run the same archive checks on the real artifact;
- upload/publish the exact installable EAF used for device testing.

A skipped real-Dex stage should emit a clear notice, not disappear silently.

## Final-Dex validation is a separate gate

A warning-free R8 build is not enough for an independently loaded DEX. CI should validate
unexpected unresolved type descriptors in the final release `classes.dex`.

This catches classes that compiled only because they existed on compile classpath, including
compile-only annotations accidentally preserved in runtime metadata.

Keep the unresolved-type allowlist narrow. Unexpected packages must be classified before they
are accepted as host-provided.

## R8 diagnostics must stay meaningful

Do not add broad `-ignorewarnings` to turn CI green. Treat missing-class warnings and unmatched
ProGuard rules as failures when that is the repository's policy.

When dependencies are relocated:

- strip stale packaged consumer rules whose original package names no longer match;
- translate semantically required rules to relocated namespaces rather than dropping them;
- keep original dependency JARs on R8 classpath when they are needed to resolve original
  signatures;
- use narrow `-dontwarn` only for a proven irrelevant compile-time marker.

## CI should fail on invalid structured ids

The EAF metadata validator should reject ids outside the structured Elyx grammar:

```text
2–32 chars; ASCII letters/digits/_ only
```

This is a useful template-specific regression guard because legacy metadata accepts a wider
set on some plugin paths.

Also compare identity surfaces used by the template (for example `metainfo.id`, Python
`__id__`, and JVM static id when applicable) so a rename cannot partially succeed.

## Host JAR storage strategy

If JARs are committed:

- use Git LFS only if the repository/fork reliably carries the LFS objects;
- ensure CI checkout actually restores them;
- record how they were generated and from which APK/version;
- verify CI sees real JAR/ZIP bytes rather than an LFS pointer or missing object.

If JARs are generated in CI:

- obtain the APK from a trusted/pinned source;
- pin version/checksum;
- cache derived JARs if useful;
- avoid silently following `latest` for release reproducibility.

Do not download arbitrary unofficial host binaries in a privileged release workflow.

## Development artifact availability

A manual Release workflow is not a substitute for making development builds testable.

If device testing is part of the workflow, successful full CI should upload the exact `.eaf`
as an Actions artifact or publish it through another trusted channel. The tester must be able
to identify the artifact by workflow run and source head.

Do not claim "the plugin is ready to test" if the exact build cannot be downloaded or
correlated to its source revision.

For `pull_request` workflows, `github.sha` may refer to GitHub's synthetic merge commit rather
than the PR branch head. If artifact names/messages need the source head, use
`github.event.pull_request.head.sha` (or equivalent explicit logic) rather than assuming
`github.sha` means the developer commit.

## Optional Telegram build publication

Telegram publication is useful for rapid device testing, but keep it downstream of the full
build/validation gates.

Rules:

- credentials only from GitHub Actions/environment secrets;
- never commit a bot token/chat credential into workflow YAML;
- untrusted fork PRs must not receive secrets;
- missing secrets may cleanly disable optional publication if repository policy allows it;
- when publication is configured and expected, a Telegram API failure should fail that publish
  stage rather than pretending delivery succeeded;
- publish the same EAF bytes that CI validated, not a separately rebuilt copy.

Rotate a token if it was pasted into an unsafe/shared context.

## Release metadata

The release script/workflow should update every metadata surface still supported.

For structured EAF:

- `metainfo.yml` version is canonical.

While legacy compatibility remains:

- top-level Python `__version__` may also need synchronization.

Project packaging metadata such as `pyproject.toml` can be synchronized if the repository uses
it as a version source/tooling contract.

After stamping, verify the values agree before building the release.

Do not make `author` equality to the template default part of release validation. A fork is
supposed to be able to change the author independently.

## Release version input

Validate release version input before doing expensive build work. If the repository supports
only `x.y.z`, enforce that explicitly. If prereleases become supported, update both parser and
metadata tests rather than weakening validation ad hoc.

## Release workflow ordering

Recommended order:

1. checkout exact ref with required history/JAR inputs;
2. validate requested version;
3. resolve/synchronize plugin id/source metadata;
4. verify required host inputs;
5. set up JDK/Android/Python;
6. stamp metadata;
7. build release DEX;
8. run strict R8/final-Dex runtime-surface validation;
9. package EAF;
10. inspect/validate archive including explicit directory entries;
11. install/device-test when architecture/runtime changed;
12. attest artifact;
13. commit release metadata if repository policy requires it;
14. tag exact commit;
15. publish release with the exact attested EAF.

Do not tag/publish before artifact validation succeeds.

## Provenance

If GitHub build provenance attestation is enabled, the attested subject must be the exact
`.eaf` uploaded to the release.

Avoid modifying/repacking the artifact after attestation.

The same principle applies to runtime testing: if a device test validates artifact A, do not
quietly rebuild artifact B and describe the device result as proof for B.

## Revision safety

For implementation or review tasks, resolve current base/head first.

Before merge/release:

- compare branch against intended base;
- ensure it is not unexpectedly behind;
- ensure CI result belongs to current head, not an older commit;
- distinguish PR head SHA from synthetic merge-test SHA;
- if a revision gate is specified, compare exact SHA character-for-character.

Never report a previous green run as proof for a newer head.

## CI changes require tests of the test

When editing workflow conditions, inspect the resulting run steps. A YAML-valid workflow can
still skip the important build because of a bad condition/output.

If a required stage is unexpectedly skipped, treat that as a CI bug even when the job is green.

When adding a regression gate, prefer evidence that it would reject the old broken state where
practical.

## Artifact validation script

Prefer one reusable validation function/script over duplicated snippets in CI and Release when
the checks grow substantial. It should be callable locally.

Potential checks:

```text
archive extension
zip integrity
required entries
explicit declared directory entries + directory semantics
no duplicate entries
no absolute/traversal paths
no wrapper dir
metainfo/refmap parse
structured id grammar
identity/version synchronization
main.py syntax
local module syntax
assets/classes.dex magic
DEX bytes match expected build input when provided
final-Dex runtime type surface (for real release DEX)
legacy embedded markers absent/payload empty in EAF main
```

## Release checklist

- Current HEAD/base confirmed?
- Required host JARs exact and available as real bytes?
- Release DEX built, not synthetic?
- R8 diagnostics strict/clean?
- Final-Dex runtime type surface green?
- EAF validator green, including explicit declared directories?
- Structured id valid and identity surfaces synchronized?
- Metadata versions synchronized? Author still freely changeable?
- Required Elyx asset bootstrap independent of `__file__`?
- Exact CI/device artifact identifiable and downloadable?
- No secrets/local logs/caches in archive?
- Device install/load + Python → JVM callback performed for architecture changes?
- Reload/disable tested if lifecycle/hooks changed?
- Attestation subject equals uploaded EAF?
- Tag points to metadata/artifact source commit?
- Release contains `.eaf`, not stale `.plugin` artifact?
