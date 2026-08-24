RELEASE_DEX_PATH := `realpath -m build/outputs/dex/release/classes.dex`
DEBUG_DEX_PATH := `realpath -m build/outputs/dex/debug/classes.dex`

PLUGIN_PY := `grep -ls '^__id__ = ' -- *.py | head -n1`
EAF_PLUGIN_ID := `sed -n 's/^id: *//p' metainfo.yml | head -n1`
DIST_PY := "dist/" + file_name(PLUGIN_PY)
DIST_EAF := "dist/" + EAF_PLUGIN_ID + ".eaf"

# fail early if the tools a recipe needs are not installed
[private]
_require +COMMANDS:
    #!/usr/bin/env bash
    set -euo pipefail

    missing=()
    for cmd in {{ COMMANDS }}; do
        command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
    done

    if [ ${#missing[@]} -ne 0 ]; then
        echo "missing required commands: ${missing[*]}" >&2
        exit 1
    fi

# build dex in debug mode
dex: (_require "java")
    ./gradlew buildDexDebug

# generate i18n files (use added lines without full dex rebuild)
loc: (_require "java")
    ./gradlew generateI18n4kFiles

# build the release DEX
ci: (_require "java")
    ./gradlew buildDexRelease
    cp {{ RELEASE_DEX_PATH }} ./

# build the structured multi-file Elyx archive from an already-built DEX
eaf DEX_PATH=RELEASE_DEX_PATH OUTPUT=DIST_EAF: (_require "uv")
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "$(dirname '{{ OUTPUT }}')"
    uv run python tools/build_eaf.py \
        --dex '{{ DEX_PATH }}' \
        --plugin-file '{{ PLUGIN_PY }}' \
        --refmap refmap.yml \
        --metainfo metainfo.yml \
        --extra-source-dir plugin_src \
        --asset-dir assets \
        --output '{{ OUTPUT }}'

# full release build: Kotlin -> DEX -> EAF
build: ci eaf

# legacy single-file build kept for compatibility while the EAF migration settles
embed DEX_PATH=RELEASE_DEX_PATH OUTPUT=DIST_PY: (_require "uv")
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "$(dirname '{{ OUTPUT }}')"
    uv run python tools/embed_dex.py '{{ DEX_PATH }}' '{{ PLUGIN_PY }}' '{{ OUTPUT }}'

# legacy single-file live reload; structured EAF reload will be migrated separately
watch *ARGS: (_require "uv" "adb")
    uv run python tools/dev_watch.py '{{ PLUGIN_PY }}' '{{ DEBUG_DEX_PATH }}' {{ ARGS }}

# generate new Telegram[-compile].jar from updated extera/Ayu-Gram apk
update-apk PATH_TO_APK: (_require "dex2jar" "jbang" "git")
    #!/usr/bin/env bash
    set -veuo pipefail

    # create task temp dir
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

    # copy provided apk into temp dir
    cp {{ PATH_TO_APK }} "$tmp/Telegram.apk"

    # convert apk to jar
    dex2jar -f -o "$tmp/Telegram.jar" "$tmp/Telegram.apk"

    # fix class inheritance and exclude unneded packages
    jbang ./tools/FixTelegramJar.java "$tmp/Telegram.jar" "$tmp/Telegram-compile.jar"

    # copy generated jars
    mkdir ./libs/
    cp "$tmp/Telegram.jar" ./libs/Telegram.jar
    cp "$tmp/Telegram-compile.jar" ./libs/Telegram-compile.jar

    # and commit them
    git add -N -- ./libs/Telegram.jar ./libs/Telegram-compile.jar
    git commit -m "chore: bump telegram version" -- ./libs/Telegram.jar ./libs/Telegram-compile.jar

# generate stubs for python
gen-stubs PATH_TO_RT_JAR PATH_TO_ANDROID_JAR: (_require "java2pyi")
    java2pyi {{ PATH_TO_RT_JAR }} {{ PATH_TO_ANDROID_JAR }} ./libs/Telegram.jar -o stubs/

# rename plugin package/id/name and move sources
init NEW_PACKAGE NEW_ID NEW_NAME: (_require "uv")
    #!/usr/bin/env bash
    set -euo pipefail

    new_package='{{ NEW_PACKAGE }}'
    new_id='{{ NEW_ID }}'
    new_name='{{ NEW_NAME }}'

    if ! [[ "$new_package" =~ ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$ ]]; then
        echo "invalid package: $new_package (expected e.g. com.example.myplugin)" >&2
        exit 1
    fi

    # Intersection of legacy BasePlugin and structured Elyx id rules:
    # 2-32 chars, start with a letter, then letters/digits/underscore only.
    if ! [[ "$new_id" =~ ^[A-Za-z][A-Za-z0-9_]{1,31}$ ]]; then
        echo "invalid plugin id: $new_id (2-32 chars; start with a letter; use letters, digits, _)" >&2
        exit 1
    fi

    # current values are read from the sources, so the recipe can be run repeatedly
    old_package=$(sed -n 's/^ *namespace = "\(.*\)"$/\1/p' build.gradle.kts)
    old_py=$(grep -ls '^__id__ = ' -- *.py | head -n1)
    old_id=$(sed -n 's/^__id__ = "\(.*\)"$/\1/p' "$old_py")
    old_eaf_id=$(sed -n 's/^id: *//p' metainfo.yml | head -n1)
    old_name=$(sed -n 's/^rootProject.name = "\(.*\)"$/\1/p' settings.gradle.kts)

    if [ -z "$old_package" ] || [ -z "$old_py" ] || [ -z "$old_id" ] || [ -z "$old_eaf_id" ]; then
        echo "failed to detect current plugin package/id" >&2
        exit 1
    fi

    old_path="src/main/kotlin/${old_package//.//}"
    new_path="src/main/kotlin/${new_package//.//}"

    echo "package:   $old_package -> $new_package"
    echo "legacy id: $old_id -> $new_id"
    echo "EAF id:    $old_eaf_id -> $new_id"
    echo "name:      $old_name -> $new_name"

    # move the Kotlin sources into the new package folder
    if [ "$old_path" != "$new_path" ]; then
        mkdir -p "$(dirname "$new_path")"
        mv "$old_path" "$new_path"

        # drop the package folders left empty by the move
        old_parent=$(dirname "$old_path")
        while [ "$old_parent" != "src/main/kotlin" ] && rmdir "$old_parent" 2>/dev/null; do
            old_parent=$(dirname "$old_parent")
        done
    fi

    # package references, both dotted (Kotlin) and slashed (relocation/proguard config)
    files=(build.gradle.kts proguard-rules.pro "$old_py")
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find src -name '*.kt' -print0)

    sed -i \
        -e "s|${old_package//./\\.}|${new_package}|g" \
        -e "s|${old_package//.//}|${new_package//.//}|g" \
        -e "s|${old_id}|${new_id}|g" \
        "${files[@]}"

    # Keep legacy Python metadata and structured Elyx metadata synchronized.
    sed -i "s|^__id__ = \".*\"$|__id__ = \"${new_id}\"|" "$old_py"
    sed -i "s|^__name__ = \".*\"$|__name__ = \"${new_name}\"|" "$old_py"
    sed -i "s|^id: .*|id: ${new_id}|" metainfo.yml
    sed -i "s|^name: .*|name: ${new_name}|" metainfo.yml
    sed -i "s|^rootProject.name = \".*\"$|rootProject.name = \"${new_name}\"|" settings.gradle.kts
    sed -i "s|^name = \".*\"$|name = \"${new_id}\"|" pyproject.toml

    if [ "$old_py" != "${new_id}.py" ]; then
        mv "$old_py" "${new_id}.py"
    fi

    uv sync

    echo "done, run 'just build' to produce dist/${new_id}.eaf"
