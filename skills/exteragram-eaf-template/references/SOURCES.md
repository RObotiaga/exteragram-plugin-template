# Sources and Provenance

This skill is an original synthesis tailored to `RObotiaga/exteragram-plugin-template`.
It is not a concatenation of the source skills below. Facts and patterns were compared,
rewritten and, for public SDK/Elyx behavior, checked against current official documentation.

## Primary authority

### Current exteraGram plugin documentation

- `https://plugins.exteragram.app/docs`
- Especially Elyx pages for project structure, metadata, modules/imports, assets,
  dependencies, development/live reload and public API.
- Use the live site when a copied reference or this skill becomes stale.

### Current template repository

- `https://github.com/RObotiaga/exteragram-plugin-template`
- The checked-out branch/PR is authoritative for actual file names, Gradle tasks, bridge
  implementation, EAF packager and CI/release behavior.

### Target app source/decompile

For Telegram/exteraGram/AyuGram internals, use the exact target APK/decompile/source revision
when possible. Private classes/methods are version-sensitive.

## Source skills / reference collections

### fossSquad/exteraSkill

Repository: `https://github.com/fossSquad/exteraSkill`

Useful for:

- broad navigation across BasePlugin, DEX, Elyx and Telegram internals;
- copied/curated Elyx documentation references;
- large references for `ChatActivity`, `MessageObject`, `MessagesController`,
  `SendMessagesHelper`, TLRPC and UI components;
- DEX build/loading concepts;
- debugging and utility API navigation.

License observed in repository: **GPL-3.0**.

This skill does not copy its large reference files or source examples wholesale. Treat its
API snapshots as potentially stale relative to the live docs.

### makarworld/exteragram-plugin-skill

Repository: `https://github.com/makarworld/exteragram-plugin-skill`

Useful for:

- concise BasePlugin/public SDK structure;
- multi-account rules;
- Elyx overview;
- development workflow and common mistakes;
- organized references for settings, helpers, hooks and repo conventions.

License observed in repository: **MIT**.

### faustyu1/exteragram-plugins-skill

Repository: `https://github.com/faustyu1/exteragram-plugins-skill`

Useful as:

- an older broad SDK/example reference;
- a source of topics to verify elsewhere.

Caution:

- it targets an older SDK snapshot;
- the same document contains mutually incompatible statements about `.plugin` being plain
  text versus a ZIP plugin layout;
- no separate license file was observed during synthesis.

Therefore no nontrivial rule from this source should be adopted without verification against
current docs/repository/runtime.

### corerudo/for-vibecoders

Repository: `https://github.com/corerudo/for-vibecoders`

Useful for:

- analyses of real working plugins rather than only API summaries;
- practical hook/reflection failure modes;
- before-vs-after reasoning;
- high-frequency event deduplication;
- bounded resource caches;
- exact cleanup/unhook patterns;
- account/background-work/media/UI examples;
- empirical discrepancies between documented wrappers and particular app builds.

License observed in repository: **Apache-2.0**.

Treat every private Telegram class/field/method in those analyses as version-specific until
verified against the target host.

## Important distilled lessons from cross-source comparison

These are principles, not copied text:

1. Public SDK behavior should come from live exteraGram documentation.
2. Private Telegram behavior should come from exact host source/decompile and working runtime
   evidence.
3. EAF is a structured ZIP-compatible format and should not inherit legacy `.plugin`
   assumptions.
4. The canonical template should keep DEX binary as `assets/classes.dex` rather than expanding
   it into Python source.
5. High-level TL hooks and arbitrary Java/Xposed hooks are separate APIs.
6. Account context must follow the hook event through asynchronous work.
7. Hot hooks need bounded work, cached reflection and no blocking I/O.
8. Every persistent hook/listener/thread/callback/cache needs explicit reload cleanup.
9. Real-plugin analyses are strongest when used to learn *why* a pattern works, then re-check
   exact private members for the current host.
10. A green packaging smoke test is not a real Kotlin/DEX integration test when host JARs are
    absent.

## Updating this skill

When refreshing the skill:

1. resolve current template HEAD;
2. check live official docs for changed SDK/Elyx contracts;
3. inspect upstream skill/repo changes only for relevant new material;
4. verify private API claims against a target build;
5. update the smallest topical reference file;
6. keep `SKILL.md` as a router rather than growing it into a monolith;
7. preserve source/license notes;
8. add/remove pitfalls when CI/device evidence changes.

## Copyright / copying policy

Prefer original explanations and newly written minimal examples. Do not import entire third-party
reference files into this skill merely for completeness. Link to external material when a large
class/reference index is more useful at its source.
