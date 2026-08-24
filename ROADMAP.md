# Roadmap

Отложенные доработки шаблона. Этот файл фиксирует направления, но не означает, что они входят в текущий PR.

## Backlog

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
