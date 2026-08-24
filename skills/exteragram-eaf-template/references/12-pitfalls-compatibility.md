# Pitfalls and Compatibility Hazards

Use this reference when reviewing a change, migrating old plugin code, or resolving conflicting
examples from third-party skills.

## 1. Legacy `.plugin` rules are not EAF rules

Do not apply single-file assumptions to structured Elyx.

Legacy path may use:

```text
one Python source
+ top-level dunder metadata
+ optional embedded DEX compatibility payload
```

Structured EAF uses:

```text
refmap.yml
metainfo.yml
main.py
modules/assets/strings/wheels
```

A statement such as “plugins are always one plain `.plugin` file” is obsolete for Elyx/EAF.
Likewise, an old ZIP trick for `.plugin` is not a substitute for current Elyx packaging.

## 2. Structured id grammar is stricter

Current Elyx `metainfo.yml` ids accept only ASCII letters, digits and `_`, length 2–32.
Hyphen is invalid.

Some legacy plugin docs/examples allow `-`. Keep validators separate while dual-format support
exists.

Template consequence: any current hyphenated `metainfo.yml` id or init regex that accepts
hyphen is a release blocker for the EAF path until corrected.

## 3. Python version confusion

Current plugin runtime is Python 3.11. A repository may use a newer desktop Python for tooling,
but compiled plugin bytecode must match runtime Python 3.11.

Source `.py` avoids this bytecode-version trap.

Do not infer device runtime from `.python-version` or CI setup without checking official docs.

## 4. Old SDK version snapshots

Third-party skills may pin SDK versions such as 1.4.3.6 or 1.4.4.3. Public API behavior and
minimum versions can move.

Verify live docs for:

- callback signatures;
- menu types;
- Elyx minimum SDK;
- multi-account APIs;
- metadata keys;
- helper availability.

Do not rewrite a modern template to an older snapshot merely because the example is detailed.

## 5. `find_class` representation differences

Some documented examples treat `find_class(...)` as directly usable for Java reflection.
Real-device analyses have observed builds where the returned Chaquopy wrapper did not expose
`getDeclaredMethod` as expected.

Treat this as a version/build compatibility issue, not proof that docs are universally wrong.
Feature-detect or use an explicit verified `java.lang.Class` path for affected hosts.

## 6. `add_hook` is not `hook_method`

Frequent hallucination:

```text
add_hook(JavaClass, "method", callback)
```

The high-level `add_hook` API is for Telegram request/update names. Arbitrary Java methods use
Xposed-style `hook_method`/constructor APIs.

## 7. Method name without overload is incomplete

For reflection, `"setChecked"` or `"createActionBarMenu"` alone is not a contract.

Always identify exact parameter types. Host upgrades often keep the name but change/add an
overload.

## 8. Upstream Telegram is not the target fork

A method in DrKLO/Telegram can differ in exteraGram/AyuGram due to:

- different revision;
- fork patches;
- backports;
- renamed/added fields;
- obfuscation/transformation.

Use upstream for architecture, exact target decompile for hooks.

## 9. Compile-time host JAR mismatch

A plugin can compile against JAR from build A and run on build B, then fail only at runtime.
Regenerate host JARs when target APK changes.

Record host build provenance for release-critical JARs.

## 10. Green CI can be partial CI

If `Telegram.jar` inputs are absent, CI may deliberately skip Gradle/real DEX while still
passing EAF smoke tests.

Always report:

```text
packaging smoke: pass/fail
real Kotlin/DEX: pass/fail/skipped
```

Never claim full integration from a synthetic-Dex-only run.

## 11. EAF smoke DEX is not a real DEX integration test

A tiny synthetic payload with `dex\n` magic proves archive wiring, not class loading.
A release requires real Gradle/D8 output and device validation for DEX changes.

## 12. Encoded DEX is legacy transport

Hex/base64 expansion:

- increases source/artifact size;
- makes Python source noisy;
- couples Python edits to binary transport;
- can increase parsing/memory overhead.

For this template's EAF path use binary `assets/classes.dex`. Keep encoded DEX only while a
legacy single-file artifact is intentionally supported.

## 13. Private Elyx install paths are runtime details

Official docs describe an installed directory layout, but plugin code should prefer public
`elyx` environment/assets APIs and normal imports.

The template may resolve `classes.dex` relative to `main.py` during bootstrap; treat that as a
specific bridge implementation, not permission to hard-code global Elyx storage paths
throughout the plugin.

## 14. Asset tree is read-only content

Do not write mutable settings/cache/database files under installed `assets/`. Use supported
data/cache locations.

## 15. Local module shadowing

Avoid modules named like `json.py`, `typing.py`, `java.py`, `elyx.py`, `ui.py`, `org.py`,
`base_plugin.py`, etc.

Elyx isolation protects plugins from each other, not from confusing imports inside one plugin.

## 16. Blocking work in hook/UI callback

Network, disk, HTML parsing, media processing and heavy reflection inside UI/hot hook callbacks
cause freezes/jank.

Move work to background queue and return minimal result quickly.

## 17. UI work from background thread

Android View mutation from a worker is unsafe. Move only the final UI operation to main thread.

## 18. Wrong Telegram account

Hooks can fire for background accounts. Using selected-account helpers inside the callback can
send/read on the wrong account.

Carry callback `account` through every async operation.

## 19. Recycler/cell hooks accumulate state

Message/UI cells are reused. If plugin only adds/modifies on matching item and never resets on
non-matching rebind, stale UI leaks into other items.

Every bind must derive full plugin-visible state from current model.

## 20. Global hook replacement leaks

Installing a temporary `MethodReplacement` without `finally` can leave the host globally
modified until restart.

Retain handle and always unhook.

## 21. Old reload generation still alive

Elyx reload clears Python modules but cannot magically remove:

- JVM static callbacks;
- Xposed hooks;
- worker threads;
- observers/listeners;
- sockets;
- strong View references.

Implement explicit eject/unload on both Python and Kotlin sides.

## 22. Deleting upload file too early

A send helper can enqueue asynchronous work and return before uploader reopens/finishes file.
Verify ownership before deletion. A `finally` after enqueue is not automatically correct.

## 23. Broad security/URI bypasses

A workaround that disables a Telegram path/URI safety check globally can affect unrelated
features. Prefer supported paths/APIs. If a verified temporary bypass is unavoidable, scope it
to one operation and restore in `finally`.

## 24. TLRPC flags guessed from examples

Optional TLRPC fields often require corresponding bit flags. Flags differ by generated class
revision.

Inspect target generated class/schema; do not copy bit masks blindly from another plugin.

## 25. Application context used for themed UI

`ApplicationLoader.applicationContext` is useful for process services/class loading but may be
wrong for Activity/theme-bound dialogs/components.

Resolve visible Fragment/Activity context when needed and handle absence.

## 26. Copying real-plugin hacks as general APIs

Patterns from `for-vibecoders` are valuable because they explain why a solution worked, but
host-specific details (private fields, shader strings, exact menu methods, magic markers) are
not universal SDK contracts.

Extract the principle, then re-verify exact host implementation.

## 27. Licensing by compilation

Do not concatenate third-party skill documents into this repository verbatim.

Source licensing differs (GPL-3.0, MIT, Apache-2.0, and unclear/unlicensed material). Write an
original synthesis, attribute sources, and copy code/text only when license and need are clear.

## 28. Stale PR/CI revision

Before reporting or merging, verify the CI run belongs to current head SHA. A green older run
is not evidence for a newer commit.

## 29. Release artifact rebuilt after attestation

If provenance attests one `.eaf` and release uploads a repacked/modified one, provenance no
longer describes the published bytes.

Attest the final validated artifact and do not modify it afterward.

## 30. Silent graceful degradation of required core

Optional feature hook can disable itself when target member is absent. Core bridge/DEX load
cannot silently fail while plugin claims to be loaded.

Classify dependencies as required vs optional and make failure state explicit.

## Compatibility review questions

Before supporting a second host version ask:

- Which public SDK behavior differs?
- Which Telegram classes/methods differ?
- Which bridge signatures differ?
- Can differences be probed safely at runtime?
- Is branching complexity cheaper than raising minimum version?
- Do both variants have device tests?

Avoid accumulating untested fallback signatures indefinitely.
