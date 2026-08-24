# UI, Settings, Menus and User Feedback

Use this reference for plugin settings, menu items, dialogs, bulletins, custom Telegram UI and
UI-thread rules.

## Prefer public UI surfaces first

Use the stable plugin UI APIs when they can express the feature:

1. `ui.settings` for plugin preferences;
2. `MenuItemData`/`MenuItemType` for supported menu placements;
3. alert/bulletin helpers for feedback;
4. only then low-level hooks into Telegram screens/components.

This reduces breakage when Telegram UI internals change.

## Settings design

A settings screen should be a projection of persistent plugin state, not the state store
itself.

Use stable keys and explicit defaults. Example style:

```python
def create_settings(self):
    return [
        Header(text="General"),
        Switch(
            key="feature_enabled",
            text="Enable feature",
            default=True,
        ),
    ]
```

Check the current docs for constructor parameters and available row classes before writing a
new type.

When a setting changes behavior in a hot hook, consider maintaining a cheap in-memory value
rather than repeatedly doing persistent reads per callback.

## Settings migrations

If a key changes meaning or type:

- do not silently reinterpret old data where that can produce unsafe behavior;
- migrate once during load or read;
- keep a schema/version key when settings become complex;
- preserve defaults for new installs;
- test import/export if the plugin exposes it.

## Elyx settings vs BasePlugin settings

Structured Elyx exposes a plugin-bound settings controller; `BasePlugin` also provides
settings helpers. They ultimately exist to solve the same persistent configuration problem.

Choose a consistent convention per plugin. Do not mirror every value into two stores.

## Menu items

Use public menu item types when possible. Current public SDK exposes several placements such as
message-context, drawer/main, chat-action and profile-action menu types.

The callback context is conditional. Treat entries such as `message`, `dialog_id`, `fragment`,
`user`, `chat`, `account` and grouped data as optional unless the specific menu contract
promises them.

During development, logging available context keys is safer than inventing them.

## Public menu API vs low-level UI hook

Use a Telegram UI hook only when the public menu system cannot satisfy the requirement.
Examples:

- injecting a custom section into an unsupported settings screen;
- modifying an existing host button/row;
- placement visible only under a host-internal state not exposed by the menu condition API;
- manipulating a component before/after Telegram creates it.

Document why the public API was insufficient. This prevents future maintainers from keeping a
fragile hook after a stable menu API becomes available.

## Telegram custom components

Telegram uses many custom classes under `org.telegram.ui.Components` and related packages.
Do not guess constructors or methods.

Before instantiating or hooking one:

1. inspect the exact target source/decompile;
2. determine required Context/theme/lifecycle;
3. inspect overloads and listener interfaces;
4. verify layout/density assumptions;
5. use UI-thread execution.

An `Application` context is often insufficient for themed dialogs/components that need an
Activity context.

## UI thread

All Android View hierarchy changes must occur on the main/UI thread.

Use `run_on_ui_thread` for the final UI mutation when the caller may be off-thread.

Bad:

```text
background network request
-> directly modify TextView
```

Good:

```text
background network request
-> compute result
-> run_on_ui_thread(minimal View update)
```

Do not move network/parsing work to the UI thread just because a callback ends in UI.

## Bulletins

Bulletins are appropriate for short transient states:

- success;
- error;
- operation started/completed;
- action with a small button such as Copy/Undo.

Avoid emitting a bulletin for every event in a high-frequency hook.

For long operations, use a small state progression rather than flooding the screen.

When an error is technical, show a concise message and offer copyable diagnostics instead of
rendering a full traceback to the user.

## Dialogs

Dialogs fit confirmation, choice, detailed errors and flows that require explicit user action.

Rules:

- resolve a valid visible Fragment/Activity context;
- handle the no-visible-fragment case gracefully;
- construct/show on UI thread;
- do not retain dialog/Activity references in global static caches;
- avoid launching dialogs from high-frequency callbacks without deduplication.

## Localization

For structured EAF, use Elyx strings/localization for production user-facing text when the
feature has more than a handful of strings.

Benefits:

- locale separation from code;
- English fallback;
- metadata description localization;
- less churn in `main.py`;
- easier translation review.

Keep debug logs in a stable developer language where useful; user-facing UI should be
localized.

## Accessibility and host consistency

Prefer Telegram/exteraGram components and theme colors/icons where possible so UI follows
light/dark themes and host behavior.

When adding custom rows/buttons:

- preserve touch target sizes;
- do not encode meaning only in color;
- avoid hard-coded pixel dimensions when density helpers exist;
- verify scroll/recycler reuse;
- ensure feature disable/unload removes or stops affecting custom UI.

## View reuse

Telegram list/chat cells are often recycled. A hook that changes a View for one item must also
reset that modification when the View binds another item.

Do not assume a View instance permanently belongs to one message/user/settings item.

Use stable model state to decide every bind, and make the transformation idempotent.

## UI caching

Caching expensive graphics/resources can be appropriate, but:

- key by a stable scope;
- use a bounded cache;
- avoid strong references to dead Activity/View trees;
- clear generation-specific caches on unload/eject;
- create expensive graphics on the appropriate thread.

A real plugin may cache a shader/effect per root View to avoid recompilation on every touch.
The reusable principle is **cache expensive immutable-ish per-View resources with bounds and
cleanup**, not the exact class/cache size from one example.

## UI review checklist

- Public settings/menu API considered first?
- Exact current row/menu class names verified?
- Context keys checked for absence?
- View mutations on UI thread?
- Heavy work off UI thread?
- Current Fragment/Activity may be `None`?
- Theme/density respected?
- Recycled View state reset?
- Dialog/bulletin deduplicated?
- Cached UI references bounded/cleaned?
- Unload/disable leaves no stale UI behavior?
