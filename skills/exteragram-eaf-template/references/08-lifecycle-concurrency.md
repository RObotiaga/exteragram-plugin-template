# Lifecycle, Concurrency and Reload Safety

Use this reference when code starts threads, holds callbacks, registers listeners/hooks,
maintains caches, crosses Python/JVM boundaries or must survive Elyx reloads safely.

## Ownership rule

Every long-lived resource needs one clear owner and one cleanup path.

Examples of resources:

- Xposed/unhook handles;
- NotificationCenter observers;
- Android listeners;
- menu items not host-cleaned automatically;
- Python threads/workers;
- sockets;
- timers;
- Java/Kotlin executors;
- callbacks/proxies bridging Python and JVM;
- Activity/View/Fragment references;
- per-generation caches.

If you cannot answer "who stops/removes this?", the lifecycle is incomplete.

## Module import is not plugin load

Avoid starting permanent work at module import time.

Elyx reload can clear/import Python modules while the Android process stays alive. Put resource
creation in `on_plugin_load` and resource retirement in `on_plugin_unload`/eject.

Safe mental model:

```text
import module -> define classes/constants
plugin load -> allocate/register/start
plugin unload/eject -> unregister/stop/drop
```

## Reload generation

A reload creates a new Python code generation inside the same process. Old Java/Kotlin static
state can outlive the old Python object if cleanup is incomplete.

For complicated asynchronous plugins, maintain a generation/cancellation token.

Conceptually:

```python
class MyPlugin(BasePlugin):
    def on_plugin_load(self):
        self._active = True
        self._generation = object()

    def on_plugin_unload(self):
        self._active = False
```

Background callbacks should check that they still belong to the active generation before
mutating UI/state or calling the JVM bridge.

## Python bridge locking

Initialization/ejection can race with worker callbacks or reload. The template already uses
locks around critical bridge lifecycle operations; preserve that principle when extending it.

Protect state transitions such as:

```text
not loaded -> loading -> loaded -> ejecting -> ejected
```

Do not hold a global lock while performing slow network or UI operations. Lock state mutation,
then perform independent work outside when possible.

## DEX/JVM generation safety

A DEX class loader and its static state can remain reachable after Python reload if:

- Kotlin holds a callback into Python;
- Xposed keeps a hook object;
- static fields reference host objects;
- a JVM worker thread retains plugin classes.

The JVM `eject` contract should therefore run before Python drops its bridge where possible.
It should:

- unhook persistent hooks;
- unregister observers/listeners;
- stop JVM-owned workers;
- clear callbacks into Python;
- clear caches/references;
- mark the old generation inactive.

Then Python should drop the class/bridge references.

## Work queues vs raw threads

Prefer existing SDK/background queues for bounded tasks such as HTTP, file I/O and parsing.
Create a dedicated thread only when the feature needs a persistent worker or behavior the queue
cannot provide.

If you create a worker:

- give it a stop flag/event;
- avoid non-daemon process blockers unless deliberate;
- bound its input queue;
- catch/log top-level exceptions;
- stop/join with a bounded strategy on unload;
- never assume process exit will clean it soon.

## UI crossing

Background work must not mutate Views directly.

Pattern:

```text
hook/UI callback
-> capture minimal immutable identifiers
-> background work
-> check generation still active
-> resolve current UI if needed
-> run_on_ui_thread(minimal mutation)
```

Do not hold a View/Fragment reference across long background work unless the lifecycle is
explicit and checked. Re-resolve current UI or use weak references where appropriate.

## Account state across async work

Capture the hook's account id together with dialog/message identifiers. Do not re-read the
currently selected account later and assume it is the same.

Async job payload should include the account it belongs to.

## Temporary files and asynchronous sends

A method returning after enqueuing a Telegram upload does not necessarily mean the file is no
longer needed.

Before deleting a temporary file, understand the send helper's ownership:

- did it copy bytes synchronously?
- did it open a descriptor that remains valid after unlink?
- will a later background uploader open the path again?

When uncertain, observe source/runtime and clean through completion/error callbacks or a
bounded cache cleanup policy rather than immediate deletion.

## Temporary hooks

Some workarounds require a global method replacement only for one operation. Keep the exposure
window minimal:

```text
install hook
try:
    perform operation
finally:
    unhook
```

If setup can fail before the `try`, make the cleanup path resilient. Track whether the hook was
actually installed.

## Observers/listeners

Host event systems frequently hold strong references. Store enough information to remove the
same observer/listener on unload.

Do not register a new observer on every reload without first removing the old one.

## Caches

Classify caches:

- **pure data cache**: usually safe if bounded and generation-independent;
- **reflection member cache**: often safe process-wide if target class loader is stable;
- **host object cache**: high leak risk;
- **View/Activity cache**: highest lifecycle risk;
- **DEX-generation object cache**: clear on eject.

Bound caches by size/time where the key space can grow.

## Reentrant callbacks

Hook callbacks can trigger APIs that themselves call the hooked method, causing recursion.
Use a narrow reentrancy guard when the call graph can loop.

Prefer per-thread/per-operation guards over one global boolean when concurrent accounts/threads
can legitimately execute simultaneously.

## Exception safety

Cleanup belongs in `finally` when it must happen whether work succeeds or fails.

Do not write:

```python
install_hook()
do_work()   # exception -> leaked hook
unhook()
```

Use:

```python
install_hook()
try:
    do_work()
finally:
    unhook()
```

Likewise, mark half-initialized lifecycle state carefully. A failed load should not make later
load attempts think initialization completed.

## Disable/eject semantics

Distinguish normal unload from emergency/concurrent eject if the template exposes both.

Normal unload may call the JVM's full cleanup API.
An eject path caused by a concurrent reload may need to invalidate references without invoking
unsafe callbacks into a generation that is already disappearing.

Keep these semantics explicit in code and logs.

## Lifecycle test matrix

For nontrivial plugins test:

1. cold app start with plugin enabled;
2. enable plugin after app already running;
3. disable plugin;
4. enable again without process restart;
5. Elyx reload after Python-only change;
6. reload after DEX change;
7. reload while background work is active;
8. switch Telegram account while background work is active;
9. leave/re-enter relevant screen;
10. repeat several reloads and watch for duplicate callbacks/leaks.

## Review checklist

- One owner per resource?
- Symmetric cleanup?
- No permanent import-time side effects?
- Old Python callbacks dropped by JVM?
- Workers stoppable?
- Async work generation/account aware?
- UI references not retained unnecessarily?
- Temporary hooks use `finally`?
- Caches bounded and correct lifetime?
- Reentrancy possible/guarded?
- Failed load can retry cleanly?
- Repeated reload does not duplicate behavior?
