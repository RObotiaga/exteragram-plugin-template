# exteraGram Plugin Template

Шаблон плагина для exteraGram / AyuGram с Kotlin-логикой, которая собирается в DEX, и структурированной многофайловой сборкой Elyx/EAF.

## Как это устроено

- `<plugin-id>.py` — основной Python entry point: legacy-метаданные, загрузка бинарного DEX из EAF и мост к Kotlin-классу `Plugin`.
- `src/main/kotlin/...` — основная Kotlin-логика: хуки, пункты меню, настройки и i18n.
- `plugin_src/` — дополнительные Python-модули. При EAF-сборке каталог попадает в архив как пакет `src/`.
- `assets/` — дополнительные бинарные/текстовые ресурсы проекта. Release `classes.dex` добавляется сюда автоматически как `assets/classes.dex`.
- `refmap.yml` и `metainfo.yml` — структура и канонические метаданные Elyx.
- `tools/build_eaf.py` — валидирует Python-файлы и Elyx id, добавляет бинарный DEX и собирает единый `.eaf`.
- `tools/embed_dex.py` — старый упаковщик для совместимого однофайлового режима; в EAF-сборке не используется.
- `tools/dev_watch.py` — старый live-reload для однофайлового режима через `extera dev-sync`.
- `libs/Telegram*.jar` — классы хост-приложения; генерируются из APK командой `just update-apk`.

## Что находится внутри EAF

Релизный архив имеет вид:

```text
<plugin-id>.eaf
├── refmap.yml
├── metainfo.yml
├── main.py                 # исходный Python entry point без встроенного DEX
├── assets/
│   ├── classes.dex         # настоящий бинарный release DEX
│   └── ...                 # дополнительные ресурсы из assets/
└── src/
    ├── __init__.py
    └── ...                 # дополнительные Python-модули из plugin_src/
```

`refmap.yml` находится в корне архива и объявляет `assets: assets`. EAF является обычным ZIP-совместимым архивом, поэтому его структуру можно проверить стандартными ZIP-инструментами.

DEX больше не переводится в hex и не вставляется в `main.py`. В structured Elyx runtime `__file__` может отсутствовать, поэтому `JvmPluginBridge` в первую очередь определяет корень установленного EAF через `file_utils.get_plugins_dir()` и читает `<plugins-dir>/ElyxPlugins/<plugin-id>/assets/classes.dex`. Путь относительно `__file__` остаётся только дополнительным compatibility fallback.

Старый hex-механизм остаётся резервным только для `just embed`, чтобы не ломать однофайловую совместимость во время миграции.

## Идентификатор плагина

Для structured EAF канонический идентификатор хранится в `metainfo.yml` в поле `id`. Elyx разрешает 2–32 ASCII-символа из букв, цифр и `_`; дефис `-` недопустим.

Legacy single-file metadata `__id__` допускает дефис, но `just init` намеренно использует более строгий общий формат, совместимый сразу с обоими режимами:

```text
^[A-Za-z][A-Za-z0-9_]{1,31}$
```

То есть используйте `my_plugin`, а не `my-plugin`. После `just init` значения `metainfo.id`, Python `__id__`, имя Python-файла и имя EAF синхронизированы.

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

## Дополнительные assets

Если плагину нужны изображения, JSON, модели или другие файлы, создайте каталог `assets/`:

```text
assets/
├── config.json
└── icons/
    └── example.png
```

Они попадут в EAF с сохранением относительных путей. Файл `assets/classes.dex` резервируется сборщиком: его нельзя хранить вручную, потому что он всегда берётся из результата Gradle через параметр `--dex`.

## Требования

`java` (JDK 21), `uv`, `just`, `adb`. Для `update-apk` дополнительно нужны `dex2jar` и `jbang`.

## Быстрый старт

```sh
# переименовать шаблон: Kotlin package, plugin id, отображаемое имя
just init com.example.myplugin my_plugin "My Plugin"

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
dist/<metainfo.id>.eaf
```

Путь сборки:

```text
Kotlin sources
    ↓ Gradle
classes.dex
    ↓
assets/classes.dex ─┐
Python modules ─────┤
assets/* ───────────┤
refmap/metainfo ────┤
                    ↓
             <metainfo.id>.eaf
```

Если release DEX уже собран, можно отдельно выполнить упаковку:

```sh
just eaf
```

Для совместимости пока сохранена старая однофайловая сборка:

```sh
just embed
# -> dist/<plugin-source>.py
```

В этом режиме `tools/embed_dex.py` по-прежнему вставляет DEX в hex-комментарии, а загрузчик автоматически использует их как fallback, если `assets/classes.dex` отсутствует.

GitHub Actions workflow **Release** публикует `<metainfo.id>.eaf`. Workflow **CI** всегда выполняет smoke-сборку с тестовым бинарным DEX и проверяет:

- валидность Elyx `metainfo.id`;
- отказ сборки для id с дефисом;
- наличие `assets/classes.dex`;
- точное совпадение бинарного DEX с входным файлом;
- отсутствие DEX-hex в `main.py`;
- неизменность `main.py` при EAF-упаковке;
- структуру `refmap.yml`;
- целостность ZIP/EAF.

Если в репозитории присутствуют `libs/Telegram.jar` и `libs/Telegram-compile.jar`, CI дополнительно выполняет полный Gradle → release DEX → EAF путь.

## Релизы

Workflow **Release** запускается вручную и принимает версию `x.x.x`. Перед сборкой он синхронно обновляет:

- `__version__` в Python entry point;
- `version` в `metainfo.yml`;
- версию проекта в `pyproject.toml`.

Имя EAF и release asset берётся из `metainfo.id`. После этого собираются DEX и EAF, проверяется бинарный `assets/classes.dex`, создаётся build provenance attestation, коммитятся метаданные, создаётся tag и GitHub Release.

## Прочие команды

- `just loc` — перегенерировать i18n-файлы без полной пересборки DEX.
- `just watch` — старый однофайловый live-reload; структурированный Elyx live-reload будет отдельным этапом миграции.
- `just gen-stubs <rt.jar> <android.jar>` — стабы для автодополнения в Python.

## Статус миграции

Многофайловый EAF и бинарный DEX разделены: Python-код остаётся обычным исходным кодом, а JVM-движок хранится отдельным `assets/classes.dex`. Structured identity берётся из `metainfo.yml` и синхронизируется с Python/JVM metadata. Загрузка DEX из structured Elyx каталога проверена на AyuGram на устройстве. Следующий независимый этап — перевести dev-watch на structured Elyx live-reload, чтобы изменения Python-файлов и DEX синхронизировались на устройство независимо.

## Лицензия

[MIT](LICENSE)