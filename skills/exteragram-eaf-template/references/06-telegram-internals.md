# Telegram Internals

Use this reference when a feature crosses from the plugin SDK into Telegram/exteraGram/AyuGram
classes, controllers, TLRPC objects or rendering code.

## Do not treat Telegram internals as a stable SDK

The `org.telegram.*` surface is application implementation, not the plugin API. It changes with
Telegram revisions and client forks.

For every private/internal integration, record which target build was used to verify it.

## Investigation order

When implementing a new internal integration:

1. Search the exact target APK/decompile for the relevant screen/action/data flow.
2. Identify the concrete class and method actually used by that build.
3. Inspect callers/callees, not only the one method declaration.
4. Confirm thread/lifecycle context.
5. Check whether a public plugin helper already wraps the behavior.
6. Only then design reflection/hook code.

Use upstream Telegram source to understand architecture, but do not assume it matches the fork
exactly.

## Common class families

Names below are navigation hints, not promises of signatures.

### `ApplicationLoader`

Global application/process context and initialization entry points. Useful for obtaining the
application context or parent class loader, but Activity-bound UI often needs an Activity or
Fragment context instead.

### `LocaleController`

Telegram locale state and language helpers. Useful when a plugin needs to align behavior with
the app language. For structured plugin user-facing strings, prefer Elyx localization when it
fits the feature.

### `ChatActivity`

Chat screen/fragment behavior. Relevant to:

- current dialog/chat state;
- action bar/menu construction;
- message interaction;
- composer behavior;
- chat-specific lifecycle.

It is a large class and changes frequently. Never hook a method only because an older analysis
names it.

### `MessageObject`

Telegram's higher-level wrapper around raw message structures. Commonly used by rendering and
interaction code. Prefer wrapper helpers when the host already exposes the information rather
than manually decoding every TLRPC field.

### `MessagesController`

Per-account state/controller for users, chats, dialogs and many request flows. Resolve it for
the correct account.

### `SendMessagesHelper`

Per-account send pipeline. Prefer public `client_utils` send helpers first; use internal send
APIs when the public helper cannot express required media/attributes/flags.

### `NotificationCenter`

Telegram's event bus. It can be useful for forcing/observing UI/data refreshes, but observer
registration is process state. Remove custom observers on unload/reload.

### `AndroidUtilities`

Large utility class used throughout Telegram. It contains UI, URI, dimensions and threading
helpers. Patching a broadly-used method can affect the entire app, so keep replacements narrow
and short-lived where possible.

### `TLRPC`

Generated Telegram protocol object model. Fields and flag bits encode wire-level semantics.
Do not set flags by guesswork.

When building a TLRPC object manually:

- inspect the generated class for that host revision;
- understand which flags correspond to optional fields;
- populate required fields consistently;
- test serialization/send behavior on the target client;
- prefer SDK send helpers when they already construct the object correctly.

## Account scoping

Most Telegram controllers are per-account. A hook can fire for a background account.

When resolving controllers from Python, pass the hook's account to account-aware SDK helpers.
When working inside Kotlin, derive/use the same account that owns the hooked object/request.

Do not mix a message from account A with `MessagesController`/`SendMessagesHelper` from the
currently selected account B.

## Rendering hooks

Message cell/rendering hooks can fire repeatedly because RecyclerView/ListView cells are
rebound and reused.

Rules:

- make operations idempotent;
- remove/reset modifications when a recycled cell receives a different message;
- avoid network/disk work in binding/draw methods;
- cache immutable lookup data, not View ownership indefinitely;
- consider stable markers/ids to associate plugin state with messages;
- trigger heavy background work once, then request a UI refresh through a supported path.

A real-plugin pattern is embedding a stable invisible marker in plugin-created text so a later
cell-binding hook can recognize that message without knowing its server id in advance. This is
an advanced workaround, not a generic recommendation; prefer explicit metadata/state when the
host API provides it.

## Touch/UI internals

A hook on a base Android View method can observe the same physical event at several levels of
the View hierarchy. If implementing global gesture/effect behavior:

- understand dispatch propagation;
- deduplicate one physical event;
- distinguish raw screen coordinates from View-local coordinates;
- avoid allocating heavy shader/effect objects per event;
- bound View-keyed caches;
- clear caches on unload and avoid leaking dead windows.

This pattern comes from working plugins, but exact fields/classes such as Telegram visual effect
implementations must be verified in the target host.

## Sending custom media

Before manually building Telegram documents/media:

1. Try `client_utils` send helpers.
2. Determine what metadata the helper cannot express.
3. Inspect `SendMessagesHelper` and related TLRPC structures.
4. Build only the missing custom layer.
5. Preserve a safe fallback if the custom path is optional.

Be careful with file lifetime. A send helper may enqueue asynchronous upload and return before
the file is fully consumed. Do not delete a temporary file merely because the enqueue call
returned successfully unless the implementation guarantees it has copied/opened what it needs.

## File/URI checks

Telegram has security checks around internal URIs/paths. Do not globally disable them as a
permanent workaround.

If a verified operation requires a temporary hook around one call, scope it tightly and unhook
in `finally`. Prefer choosing a supported file location/API over bypassing a security check.

## Context and UI ownership

`ApplicationLoader.applicationContext` is not interchangeable with an Activity/Fragment
context. Custom Telegram UI components/dialogs may require theme/activity context.

Obtain the current fragment/activity through public client helpers when appropriate and handle
`None` when there is no visible UI.

## Source matching

Useful sources include:

- exact exteraGram/AyuGram APK decompile;
- matching Telegram Android source revision;
- known working plugin analyses;
- `fossSquad/exteraSkill` references for class navigation.

Treat large generated references (for example lists of TLRPC classes) as search indexes rather
than something to memorize or copy wholesale into new code.

## Internal integration checklist

- Exact target build identified?
- Public SDK helper considered first?
- Declaring class/method/field verified?
- Correct account?
- Correct thread/context?
- Recycled UI behavior handled?
- TLRPC flags verified from source?
- Temporary files kept alive long enough?
- Broad host hook scoped narrowly?
- Observer/listener/hook cleanup implemented?
- Failure path degrades safely or blocks initialization clearly?
