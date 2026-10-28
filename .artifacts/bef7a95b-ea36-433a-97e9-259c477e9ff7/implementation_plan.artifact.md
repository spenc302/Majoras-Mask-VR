# Implementation Plan: Host Asset Compiler Isolation & Standalone Runtime Guarding

Isolate host asset compilation (`2ship.o2r`) from the Android standalone runtime by ensuring the CI build runs only a headless asset extractor/compiler step for packaging, while guarding out desktop-only runtime loops (GLFW, Win32 windowing, desktop input) with `#ifndef __ANDROID__` across the C++ codebase.

---

## Technical Strategy

1. **Host Asset Compilation vs. Android Runtime:**
   - Acknowledge that the CI desktop build step is required solely to generate the `2ship.o2r` asset archive needed by `package-quest.ps1`.
   - Treat the desktop build target in CI as a headless asset compiler rather than a playable PCVR binary.

2. **Guarding Desktop-Only Runtime Code (`#ifndef __ANDROID__`):**
   - Audit desktop-specific runtime systems (GLFW initialization, desktop window event loops, Win32 specific helpers) and wrap them in `#ifndef __ANDROID__` conditional compilation blocks.
   - Ensure Android builds compile exclusively against SDL2 + OpenXR (`lib2ship.so`).

3. **In-App Restart & Texture Diagnostics:**
   - Maintain the robust Android IPC restart handshake (`GameActivity` ⇄ `StateRestartActivity` ⇄ `SetupActivity`), ClassLoader fix, and `MMVR-TextureDiagnostics` logging.

---

## Proposed Changes (Pending Approval)

### Component 1: C++ Runtime Guards (`src/2ship2harkinian/mm/2s2h/`)
- **[MODIFY]** `BenPort.cpp` and window initialization files: Ensure desktop-only window loops and GLFW hooks are guarded with `#ifndef __ANDROID__`.

### Component 2: CI/CD Workflow (`.github/workflows/build-quest-apk.yml`)
- **[MODIFY]** `.github/workflows/build-quest-apk.yml`: Document the role of the Windows build step as a headless asset compiler for `2ship.o2r` generation prior to Quest APK packaging.

---

## Verification Plan

### Automated Checks
- Run `analyze_file` on modified C++ files.
- Execute `tools/build-quest.ps1` locally.

### Manual Verification
- Verify that GitHub Actions CI successfully compiles `2ship.o2r`, packages the Quest APK, and outputs artifacts.
