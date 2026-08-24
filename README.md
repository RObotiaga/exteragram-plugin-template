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
- `libs/Telegram*.jar` — классы хост-приложения; генерируются из вручную переданного APK командой `just update-apk`.

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

DEX больше не переводится в hex и не вставляется в `main.py`. В Elyx переменная `__file__` у entry point может отсутствовать, поэтому `JvmPluginBridge` не полагается на неё как на основной источник пути. Загрузчик получает каталог плагинов через `file_utils.get_plugins_dir()` и ищет DEX по структурированному пути:

```text
<get_plugins_dir()>/ElyxPlugins/<plugin-id>/assets/classes.dex
```

Если `__file__` доступен, каталог `main.py` используется как дополнительный кандидат. Это сохраняет совместимость с окружениями, где Python entry point запускается обычным способом.

Старый hex-механизм остаётся резервным только для `just embed`, чтобы не ломать однофайловую совместимость во время миграции.

## Идентификатор плагина

Для structured EAF канонический идентификатор хранится в `metainfo.yml` в поле `id`. Elyx разрешает 2–32 ASCII-символа из букв, цифр и `_`; дефис `-` недопустим.

Legacy single-file metadata `__id__` допускает дефис, но шаблон намеренно использует более строгий общий формат, совместимый сразу с обоими режимами:

```text
^[A-Za-z][A-Za-z0-9_]{1,31}$
```

То есть используйте `my_plugin`, а не `my-plugin`. Значения `metainfo.id`, Python `__id__`, JVM `Plugin.ID` и имя EAF должны оставаться синхронизированы. `just init` обновляет идентификатор и переименовывает основной Python-файл.

## Метаданные шаблона

Исходная версия шаблона — `0.1.0`. Она синхронизирована между Python `__version__`, `metainfo.yml` и `pyproject.toml`.

Автор по умолчанию:

```text
@me_tema
```

Это только стартовое значение. Автор плагина может свободно менять `__author__` и поле `author` в `metainfo.yml`; CI и release workflow не привязаны к конкретному имени автора.

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

# вручную получить APK хоста и сгенерировать из него Telegram.jar/Telegram-compile.jar
just update-apk /path/to/exteragram.apk

# debug DEX
just dex
```

`just update-apk` не скачивает APK автоматически: путь к APK всегда передаётся разработчиком вручную.

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

В этом режиме `tools/embed_dex.py` по-прежнему вставляет DEX в hex-комментарии, а загрузчик автоматически использует их как fallback, если structured `assets/classes.dex` отсутствует.

GitHub Actions workflow **Release** публикует `<metainfo.id>.eaf`. Workflow **CI** всегда выполняет smoke-сборку с тестовым бинарным DEX и проверяет:

- валидность Elyx `metainfo.id`;
- отказ сборки для id с дефисом;
- совпадение Python `__id__` с `metainfo.id`;
- совпадение версии между Python, `metainfo.yml` и `pyproject.toml`;
- наличие `assets/classes.dex`;
- точное совпадение бинарного DEX с входным файлом;
- отсутствие DEX-hex в `main.py`;
- неизменность `main.py` при EAF-упаковке;
- структуру `refmap.yml`;
- целостность ZIP/EAF.

Значение автора намеренно не сравнивается с шаблонной константой.

Если в репозитории присутствуют `libs/Telegram.jar` и `libs/Telegram-compile.jar`, CI дополнительно выполняет полный Gradle → release DEX → проверку runtime type surface → EAF путь.

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

Многофайловый EAF и бинарный DEX уже разделены: Python-код остаётся обычным исходным кодом, а JVM-движок хранится отдельным `assets/classes.dex`. Structured identity теперь синхронизирован между Python, Elyx и JVM-частью. Runtime asset resolver поддерживает Elyx, где `__file__` отсутствует. Следующий независимый этап — перевести dev-watch на структурированный Elyx live-reload, чтобы изменения Python-файлов и DEX синхронизировались на устройство независимо.

## Лицензия

[MIT](LICENSE)