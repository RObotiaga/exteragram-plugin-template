# Elyx / EAF Structured Plugins

Use this reference for archive layout, `refmap.yml`, `metainfo.yml`, local modules,
assets, settings, localization, dependencies and structured live reload.

Current official docs are authoritative: `https://plugins.exteragram.app/docs/elyx`.

## Core model

Elyx is a structured plugin format. An installable `.eaf`/`.elyx` file is ZIP-compatible
and contains the plugin project itself. The archive root must contain a discoverable
`refmap.yml`/`refmap.yaml`/`refmap.json` or a supported default layout.

The archive must not add a wrapper directory above `refmap.yml`.

Correct:

```text
plugin.eaf
├── refmap.yml
├── metainfo.yml
├── main.py
├── assets/
└── src/
```

Incorrect:

```text
plugin.eaf
└── plugin/
    ├── refmap.yml
    └── main.py
```

For strict installers, directory names in this diagram are not merely conceptual. If refmap
or the layout declares `assets`/`src`, emit actual ZIP directory entries (`assets/`, `src/`)
in addition to their children. A child such as `assets/classes.dex` does not guarantee that a
strict ZIP consumer sees a real `assets/` directory entry.

## `refmap.yml`

Use YAML unless the project has a reason to choose another supported format.

Template-oriented example:

```yaml
metainfo: metainfo.yml
main: main.py
assets: assets
```

If a separate strings directory is added:

```yaml
strings: strings
```

If bundled wheels are intentionally shipped:

```yaml
wheels: wheels
```

Every explicitly declared directory/path must exist in the produced archive. When changing
paths, update the builder, tests and `refmap` together.

For declared directories, validate both the path and directory semantics where the installer
is strict. Regression checks should be able to distinguish `assets/` from merely having an
`assets/foo` child.

## `metainfo.yml`

Structured plugins should keep metadata outside `main.py`.

Recommended baseline:

```yaml
id: my_plugin
name: My Plugin
description: "Plugin description"
author: "@author"
version: "1.0.0"
app_version: ">=12.5.1"
sdk_version: ">=1.4.5.3"
requirements: ""
```

Important current EAF rule:

- `id` length: 2–32;
- characters: ASCII letters, digits and `_` only;
- keep it stable across upgrades;
- hyphenated ids are invalid for structured Elyx metadata.

This is stricter than some legacy single-file metadata rules. Do not collapse the two rules
into one regex while dual-format compatibility exists.

Quote version/constraint values in YAML.

When the template still carries legacy Python metadata and JVM static identity, treat identity
as a synchronized contract. `metainfo.id`, Python `__id__`, JVM `Plugin.ID`/equivalent and
artifact naming should not drift accidentally.

Version surfaces should also agree while they are all supported. By contrast, author is
plugin-owned metadata: provide a template default if desired, but do not make a particular
template author a CI invariant.

## Entry module

`main` points to the Python entry module. It must expose at least one `BasePlugin` subclass.
Only the first discovered plugin subclass is instantiated, so keep one deliberate entry
class and put helpers elsewhere.

Avoid large side effects at module import. Persistent resources belong in
`on_plugin_load`/`on_plugin_unload` ownership.

Do not assume the Elyx runtime defines Python `__file__` for `main.py`. Required bootstrap
logic must be able to operate without it.

## Local modules and isolation

Each Elyx plugin receives its own internal namespace, preventing two installed plugins with
same-named helper modules from sharing `sys.modules` entries.

Normal local imports work. For example, if EAF contains:

```text
main.py
src/
├── __init__.py
├── bridge_helpers.py
└── features/
    ├── __init__.py
    └── preview.py
```

then `main.py` may import:

```python
from src.bridge_helpers import helper
from src.features.preview import PreviewFeature
```

If you compute a module name dynamically, use `elyx.import_module` rather than plain
`importlib.import_module`, because the Elyx helper preserves plugin-local resolution.

Add `__init__.py` even where namespace directories are supported when it improves desktop
analysis/tooling consistency.

Do not shadow SDK/Java/stdlib roots such as:

- `base_plugin`, `client_utils`, `hook_utils`, `elyx`, `ui`;
- `android`, `androidx`, `java`, `org`, `com`, `de`;
- common stdlib names such as `json`, `pathlib`, `typing`.

## Assets

Declare/discover an asset root and prefer the public plugin-bound facade:

```python
from elyx import assets
raw = assets["classes.dex"].content_bytes()
```

Useful asset properties/methods include resolved `path`, `path_str`, `java_file`,
`content_bytes()`, `content_string()`, JSON/YAML readers and image/SVG/Lottie conversion.

Bundled assets are read-only from the plugin's point of view. Store mutable runtime data in
plugin/app data or cache locations, not inside the installed asset tree.

For this template:

- `assets/classes.dex` is generated during packaging;
- the EAF builder must ensure the DEX bytes are exactly the selected input;
- project assets may also be copied under `assets/`;
- a source file must not silently overwrite generated `classes.dex`;
- required DEX loading must not rely solely on `__file__`.

If an early bootstrap path cannot use the asset facade, use a documented/imported runtime
helper deliberately and centralize private install-layout knowledge in the bridge. Do not use
an unimported `globals().get("get_plugins_dir")` as a pretend fallback.

## Strings/localization

When user-facing text grows beyond a tiny plugin, prefer Elyx localization over large
language dictionaries embedded in `main.py`.

General rules:

- keep English as a reliable fallback;
- use stable semantic keys;
- test missing-key behavior;
- keep metadata description localization compatible with `metainfo` placeholders if used;
- do not make core startup depend on a nonessential locale file without graceful fallback.

## Settings

Elyx exposes a plugin-bound settings controller. `BasePlugin` settings helpers also exist.
Choose one consistent access style within a feature rather than maintaining duplicate stores.

Settings are mutable user data; assets are not.

## Dependencies

Pure-Python dependencies can be declared through plugin metadata. Binary extension wheels are
not generally available through the normal plugin PIP path.

Bundled wheels are a distinct Elyx mechanism. Use them only when the runtime/ABI is known and
when the package is suitable for the target environment.

Never put secrets in dependencies, assets or compiled Python and assume packaging hides them.
`.pyc` is not a security boundary.

## Python version

Current plugin runtime is Python 3.11. Source `.py` is portable across compatible runtime
patches, but `.pyc` is version-specific. Any compiled Elyx Python release must be built with
Python 3.11 matching the device runtime magic.

The template currently favors source Python in EAF; preserve that unless compiled bytecode is
an explicit requirement.

## Build options

ElyxBuilder is optional. A custom deterministic ZIP builder is valid when it obeys the
structured archive contract.

For this template, prefer `tools/build_eaf.py` because it can also enforce template-specific
DEX and path invariants.

A good builder should verify:

- required files exist and are non-empty;
- Python files parse;
- no absolute/traversal paths;
- no duplicate archive entries;
- required `refmap` paths resolve;
- declared directories exist as explicit directory entries when required by the installer;
- `assets/classes.dex` has DEX magic and matches build input;
- ZIP integrity succeeds;
- repeated builds with identical inputs are deterministic where practical.

When writing directory entries manually, set directory semantics consistently (for example
Unix directory mode and/or DOS directory bit) rather than only appending `/` to a filename.

## Structured live reload

Elyx development flow is:

1. install an `.eaf`/`.elyx` once;
2. enable it;
3. forward the dev-server port, normally `42690`;
4. compare local/installed file hashes;
5. send created/modified/deleted/moved paths relative to plugin root;
6. let Elyx unload, clear local modules and reload the plugin.

Because files are synchronized independently, Python-only changes should not require a Kotlin
rebuild. Kotlin changes should rebuild the DEX and then sync/replace `assets/classes.dex`.

The current template's old single-file watcher is not automatically a structured Elyx watcher.
Do not describe it as such until the protocol is actually implemented/tested.

## Reload implications

Elyx clears plugin-local Python modules, but code-created process-global resources remain the
plugin's responsibility.

On reload/unload explicitly stop or remove:

- threads/executors/work queues you own;
- sockets;
- notification observers/listeners;
- callbacks registered outside host-managed plugin registration;
- JVM static references and hook objects owned by the DEX layer.

## EAF release checklist

Before publishing:

- inspect archive root;
- install from the clean archive, not only live reload;
- verify id/version constraints and synchronization surfaces;
- verify all declared `refmap` paths;
- verify explicit directory entries required by the installer;
- verify `assets/classes.dex` is binary and correct;
- verify required asset bootstrap works without assuming `__file__`;
- test enable → disable → enable;
- test reload after Python change;
- test update from previous version when relevant;
- test at least default locale + English fallback;
- ensure no `.git`, venv, cache, build output, credentials or local logs are shipped.
