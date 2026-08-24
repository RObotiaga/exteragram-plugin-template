# Hooks and Reflection

Use this reference for Xposed-style method hooks, constructors, Java reflection, private
members and performance rules.

## Two hook systems: keep them separate

### High-level Telegram event hooks

`BasePlugin.add_hook("TL_...")` registers request/update interception by Telegram TL name.
`add_on_send_message_hook()` registers outgoing-message interception.

These are not arbitrary Java method hooks.

### Java/Xposed-style hooks

Use `hook_method`, constructor helpers and `MethodHook`/`MethodReplacement` (or supported
functional before/after callbacks) for Java methods and constructors.

Do not write code like `add_hook(JavaClass, "method", ...)` unless the current SDK explicitly
supports that exact overload; it is not the normal public contract.

## Find the exact member first

Before writing a hook, establish:

- fully-qualified declaring class;
- method/constructor name;
- static or instance;
- exact parameter Java types in order;
- return type;
- overload chosen;
- visibility;
- whether the host calls it on UI/background thread;
- version/build where the member was verified.

For Telegram internals, inspect the exact target decompile/source. Do not infer signatures from
method names.

## `MethodHook`

Use before/after hooks when the original implementation should normally run.

Conceptually:

```python
class MyHook(MethodHook):
    def before_hooked_method(self, param):
        value = param.args[0]
        ...

    def after_hooked_method(self, param):
        result = param.getResult()
        ...
```

Useful `param` concepts:

- `thisObject`: receiver for instance methods;
- `args`: mutable argument array;
- `method`: reflected member;
- `getResult()`/`setResult(...)`: result handling.

Setting a result in a before hook can skip the original call. Use this deliberately; it can
change control flow far beyond your plugin.

## Before vs after

Choose based on semantics, not habit.

Use **before** when you need to:

- inspect/modify inputs;
- cancel/short-circuit;
- trigger something at event start;
- prevent the original side effect.

Use **after** when you need to:

- inspect/modify the returned result;
- use fields initialized by the original method/constructor;
- patch an object after host initialization;
- react only after successful original execution.

For constructors, after-hooking is often safer when you need a fully initialized instance.

## Method replacement

`MethodReplacement` is appropriate when the original method must not execute. It is more
invasive than before/after hooking.

Prefer a narrow conditional before-hook with `setResult` when only a subset of calls needs to
be suppressed and the original should run otherwise.

## Exact reflection signatures

Java reflection requires exact classes for overload resolution.

Do not assume Python values imply Java reflection types. Resolve primitives/boxed/reference
classes explicitly.

When a method changes across host versions, do not swallow `NoSuchMethodException` and act as
if the hook succeeded. Either:

- probe supported signatures in a defined order;
- gate by version;
- disable the feature and log a compatibility error.

## `find_class` vs `Class.forName`

Official SDK documentation may expose `hook_utils.find_class` as a convenient class lookup.
Real plugin analyses have observed version/build differences where a returned Chaquopy class
wrapper did not expose the same reflection methods expected by documentation.

Do not turn either representation into a universal rule.

Safe approach for version-sensitive code:

1. use the current documented helper where its returned object supports the needed operation;
2. when an actual target build demonstrates wrapper/reflection incompatibility, obtain an
   explicit `java.lang.Class` with a verified path such as `Class.forName`;
3. log the app/SDK version and preserve the workaround as a scoped compatibility branch;
4. remove old workarounds when no longer tested/supported.

The template itself may already use direct Java `Class` reflection in its bridge. Follow the
current repository implementation for that bridge rather than mixing class representations.

## Private fields

Private-field access is fragile. Use `hook_utils` helpers or explicit reflection only when the
feature cannot be implemented through a stable public path.

For every private field access:

- verify field name/type in the target host;
- wrap failure with a useful feature-specific log;
- do not mutate unrelated global state;
- avoid retaining the field value if it owns Activity/View state beyond its lifecycle.

If a field is only an optimization, the plugin should usually survive its absence.

## High-frequency hooks

Examples: touch dispatch, message-cell binding, drawing/layout, scrolling and networking hot
paths.

Rules:

- no network;
- no disk I/O;
- no expensive reflection lookup per call;
- no unbounded allocation;
- no repeated settings/database reads when a cache works;
- no verbose logging per event outside a diagnostic mode;
- deduplicate repeated delivery where the host dispatches one event through many Views/cells;
- bound caches and clear them on unload/eject.

A real-plugin pattern is deduplicating repeated touch dispatch with a stable event token such
as event down-time/action rather than firing once for every View in the dispatch chain. Use the
pattern only where it matches the host event model; do not copy a token mechanically.

## Cache reflection results

Reflection lookup is expensive enough to keep out of hot callbacks.

Resolve classes/methods/fields during initialization or first use, then cache the reflected
member if its lifecycle is process-safe.

Do not cache host object instances (Activity/View/Fragment) just because caching a `Method`
object is acceptable.

## UI hooks

Android View mutation belongs on the UI thread. A hook may already run there, but if the call
can originate off-thread or later callback behavior is uncertain, marshal the actual View
mutation through `run_on_ui_thread`.

Do not move heavy computation onto UI thread merely because the final operation touches a
View. Compute off-thread, then apply the minimal UI change.

## Hook scope

Keep invasive hooks active for the shortest scope that satisfies the feature when practical.
A useful pattern for a temporary host bypass is:

```text
install narrow hook
try:
    perform operation that needs it
finally:
    unhook
```

Use `finally`. A leaked method replacement can corrupt unrelated application behavior until
process restart.

For persistent plugin features, register on load and unhook on unload/eject.

## Priorities

Hook priority changes ordering relative to other hooks/plugins. Do not pick extreme priorities
without a requirement.

Document why ordering matters when setting a non-default priority. Plugins can coexist; avoid
assuming yours is the only hook on the method.

## Error boundaries

At registration time, distinguish class-not-found, member-not-found and hook-install failure.
Inside callbacks, catch failures only where the feature can safely degrade.

Never let a catch-all convert a failed required hook into a false success state.

Useful diagnostics include:

```text
feature
host version
class
method/constructor signature
hook phase (before/after/replacement)
exception type/message
```

## Prefer Kotlin for very hot hooks

A Python hook is convenient, but every hot Python↔Java transition has overhead. For extremely
frequent hooks or complex Java object processing, moving only the hot path into Kotlin/DEX can
improve performance and type clarity while Python retains lifecycle/settings ownership.

Measure or reason from call frequency; do not migrate trivial hooks preemptively.

## Hook review checklist

- Correct hook system chosen?
- Exact target source inspected?
- Exact overload/types?
- Before/after/replacement justified?
- High-frequency callback bounded?
- Reflection lookup outside hot path?
- UI work on UI thread?
- Unhook handle owned?
- Cleanup in unload/eject?
- Version-specific fallback documented?
- Failure visible instead of silently ignored?
