#!/usr/bin/env bash
# DS Forever Linux Edition: one-command build on a Linux PC (no Windows tools needed).
#   ./linux-build.sh            debug APK (signed with this PC's ~/.android/debug.keystore)
#   ./linux-build.sh --test     also run the streaming module's unit tests
#   DSF_LOCAL_RUNTIME=1 ./linux-build.sh   also fetch and package the local game runtime (Proton, drivers...; upstream's full app)
# Needs: JDK 17 and the Android SDK (platform 36, build-tools 36.1.0, NDK 27.2.12479018, cmake 3.22.1).
# Defaults to ~/.local/android-build/{jdk-17*,sdk}; override with JAVA_HOME / ANDROID_HOME.
# Output: app/build/outputs/apk/modern/debug/app-modern-debug.apk. Personal builds only: see FORK.md before sharing an APK.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd); cd "$ROOT"
TOOLS=${DSF_TOOLS:-$HOME/.local/android-build}
export JAVA_HOME=${JAVA_HOME:-$(ls -d "$TOOLS"/jdk-17* 2>/dev/null | head -1)}
export ANDROID_HOME=${ANDROID_HOME:-$TOOLS/sdk}
NDK=$ANDROID_HOME/ndk/27.2.12479018
CMAKE_BIN=$ANDROID_HOME/cmake/3.22.1/bin
[ -x "$JAVA_HOME/bin/java" ] || { echo "JDK 17 not found (set JAVA_HOME)"; exit 1; }
[ -d "$NDK" ] || { echo "NDK 27.2.12479018 not found under $ANDROID_HOME"; exit 1; }
export PATH=$JAVA_HOME/bin:$CMAKE_BIN:$PATH ANDROID_NDK=$NDK
echo "sdk.dir=$ANDROID_HOME" > local.properties
TMPD=$(mktemp -d); trap 'rm -rf "$TMPD"' EXIT
lf() { tr -d '\r' < "$1" | sed 's#prebuilt/windows-x86_64#prebuilt/linux-x86_64#g; s#\.exe"#"#g; s#^python #python3 #' > "$TMPD/$(basename "$1")"; echo "$TMPD/$(basename "$1")"; }

dep() {  # name url commit
    local d=.deps/$1
    if [ ! -d "$d" ]; then git init -q "$d"; git -C "$d" remote add origin "$2"; git -C "$d" fetch -q --depth=1 origin "$3"; git -C "$d" checkout -q --detach FETCH_HEAD; fi
    [ "$(git -C "$d" rev-parse HEAD)" = "$3" ] || { echo "$1 is not at $3"; exit 1; }
}

if [ "${DSF_LOCAL_RUNTIME:-0}" = 1 ]; then
echo "== runtime components (checksum-verified)"
sed "s#shasum -a 256 -c \"\$REPO_DIR/tools/components.sha256\"#sha256sum -c \"$TMPD/c.sha\"#" "$(lf tools/fetch_components.sh)" > "$TMPD/fc.sh"
tr -d '\r' < tools/components.sha256 > "$TMPD/c.sha"
cp "$TMPD/fc.sh" tools/.fc_linux.sh; bash tools/.fc_linux.sh | grep -v '^have ' || true; rm -f tools/.fc_linux.sh
fi   # the Streaming Edition does not package them (app/build.gradle.kts, -PlocalRuntime)

JNI=companion/app/src/main/jniLibs/arm64-v8a
if [ ! -s $JNI/libcasc.so ] || [ ! -s $JNI/libinteriors.so ]; then
    echo "== native game-file reader + indoor maps"
    dep CascLib https://github.com/ladislav-zezula/CascLib.git 38a34665624b8775bb875274b36191b21c38d97b
    dep recastnavigation https://github.com/recastnavigation/recastnavigation.git 6dc1667f580357e8a2154c28b7867bea7e8ad3a7
    H=companion/tools/harvest; I=companion/tools/interiors_native
    cp "$(lf $H/build_native.sh)" $H/.linux.sh; cp "$(lf $I/build_android.sh)" $I/.linux.sh
    CMAKE=$CMAKE_BIN/cmake NINJA=$CMAKE_BIN/ninja sh $H/.linux.sh "$ROOT/.deps/CascLib" && sh $I/.linux.sh
    rm -f $H/.linux.sh $I/.linux.sh
fi

PB=dsforever/src/main/jni/prebuilt
if [ ! -s $PB/openssl/arm64-v8a/libcrypto.a ]; then
    echo "== Moonlight prebuilts (OpenSSL / Opus)"
    dep moonlight-android https://github.com/moonlight-stream/moonlight-android b48494cb96bff23d8886c4775cc4f39a1075495d
    MA=.deps/moonlight-android/app/src/main/jni/moonlight-core
    mkdir -p $PB/openssl/arm64-v8a $PB/opus/arm64-v8a
    cp $MA/openssl/arm64-v8a/libcrypto.a $PB/openssl/arm64-v8a/; cp -r $MA/openssl/include $PB/openssl/
    cp $MA/opus/arm64-v8a/libopus.a $PB/opus/arm64-v8a/; cp -r $MA/opus/include $PB/opus/; cp $MA/Build.txt $PB/
fi

echo "== gradle"
cp "$(lf gradlew)" ./.gradlew-linux; chmod +x ./.gradlew-linux
TASKS=(:app:assembleModernDebug); [ "${1:-}" = "--test" ] && TASKS=(:dsforever:testDebugUnitTest "${TASKS[@]}")
# --release: the signed, minified APK for a GitHub release (needs WC_KEYSTORE, WC_KEYSTORE_PASS, WC_KEY_ALIAS, WC_KEY_PASS in the
# environment: your own key, never in git). Linux Edition 2026-11-20
[ "${1:-}" = "--release" ] && TASKS=(:dsforever:testDebugUnitTest :app:assembleModernRelease)
EXTRA=(); [ "${DSF_LOCAL_RUNTIME:-0}" = 1 ] && EXTRA=(-PlocalRuntime=true)
./.gradlew-linux --no-daemon "${EXTRA[@]}" "${TASKS[@]}"; rm -f ./.gradlew-linux
APK=app/build/outputs/apk/modern/debug/app-modern-debug.apk
[ "${1:-}" = "--release" ] && APK=app/build/outputs/apk/modern/release/app-modern-release.apk
LIST=$(unzip -l "$APK")
for so in libcasc.so libinteriors.so libdsf-moonlight.so; do grep -q "lib/arm64-v8a/$so" <<<"$LIST" || { echo "MISSING $so in the APK"; exit 1; }; done
echo "OK: $APK"
