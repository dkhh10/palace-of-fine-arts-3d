#!/bin/zsh
# Fetch the pinned Phase 6 binaries into tools/bin (gitignored): gltfpack 1.2 (native, KTX2 support) and
# KTX-Software 4.4.2 (toktx, ktx + libktx) for Darwin arm64. Idempotent; re-run after a clone.
set -e; cd "$(dirname "$0")"; mkdir -p bin lib dl
curl -sL -o dl/gltfpack-macos.zip https://github.com/zeux/meshoptimizer/releases/download/v1.2/gltfpack-macos.zip
unzip -o -q dl/gltfpack-macos.zip -d dl/gltfpack && cp dl/gltfpack/gltfpack bin/
curl -sL -o dl/ktx.pkg https://github.com/KhronosGroup/KTX-Software/releases/download/v4.4.2/KTX-Software-4.4.2-Darwin-arm64.pkg
rm -rf dl/ktx_expanded; pkgutil --expand-full dl/ktx.pkg dl/ktx_expanded
cp dl/ktx_expanded/KTX-Software-4.4.2-Darwin-arm64-tools.pkg/Payload/usr/local/bin/{ktx,toktx} bin/
cp dl/ktx_expanded/KTX-Software-4.4.2-Darwin-arm64-library.pkg/Payload/usr/local/lib/libktx.4.dylib lib/
chmod +x bin/*; xattr -d com.apple.quarantine bin/* lib/* 2>/dev/null || true
codesign -f -s - bin/toktx bin/ktx 2>/dev/null   # the pkg binaries carry LC_RPATH @executable_path/../lib already
./bin/gltfpack 2>&1 | head -1; ./bin/toktx --version
