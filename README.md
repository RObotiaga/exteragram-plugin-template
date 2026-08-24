# exteraGram Plugin Template

Шаблон плагина для exteraGram / AyuGram с Kotlin-логикой, которая собирается в DEX, и структурированной многофайловой сборкой Elyx/EAF.

## Как это устроено

- `<plugin-id>.py` — основной Python entry point: метаданные, загрузка встроенного DEX и мост к Kotlin-классу `Plugin`.
- `src/main/kotlin/...` — основная Kotlin-логика: хуки, пункты меню, настройки и i18n.
- `plugin_src/` — дополнительные Python-модули. При EAF-сборке каталог попадает в архив как пакет `src/`.
- `refmap.yml` и `metainfo.yml` — структура и метаданные Elyx.
- `tools/embed_dex.py` — встраивает `classes.dex` в копию Python entry point.
- `tools/build_eaf.py` — валидирует Python-файлы и собирает единый `.eaf`.
- `tools/dev_watch.py` — старый live-reload для однофайлового режима через `extera dev-sync`.
- `libs/Telegram*.jar` — классы хост-приложения; генерируются из APK командой `just update-apk`.

## Что находится внутри EAF

Релизный архив имеет вид:

```text
<plugin-id>.eaf
├── refmap.yml
├── metainfo.yml
├── main.py          # копия entry point с встроенным release classes.dex
└── src/
    ├── __init__.py
    └── ...          # любые дополнительные Python-модули из plugin_src/
```

`refmap.yml` всегда находится в корне архива. EAF является обычным ZIP-совместимым архивом, поэтому его структуру можно проверить стандартными ZIP-инструментами.

## Многофайловый Python

Дополнительный код складывается в `plugin_src/`. Например:

```text
plugin_src/
├── __init__.py
└── helpers.py
```

После сборки он станет `src/helpers.py`, поэтому из основного плагина его можно импортировать как:

```python
from src.helpers import some_helper
```

Сборщик рекурсивно добавляет содержимое `plugin_src/`, исключает `__pycache__`/`.pyc` и проверяет синтаксис всех Python-файлов перед упаковкой.

## Требования

`java` (JDK 21), `uv`, `just`, `adb`. Для `update-apk` дополнительно нужны `dex2jar` и `jbang`.

## Быстрый старт

```sh
# переименовать шаблон: Kotlin package, plugin id, отображаемое имя
just init com.example.myplugin my-plugin "My Plugin"

# положить/обновить libs/Telegram.jar и Telegram-compile.jar из APK хоста
just update-apk /path/to/exteragram.apk

# debug DEX
just dex
```

## Сборка EAF

Полная release-сборка:

```sh
just build
```

Результат:

```text
dist/<plugin-id>.eaf
```

Если release DEX уже собран, можно отдельно выполнить упаковку:

```sh
just eaf
```

Для совместимости пока сохранена старая однофайловая сборка:

```sh
just embed
# -> dist/<plugin-id>.py
```

GitHub Actions workflow **Release** теперь публикует `<plugin-id>.eaf`. Workflow **CI** собирает release DEX, создаёт EAF и проверяет обязательные файлы и целостность ZIP.

## Релизы

Workflow **Release** запускается вручную и принимает версию `x.x.x`. Перед сборкой он синхронно обновляет:

- `__version__` в Python entry point;
- `version` в `metainfo.yml`;
- версию проекта в `pyproject.toml`.

После этого собираются DEX и EAF, создаётся build provenance attestation, коммитятся метаданные, создаётся tag и GitHub Release.

## Прочие команды

- `just loc` — перегенерировать i18n-файлы без полной пересборки DEX.
- `just watch` — старый однофайловый live-reload; структурированный Elyx live-reload будет отдельным этапом миграции.
- `just gen-stubs <rt.jar> <android.jar>` — стабы для автодополнения в Python.

## Статус миграции

Текущий EAF уже поддерживает несколько Python-файлов и единый релизный архив. На этом этапе DEX по-прежнему встраивается в `main.py` проверенным механизмом hex-комментариев. Следующий независимый шаг — при необходимости перевести загрузчик на бинарный `classes.dex` как отдельный ресурс внутри EAF, не меняя Kotlin/Gradle-часть.

## Лицензия

[MIT](LICENSE)
