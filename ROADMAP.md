# Roadmap

Отложенные доработки шаблона. Этот файл фиксирует направления, но не означает, что они входят в текущий PR.

## Backlog

### Runtime DEX bridge validation on AyuGram

EAF успешно устанавливается на AyuGram 12.9.0 и Python UI плагина создаётся, однако реальный JVM callback пока не подтверждён.

Наблюдавшийся runtime-симптом:

```text
Failed to execute settings callback example: cannot call invokeSettingsActionCallback: JVM plugin is not loaded
RuntimeError: cannot call invokeSettingsActionCallback: JVM plugin is not loaded
```

Это означает, что `TemplatePlugin.create_settings()` и Elyx installation path работают, но `JvmPluginBridge.load()` не оставил загруженный `ru.n08i40k.template.Plugin` в `jvm_plugin.klass` к моменту callback.

Следующий runtime-debug gate:

- собрать полный load-log начиная с `on_plugin_load()` / `_prepare_jvm_plugin()`;
- проверить фактический путь и чтение `assets/classes.dex` после распаковки Elyx;
- проверить создание `InMemoryDexClassLoader` и parent class loader;
- зафиксировать точное исключение из `loader.loadClass("ru.n08i40k.template.Plugin")`, если оно возникает;
- после исправления проверить settings callback, chat-context callback, Xposed hook и unload/reload без stale class loader.

Статус: known runtime issue; packaging/install verified, JVM execution pending.

### Structured Elyx live reload

Перевести текущий legacy `just watch` / `tools/dev_watch.py` на структурированный Elyx/EAF live reload, чтобы Python-модули, assets и `assets/classes.dex` синхронизировались независимо и без пересборки всего однофайлового payload.

Статус: deferred.

### Manual APK handoff -> automatic host JAR extraction

Сделать ручную передачу APK exteraGram/AyuGram первым классом workflow шаблона.

Ожидаемый сценарий:

```text
developer supplies target APK manually
        ↓
validate APK / record provenance
        ↓
generate libs/Telegram.jar
        ↓
run existing FixTelegramJar.java logic
        ↓
generate libs/Telegram-compile.jar
        ↓
validate both JARs
        ↓
run full Kotlin -> DEX -> EAF checks
```

Ограничения и требования:

- APK всегда предоставляет разработчик вручную;
- шаблон/CI не должен автоматически искать или скачивать APK;
- автоматически извлекаются/генерируются `Telegram.jar` и `Telegram-compile.jar`;
- желательно фиксировать hash, package/version/build metadata исходного APK для воспроизводимости;
- проверять, что оба JAR существуют, непусты и читаются как корректные ZIP/JAR;
- использовать результат в существующем полном `Kotlin -> DEX -> EAF` validation path;
- существующий `just update-apk /path/to/client.apk` можно использовать как основу, но будущий workflow должен сделать ручной APK handoff более явным и проверяемым.

Не входит в scope:

- автоматическое скачивание APK;
- автоматический выбор версии клиента;
- реализация этой задачи в текущем этапе EAF/skill-миграции.

Статус: deferred.
