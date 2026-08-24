# Python / BasePlugin Layer

Use this reference for the Python plugin lifecycle, high-level hooks, account-aware helpers,
menu items, settings and when to stay in Python instead of moving work into DEX.

The current official SDK docs are the authority for exact signatures.

## Baseline

Current public documentation describes:

- Python runtime: 3.11;
- Chaquopy-based Python/Java interop;
- `BasePlugin` as the primary plugin class;
- high-level event/request/update hooks;
- Xposed-style Java method hooking through separate APIs;
- practical app baseline around exteraGram 12.5.1+ for the current SDK tree.

For the structured template, `metainfo.yml` is canonical metadata. Legacy top-level dunder
metadata may remain while single-file compatibility is intentionally supported.

## Lifecycle

Use lifecycle methods as ownership boundaries.

```python
class MyPlugin(BasePlugin):
    def on_plugin_load(self):
        self.log("loaded")

    def on_plugin_unload(self):
        self.log("unloaded")
```

Initialization which allocates resources should normally happen in `on_plugin_load`, not at
module import time. Cleanup should be symmetric in `on_plugin_unload` or the template's
explicit eject path.

Avoid relying on object destruction/GC to remove hooks, listeners or workers.

## High-level hooks vs Java method hooks

Do not confuse these two systems.

### Telegram request/update/outgoing-message hooks

Register high-level engine hooks through `BasePlugin`, for example:

```python
def on_plugin_load(self):
    self.add_hook("TL_messages_setTyping")
    self.add_on_send_message_hook()
```

Implement the corresponding callback and return a `HookResult`.

Common strategies:

- `DEFAULT`: leave operation unchanged;
- `CANCEL`: stop it;
- `MODIFY`: use the supplied modified object;
- `MODIFY_FINAL`: modify and stop later plugin processing for that event.

Depending on callback type, place the modified value in the corresponding field such as
`request`, `response`, `update`, `updates` or `params`.

### Arbitrary Java/Xposed hooks

Use `hook_method`/constructor hooking and `MethodHook`/`MethodReplacement` for arbitrary Java
methods. `add_hook("TL_...")` is not a generic reflection API.

See `05-hooks-reflection.md`.

## Hook registration is required

Defining a callback method alone does not activate the hook. Registration belongs in load
logic.

Bad mental model:

```text
method exists -> host automatically calls it
```

Correct model:

```text
register hook -> host dispatches matching event -> callback returns HookResult
```

## Outgoing-message safety

Outgoing message parameters are not guaranteed to contain a text string. Check the field
before string operations:

```python
def on_send_message_hook(self, account, params):
    message = getattr(params, "message", None)
    if not isinstance(message, str):
        return HookResult()
    ...
```

If a command-like outgoing message must never reach the server, return `CANCEL` before
starting asynchronous work.

## Multi-account rule

Background Telegram accounts remain connected and can fire hooks while another account is
selected in the UI.

Inside a hook, the callback's `account` is the authoritative account for follow-up actions.
Prefer:

```python
client = self.client(account)
client.send_text(dialog_id, "...")
```

or pass `account=` explicitly to helpers that support it.

Do not use UI-selected-account helpers implicitly inside a background-account hook unless the
feature intentionally targets the selected account.

When a plugin keeps account-specific state, key it by account id/index instead of using one
global mutable slot.

## Client utilities

Prefer public `client_utils` helpers before raw Telegram internals for common work such as:

- sending text/media;
- editing messages;
- sending requests;
- reaching controllers/fragments;
- posting background work;
- notification listeners.

Dropping to raw `MessagesController`, `SendMessagesHelper` or TLRPC construction is justified
when the helper does not expose the required behavior or metadata.

## Threading

Never perform network calls, file I/O, heavy parsing or expensive loops in a UI callback or a
high-frequency hook.

Use the SDK's background queue helper where appropriate:

```python
from client_utils import run_on_queue
run_on_queue(lambda: do_work())
```

Move only the final View/UI mutation back to the main thread with `run_on_ui_thread`.

Do not create unbounded ad-hoc threads for work that fits the existing plugin queue.

## Settings

For normal plugin settings, prefer `ui.settings` rows and `BasePlugin`/Elyx settings storage
instead of custom Telegram UI hooks.

Typical row types include headers, switches, selectors, input/edit rows, text rows and custom
rows. Check live docs for the exact current class set and constructor arguments.

A setting key should be:

- stable across versions;
- namespaced enough to avoid accidental reuse inside the plugin;
- given an explicit default;
- migrated deliberately if type/meaning changes.

Avoid reads from persistent settings in extremely hot hooks if the helper performs nontrivial
work; cache the value and update the cache when settings change when necessary.

## Menu items

Prefer `MenuItemData` + `MenuItemType` when the public menu API can express the desired
placement/visibility.

Current docs include menu types such as message context, drawer, main, chat action and profile
action menus. Verify names in live docs before coding.

The click context is screen/menu dependent. Treat keys as optional and inspect/log them during
development rather than assuming every menu provides the same objects.

Low-level Telegram UI hooks are justified when:

- no public menu location exists;
- visibility needs host-specific state the public condition system cannot safely express;
- the feature modifies an existing component rather than adding a supported action.

## Metadata

For legacy single-file plugins, metadata values are parsed statically and must be simple
top-level constants. Do not construct them dynamically.

For this structured template:

- keep production identity/compatibility in `metainfo.yml`;
- maintain legacy dunder values only while legacy build is intentionally supported;
- release tooling should update both surfaces consistently if both remain.

Do not assume legacy id grammar equals structured Elyx id grammar.

## Dependencies

Prefer the libraries already present in the runtime when suitable. For other Python packages,
use the supported dependency metadata and pure-Python packages unless the target mechanism
explicitly supports a compatible bundled wheel.

Do not add a dependency for a tiny function that is clearer and safer to implement locally.
Do not vendor a huge library into `src/` without considering archive size, licensing and
reload cost.

## Errors and user feedback

Separate developer diagnostics from user-facing errors.

Developer-facing:

- `self.log(...)`;
- structured stage names;
- exception + traceback;
- relevant account/dialog/method/version identifiers.

User-facing:

- concise bulletin/dialog;
- avoid leaking stack traces/secrets by default;
- provide a copy-details action when diagnostics are useful.

The template's load bridge should fail closed: if DEX cannot be loaded, do not continue into
JVM calls that assume a valid class.

## Choosing Python vs Kotlin

Keep code in Python when it is mostly:

- orchestration;
- settings/state decisions;
- moderate-frequency public SDK hooks;
- network/file operations already handled off-thread;
- Elyx resource/localization logic;
- feature glue.

Consider Kotlin/DEX when it is:

- a very hot Java hook;
- complex JVM type/reflection work;
- code that benefits materially from compile-time checks;
- a reusable set of JVM helpers;
- logic where Python↔Java calls would dominate the hot path.

## Python review checklist

- Hook registered?
- Correct `HookResult` field/strategy?
- Correct `account` used for follow-up work?
- Blocking work off UI thread?
- UI mutation on UI thread?
- Optional context/message fields checked?
- State owned and cleaned up?
- No import-time permanent side effects?
- Local module name does not shadow SDK/stdlib?
- Errors logged with enough context?
- Public SDK used before private Telegram hook where feasible?
