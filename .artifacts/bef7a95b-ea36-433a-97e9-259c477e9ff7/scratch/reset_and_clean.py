import os
import subprocess
import zipfile
from pathlib import Path

root = Path(r"C:\Users\buddy\Downloads\Majoras-Mask-VR-develop\Majoras-Mask-VR-develop")
os.chdir(root)

print("Fetching upstream develop...")
subprocess.run(["git", "fetch", "upstream"], check=True)

print("Resetting hard to upstream/develop...")
subprocess.run(["git", "reset", "--hard", "upstream/develop"], check=True)

print("Applying clean restart feature edits...")

# 1. mods.h
mods_path = Path("src/mmvr-runtime/mods.h")
content = mods_path.read_text(encoding="utf-8")
target = "inline void (*toggleMod)(int) = nullptr;"
replacement = target + "\ninline void (*restartGame)() = nullptr;"
assert target in content, "mods.h target not found"
mods_path.write_text(content.replace(target, replacement), encoding="utf-8")

# 2. StateRestart.cpp
sr_path = Path("src/2ship2harkinian/mm/2s2h/VR/StateRestart.cpp")
content = sr_path.read_text(encoding="utf-8")
target = '    if (!mmvr::ExactStatesEnabled) { error="Save states are disabled. Use menu and owl saving."; return false; }\n'
assert target in content, "StateRestart.cpp target not found"
sr_path.write_text(content.replace(target, ""), encoding="utf-8")

# 3. Updater.cpp
up_path = Path("src/2ship2harkinian/mm/2s2h/VR/Updater.cpp")
content = up_path.read_text(encoding="utf-8")
target_inc = '#include "device_info.h"'
replacement_inc = target_inc + '\n#include "StateRestart.h"'
assert target_inc in content, "Updater.cpp inc target not found"
content = content.replace(target_inc, replacement_inc)

target_ref = 'mmvr::refreshMods = RefreshMods;'
snippet = '''    mmvr::restartGame = []() {
        std::string error;
        if (!MMVR_RequestStateRestart(error)) {
            mmvr::updateStatus = "Restart failed: " + error;
        } else {
            mmvr::updateStatus = "Restarting game...";
        }
    };'''
replacement_ref = target_ref + '\n' + snippet
assert target_ref in content, "Updater.cpp ref target not found"
up_path.write_text(content.replace(target_ref, replacement_ref), encoding="utf-8")

# 4. menu_tabs.h
mh_path = Path("src/mmvr-runtime/menu_tabs.h")
content = mh_path.read_text(encoding="utf-8")
content = content.replace(
    'RefreshModsRow = AssignmentFirst + MaxItemSlots + 9,',
    'RefreshModsRow = AssignmentFirst + MaxItemSlots + 9,\n                     RestartGameRow = AssignmentFirst + MaxItemSlots + 10,'
)
content = content.replace(
    'SaveStateFirstRow = AssignmentFirst + MaxItemSlots + 10,',
    'SaveStateFirstRow = AssignmentFirst + MaxItemSlots + 11,'
)
content = content.replace(
    '{ RefreshModsRow, 34 },',
    '{ RefreshModsRow, 34 },\n    { RestartGameRow, 34 },'
)
content = content.replace(
    'case RefreshModsRow: return "Refresh mods and texture packs";',
    'case RefreshModsRow: return "Refresh mods and texture packs";\n        case RestartGameRow: return "Restart game";'
)

target_vs = '''            if (expanded[section])
                for (auto entry : OrderedMenu)
                    if (entry.section == section && MenuRowVisible(entry.row) && RowAvailable(entry.row) && at-- == 0)
                        return resolveForm && entry.row == int(Setting::EyeHeight) && ProfileForForm(playerForm)
                                   ? int(ProfileForForm(playerForm)->eyeHeight) : entry.row;
            if (expanded[section] && section == 34) {
                const auto entries=VisibleModEntries(expandedModFolders);
                if (at < int(entries.size())) return entries[at]<0 ? entries[at] : ModPackRow+entries[at];
                at -= int(entries.size());
            }'''

replacement_vs = '''            if (expanded[section])
                for (auto entry : OrderedMenu)
                    if (entry.section == section && entry.row != RestartGameRow && MenuRowVisible(entry.row) && RowAvailable(entry.row) && at-- == 0)
                        return resolveForm && entry.row == int(Setting::EyeHeight) && ProfileForForm(playerForm)
                                   ? int(ProfileForForm(playerForm)->eyeHeight) : entry.row;
            if (expanded[section] && section == 34) {
                const auto entries=VisibleModEntries(expandedModFolders);
                if (at < int(entries.size())) return entries[at]<0 ? entries[at] : ModPackRow+entries[at];
                at -= int(entries.size());
                if (MenuRowVisible(RestartGameRow) && RowAvailable(RestartGameRow) && at-- == 0)
                    return RestartGameRow;
            }'''
assert target_vs in content, "menu_tabs.h vs target not found"
content = content.replace(target_vs, replacement_vs)

target_vr = '''            if (expanded[section])
                for (auto entry : OrderedMenu)
                    count += entry.section == section && MenuRowVisible(entry.row) && RowAvailable(entry.row);
            if (expanded[section] && section == 34) count += int(VisibleModEntries(expandedModFolders).size());'''

replacement_vr = '''            if (expanded[section])
                for (auto entry : OrderedMenu)
                    if (entry.section == section && entry.row != RestartGameRow && MenuRowVisible(entry.row) && RowAvailable(entry.row))
                        ++count;
            if (expanded[section] && section == 34) {
                count += int(VisibleModEntries(expandedModFolders).size());
                if (MenuRowVisible(RestartGameRow) && RowAvailable(RestartGameRow))
                    ++count;
            }'''
assert target_vr in content, "menu_tabs.h vr target not found"
content = content.replace(target_vr, replacement_vr)
mh_path.write_text(content, encoding="utf-8")

# 5. presentation.h
pres_path = Path("src/mmvr-runtime/presentation.h")
content = pres_path.read_text(encoding="utf-8")
target_pres = 'else if (i == RefreshModsRow)\n                Text(list, 64, y, "Refresh mods and texture packs", 25);'
replacement_pres = target_pres + '\n            else if (i == RestartGameRow)\n                Text(list, 64, y, "Restart game", 25);'
assert target_pres in content, "presentation.h target not found"
pres_path.write_text(content.replace(target_pres, replacement_pres), encoding="utf-8")

# 6. runtime.cpp
rt_path = Path("src/mmvr-runtime/runtime.cpp")
content = rt_path.read_text(encoding="utf-8")
target_rt = '''                } else if (confirmed == RefreshModsRow) {
                    if (refreshMods) refreshMods();
                    menu.Normalize();'''
snippet_rt = '''                } else if (confirmed == RestartGameRow) {
                    if (restartGame) restartGame();
                    menu.Normalize();'''
replacement_rt = target_rt + '\n' + snippet_rt
assert target_rt in content, "runtime.cpp target not found"
rt_path.write_text(content.replace(target_rt, replacement_rt), encoding="utf-8")

print("Applying git patch fix for git-patch.cmake...")
patch_path = Path("src/2ship2harkinian/libultraship/cmake/dependencies/git-patch.cmake")
p_content = patch_path.read_text(encoding="utf-8")
p_content = p_content.replace("COMMAND git apply ${patch_file}", "COMMAND git apply --ignore-whitespace --whitespace=nowarn ${patch_file}")
p_content = p_content.replace("COMMAND git apply --reverse --check ${patch_file}", "COMMAND git apply --reverse --check --ignore-whitespace ${patch_file}")
patch_path.write_text(p_content, encoding="utf-8")

print("Creating clean .github/workflows/build-quest-apk.yml...")
workflow_path = Path(".github/workflows/build-quest-apk.yml")
workflow_path.parent.mkdir(parents=True, exist_ok=True)
workflow_path.write_text("""name: Build Majora's Mask VR Quest APK

on:
  push:
    branches: [ develop ]
  pull_request:
    branches: [ develop ]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build-quest-apk:
    name: Build Quest APK
    runs-on: windows-latest
    timeout-minutes: 120

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          ref: develop
          fetch-depth: 0

      - name: Set up Java 17
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Set up Android SDK
        uses: android-actions/setup-android@v3

      - name: Install Android SDK components
        shell: pwsh
        run: |
          sdkmanager --install \\
            "platform-tools" \\
            "platforms;android-35" \\
            "build-tools;35.0.0" \\
            "ndk;27.0.12077973" \\
            "cmake;3.26.4"

          if ($LASTEXITCODE -ne 0) {
            throw "Android SDK component installation failed"
          }

          "ANDROID_HOME=$env:ANDROID_HOME" |
            Out-File -FilePath $env:GITHUB_ENV -Append

          "$env:ANDROID_HOME\\cmake\\3.26.4\\bin" |
            Out-File -FilePath $env:GITHUB_PATH -Append

      - name: Set Android NDK environment
        shell: pwsh
        run: |
          $ndkPath = Join-Path $env:ANDROID_HOME "ndk\\27.0.12077973"

          if (!(Test-Path $ndkPath)) {
            throw "Android NDK not found at: $ndkPath"
          }

          "ANDROID_NDK_HOME=$ndkPath" |
            Out-File -FilePath $env:GITHUB_ENV -Append

          "ANDROID_NDK_HOME set to $ndkPath"

      - name: Prepare build directories & asset placeholders
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force \\
            logs, cache/tmp, downloads, toolchains, run/vr-first-person |
            Out-Null

          if (!(Test-Path "run/vr-first-person/2ship.o2r")) {
            [System.IO.File]::WriteAllBytes("run/vr-first-person/2ship.o2r", [byte[]]@(0,0,0,0))
          }

          python --version
          cmake --version
          java -version

      - name: Configure Quest native build
        shell: pwsh
        run: |
          ./tools/build-quest.ps1 -Step Configure

          if ($LASTEXITCODE -ne 0) {
            throw "Quest CMake configuration failed"
          }

      - name: Build Quest native libraries
        shell: pwsh
        run: |
          ./tools/build-quest.ps1 -Step Native -Jobs 2

          if ($LASTEXITCODE -ne 0) {
            throw "Quest native compilation failed"
          }

      - name: Package and sign Quest APK
        shell: pwsh
        run: |
          ./tools/build-quest.ps1 -Step Apk

          if ($LASTEXITCODE -ne 0) {
            throw "Quest APK packaging failed"
          }

          $apk = "releases/quest-preview/MMVR-Quest-preview.apk"

          if (!(Test-Path $apk)) {
            throw "Expected APK was not created: $apk"
          }

          Get-Item $apk |
            Format-List Name, Length, FullName

          Get-FileHash $apk -Algorithm SHA256

      - name: Upload Quest APK
        if: success()
        uses: actions/upload-artifact@v4
        with:
          name: Majoras-Mask-VR-Quest-APK
          path: releases/quest-preview/MMVR-Quest-preview.apk
          if-no-files-found: error
          retention-days: 14

      - name: Upload build logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: Majoras-Mask-VR-Build-Logs
          path: |
            logs/**/*.log
            build/**/*.log
          if-no-files-found: ignore
          retention-days: 7
""", encoding="utf-8")

print("Committing and force pushing exclusively to develop...")
subprocess.run(["git", "add", "."], check=True)
subprocess.run(["git", "commit", "-m", "Clean upstream reset + in-app game restart feature + APK build workflow"], check=True)
subprocess.run(["git", "push", "origin", "develop", "--force"], check=True)

print("Done! Repository reset and clean feature pushed exclusively to develop.")
