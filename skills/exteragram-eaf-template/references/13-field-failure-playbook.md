# Field-Tested Failure Playbook

Use this reference when an EAF/DEX plugin builds successfully but install, JVM loading,
callbacks, hooks, metadata, or release behavior is wrong. These rules are distilled from the
actual migration and on-device validation of this template and should be treated as regression
knowledge, not optional style advice.

## Start with the first failing layer

Never debug from the final symptom alone. Classify the earliest proven failure in this order:

```text
metadata / installer
-> archive/refmap
-> Python entry
-> DEX asset resolution
-> DEX bytes/magic
-> class loader / class linkage
-> bridge method lookup
-> JVM inject
-> Python UI registration
-> finalizeInject / hooks
-> feature callback
-> unload/reload
```

A later error is often only a consequence of an earlier one. Preserve the first exception and
its stage.

Example:

```text
cannot call invokeSettingsActionCallback: JVM plugin is not loaded
```

is a secondary symptom. It does not explain why the JVM plugin was not loaded. Search earlier
startup logs for DEX path/read, `loadClass`, linkage, or inject failure before editing the
callback.

Required core failures must stop initialization clearly. Do not leave settings/menu actions
registered if their required JVM backend failed to load.

## Installer says `Assets directory not found!`

A ZIP entry such as:

```text
assets/classes.dex
```

does not guarantee that the archive contains an explicit directory entry:

```text
assets/
```

Some Elyx installers validate declared refmap directories as real ZIP directory entries.
Therefore the builder should emit explicit `assets/` and `src/` entries and verify them with
`ZipInfo.is_dir()` or equivalent.

Regression checks should assert both:

```text
assets/
assets/classes.dex
```

and likewise `src/` when the refmap/layout declares it. Child paths alone are insufficient.

When writing deterministic ZIP entries, preserve directory semantics as well as the path name
(for example Unix directory mode and/or DOS directory bit where the builder controls them).

## Never assume Elyx defines `__file__`

Structured Elyx can execute `main.py` without defining Python `__file__`.

Do not make required asset loading depend only on:

```python
os.path.dirname(__file__)
```

Preferred normal asset access is the public Elyx asset facade, for example:

```python
from elyx import assets
raw = assets["classes.dex"].content_bytes()
```

If very-early bootstrap or bridge constraints require a filesystem path, use a documented
runtime helper deliberately. In the validated AyuGram layout this template can resolve from
an imported `file_utils.get_plugins_dir()` and the structured plugin id. Keep this path logic
centralized in the bridge; do not spread private install paths throughout feature code.

Do not write code such as:

```python
globals().get("get_plugins_dir")
```

unless the symbol is actually imported/defined. A fallback that cannot exist in the module is
not a fallback.

Asset diagnostics should log all attempted candidates and distinguish:

- runtime helper unavailable;
- candidate path does not exist;
- read failed;
- file empty;
- invalid DEX magic.

## Identity is a multi-surface contract

For this template, keep these identity surfaces synchronized unless deliberately changing the
architecture:

```text
metainfo.yml id
Python __id__
Kotlin/JVM Plugin.ID or equivalent
artifact name
installed Elyx directory assumption, if used by bootstrap
```

Structured Elyx ids use letters/digits/underscore only and must not inherit a legacy
hyphenated id blindly.

Version is also multi-surface while compatibility metadata remains:

```text
metainfo.yml version
Python __version__
pyproject.toml version
release tag/input when applicable
```

CI should reject id/version drift before expensive Gradle work.

Author is different: it is plugin-owned metadata, not a template invariant. Do not pin the
author to the template maintainer in CI. A template may provide a default author, but forks
must be able to change it without disabling tests.

## A clean R8 build does not prove DEX runtime linkage

A standalone plugin DEX can contain unresolved type references that compile and shrink but
fail when ART links the class on device.

A real failure from this template was a compile-only annotation descriptor retained in the
release DEX:

```text
Landroidx/annotation/AnyThread;
```

Compile-only annotations such as AndroidX/JetBrains/animal-sniffer markers are not guaranteed
to exist in the host class loader and usually have no runtime value for the plugin.

Broad retention such as:

```proguard
-keepattributes *Annotation*
```

can preserve CLASS-retention / runtime-invisible annotations. Prefer the minimum annotation
attributes actually needed at runtime, or strip compile-time markers before final DEX.

Add a DEX runtime-surface validator that compares defined classes with referenced type
descriptors and rejects unexpected unresolved packages. Keep the allowlist narrow and based on
known providers, for example Android/Java plus exact host-provided Telegram/extera/Xposed APIs.

Do not merely add every newly failing package to the allowlist. First decide whether it is:

- intentionally host-provided;
- an accidentally leaked compile-only type;
- a missing embedded runtime dependency;
- a relocation/shading bug.

## R8/shading rules learned from real failures

### Do not use broad `-ignorewarnings`

Broad suppression hides missing classes and stale rules that can become runtime crashes. Keep
R8 diagnostics strict and use a narrow `-dontwarn` only for a class proven to be an irrelevant
compile-time marker.

### Relocation changes consumer-rule semantics

Dependency JARs may ship `META-INF/com.android.tools/r8/` or `META-INF/proguard/` rules written
for original package names. After relocation those rules can become stale or misleading.

Do not blindly copy stale consumer rules into the merged relocated program input.

But do not simply delete semantically important rules either. Translate required rules to the
relocated namespace. One concrete example is kotlinx-coroutines volatile fields used with
field updaters, including `SafeContinuation`: if the runtime package is relocated, preserve the
same field-keeping semantics under the relocated package.

### R8 classpath and program input serve different purposes

Relocated library classes can be program input while original dependency JARs remain useful on
R8's classpath to resolve unrelocated references/signatures. If a missing class such as
`kotlin.Unit` appears after shading, inspect whether the original dependency disappeared from
the classpath before inventing a keep rule.

### dex2jar synthetic names can be inconsistent

A target host JAR produced by dex2jar may contain a sanitized class file such as:

```text
Foo_IA.class
```

while another class descriptor still points at:

```text
Foo-IA
```

Normalize this only when the exact sanitized candidate is known to exist. Do not globally
replace hyphens in arbitrary class names.

### Runtime surface validation belongs after real R8/D8

Validate the final release DEX, not only Kotlin bytecode or the pre-shaded JAR. The final DEX is
what ART loads.

## Host JARs are an ABI input, not just a compile convenience

`Telegram.jar` / `Telegram-compile.jar` must correspond to the app build being targeted.
Compile success against one AyuGram/exteraGram build does not prove runtime compatibility with
another.

For host updates:

1. record exact app/version/build;
2. derive JARs from the exact APK supplied/selected for that target;
3. repair/normalize the compile JAR using the repository tooling;
4. inspect touched host classes;
5. run real release DEX build;
6. run device tests for private hooks/bridge paths.

Do not silently follow an arbitrary `latest` APK in release CI.

Large generated host JARs may exceed GitHub's recommended blob size. Git LFS is useful only if
the actual repository/fork and CI can fetch the LFS objects reliably. A broken LFS pointer is
worse than a large ordinary blob. Whatever storage strategy is chosen, CI must prove the real
JAR bytes are present.

## Bridge loading must preserve the primary cause

A robust JVM bridge should log distinct stages:

```text
resolve DEX
read DEX
validate DEX magic
construct class loader
load JVM entry class
resolve bridge method
invoke inject
register Python UI
invoke finalizeInject
run feature callback
```

If `loadClass` fails, capture:

- exact JVM class name;
- DEX source/path;
- DEX size/version when safe;
- parent class loader choice;
- complete Java/Chaquopy cause.

If DEX resolution fails, do not continue into a callback and report only `JVM plugin is not
loaded`.

If the JVM backend is required, startup should fail as a required stage and expose a copyable
report. Optional integrations may degrade separately, but core bridge loading may not silently
half-load.

## Class loader assumptions

The validated template uses `InMemoryDexClassLoader` with the host/application class loader as
parent. This permits resolution of Android, Telegram/AyuGram and hook-framework classes from
the host.

Do not change the parent loader to fix an unrelated packaging problem. First prove the missing
type and its intended provider.

Keep the JVM entry class name stable through R8 or explicitly keep it. Confirm the class exists
in the final DEX before blaming the loader.

## Synthetic EAF smoke tests are intentionally incomplete

A tiny byte sequence beginning with `dex\n` can prove:

- builder wiring;
- binary archive transport;
- path/integrity assertions.

It cannot prove:

- Kotlin compilation;
- R8 relocation;
- DEX type linkage;
- JVM class loading;
- bridge reflection signatures;
- host ABI compatibility.

Report synthetic packaging and real Kotlin/DEX integration as separate gates.

## Green CI is not an on-device acceptance test

For architecture/runtime changes, the acceptance ladder should reach a real installed build:

```text
EAF installs
-> plugin appears with correct id/version/author
-> Python entry loads
-> DEX bytes resolve
-> JVM entry class loads
-> inject succeeds
-> finalizeInject succeeds
-> one Python -> JVM settings callback succeeds
-> one chat/menu callback succeeds when relevant
-> representative hook fires
-> disable/re-enable does not duplicate hooks
-> cold restart still works
```

A successful line such as:

```text
DEX:396E [Context Menu] Example clicked for <dialog-id>
```

is strong evidence that EAF installation, Python bridge, DEX loading, JVM injection and that
callback path are working. It still does not replace testing unrelated hooks/lifecycle paths
when those changed.

## Artifact availability is part of the test workflow

A manual release workflow does not make development builds downloadable automatically.
If device testing is part of development, successful full CI should publish the installable
`.eaf` as an Actions artifact (or another trusted channel) so the exact tested build can be
installed.

Do not tell a tester to use a build that cannot be tied back to a specific workflow/head.

For pull-request workflows, remember `github.sha` may refer to GitHub's synthetic merge commit.
If artifact naming must identify the source head, use the PR head SHA explicitly. Do not confuse
a merge-test SHA with the branch head when correlating runtime reports.

## Secrets and build delivery

Never commit bot tokens or deployment credentials into workflow YAML or repository files.
Use repository/environment secrets and scope them only to the publishing step.

For optional Telegram publication:

- missing secrets may cleanly skip publication if that is repository policy;
- once publishing is configured and expected, a failed send should fail the publication stage
  rather than reporting delivery success;
- untrusted fork PRs must not receive secrets;
- rotate any token that was pasted into an unsafe/shared context.

## Regression tests should encode the exact bug

When a real bug is fixed, add the smallest machine-verifiable invariant that would have caught
it before release.

Examples from this template:

- installer rejected assets directory -> assert explicit `assets/`/`src/` ZIP directory entries;
- invalid Elyx id -> negative-test a hyphenated id;
- Python/Elyx version drift -> compare metadata surfaces in CI;
- compile-only annotation leak -> validate final DEX runtime type surface;
- binary DEX accidentally embedded -> compare `main.py` source and `assets/classes.dex` bytes;
- R8 warning hidden -> fail CI on `Warning:` and unmatched ProGuard rules;
- development build unavailable -> upload the exact EAF artifact after full build.

Do not settle for a test that merely repeats the new implementation. Test the external
contract that was broken.

## Symptom lookup

| Symptom | First checks |
|---|---|
| `Assets directory not found!` | explicit `assets/` ZIP entry, refmap path, wrapper directory |
| plugin shows wrong version | `metainfo.yml`, Python `__version__`, release stamping, installed artifact freshness |
| plugin shows wrong author | `metainfo.yml`/Python metadata; verify CI is not pinning template author |
| `__file__ is unavailable` | remove required dependence on `__file__`; use Elyx assets/runtime helper |
| `DEX is unavailable` | asset resolver candidates, installed EAF contents, exact artifact installed |
| `JVM plugin is not loaded` | search earlier startup failure; do not debug callback first |
| `ClassNotFoundException` | entry class exists, R8 keep/relocation, correct packaged DEX |
| `NoClassDefFoundError` | final DEX unresolved type surface, host/embedded dependency provider |
| R8 missing `kotlin.*` | original dependency classpath after relocation |
| strange `Foo-IA` host type | dex2jar synthetic descriptor vs sanitized class filename |
| CI green but device fails | determine whether real DEX ran; inspect runtime-surface/device gates |
| artifact SHA/name confusing in PR | synthetic PR merge SHA vs PR head SHA |

## Agent pre-merge checklist for this template

Before saying a plugin change is ready, answer these explicitly when relevant:

- Which layer failed originally, and what was the first-cause error?
- Does every declared EAF directory exist as an actual archive entry?
- Are id/version surfaces synchronized? Is author intentionally free to change?
- Does required asset loading work when `__file__` is absent?
- Does the final release DEX have only expected external runtime types?
- Are R8 warnings strict rather than broadly suppressed?
- Were semantic shrinker rules translated after relocation rather than discarded?
- Are host JARs from the exact target build?
- Did real Gradle/R8/DEX run, not only synthetic packaging?
- Does CI belong to the exact current head?
- Can the exact EAF under test be downloaded/identified?
- For runtime changes, did at least one real Python -> JVM callback succeed on device?
- If lifecycle/hooks changed, was disable/re-enable/reload tested?

If any required answer is unknown, report the remaining gate instead of claiming completion.
