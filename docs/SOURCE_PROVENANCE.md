# Source provenance

Status date: 2026-07-17

## Reviewed copies

| Copy | Role | Evidence |
|---|---|---|
| Local desktop working directory `仓库追踪系统` | latest working source | Git `master` at `2d5853ec06fa6351f8d7e6022563bdc16ab6f5ce`, with later dirty/untracked development files |
| Historical archive `仓库追踪系统.zip` | read-only historical baseline | SHA-256 `5647fb1c0925cbc65a9b257cc2b5e602ed24548cebf7b2da8b2b0c18ef5a1561` |

The original desktop directory remains untouched. The public candidate was created in a separate working directory.

## Comparison method and result

Generated/cache/private paths were excluded from the source comparison:

```text
.git
.gradle
.idea
build
__pycache__
*.db and SQLite sidecars
local.properties
real config.h files
```

After those exclusions:

```text
desktop effective files: 44
ZIP effective files:     39
byte-identical paths:    37
common paths differing:  README.md, esp32_tag/esp32_tag.ino
desktop-only relevant:   Gradle Wrapper files and docs/部署操作步骤.md
```

The desktop tag firmware contains later deep-sleep, motion/Hall wake and display-management work. Its README and Gradle wrapper/deployment material are also newer. Therefore:

> The desktop directory is the latest source candidate; the ZIP is retained as a read-only historical baseline.

This version-order decision does **not** prove that the later desktop code was hardware retested.

## Publication transformations

The separate public candidate:

- excludes original `.git`, databases, local configs, IDE/Gradle/PlatformIO output and caches;
- preserves the latest application and firmware source;
- adds example-only configuration templates;
- adds a PlatformIO adapter to reproduce Arduino IDE implicit declarations;
- pins Gradle 8.2 because the historical Gradle 9 wrapper is incompatible with Android Gradle Plugin 8.2.2;
- enables Android `BuildConfig` generation required by `ApiClient`;
- corrects region authority, deep-sleep QUERY claims and unavailable sensor semantics;
- removes historical private-LAN addresses;
- adds open-source documentation, tests, CI and release gates.

## Traceability rule

The future GitHub repository starts with a clean public history. It is not a mirror of the original dirty Git history. This file preserves the source lineage without publishing local metadata, caches or private runtime configuration.
