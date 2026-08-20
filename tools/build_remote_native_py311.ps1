$ErrorActionPreference = "Stop"

param(
    [string]$ProjectDir = (Resolve-Path ".").Path,
    [string]$CMake = "cmake",
    [string]$VcVars = "C:\Path\To\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
    [string]$PythonExe = "C:\Path\To\Python311\python.exe",
    [string]$Proxy = ""
)

$BuildDir = Join-Path $ProjectDir "build_py311"

if (-not (Test-Path $PythonExe)) {
    throw "Python 3.11 not found: $PythonExe"
}

& $PythonExe -m pip show pybind11 | Out-Null
if ($LASTEXITCODE -ne 0) {
    try {
        if ($Proxy) {
            & $PythonExe -m pip install --proxy $Proxy "pybind11==2.13.6"
        } else {
            & $PythonExe -m pip install "pybind11==2.13.6"
        }
    } catch {
        & $PythonExe -m pip install "pybind11==2.13.6"
    }
}

$Pybind11Dir = (& $PythonExe -m pybind11 --cmakedir).Trim()

Write-Output "project=$ProjectDir"
Write-Output "python=$PythonExe"
& $PythonExe -c "import sys, platform; print(sys.version); print(platform.architecture()); print(platform.machine())"
Write-Output "cmake=$CMake"
Write-Output "pybind11_DIR=$Pybind11Dir"
Write-Output "build_dir=$BuildDir"

if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}

cmd.exe /c "`"$VcVars`" && cd /d `"$ProjectDir`" && `"$CMake`" -S . -B `"$BuildDir`" -G `"NMake Makefiles`" -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE=`"$PythonExe`" -Dpybind11_DIR=`"$Pybind11Dir`" -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY -DCMAKE_EXE_LINKER_FLAGS=/MANIFEST:NO -DCMAKE_SHARED_LINKER_FLAGS=/MANIFEST:NO -DCMAKE_MODULE_LINKER_FLAGS=/MANIFEST:NO"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

cmd.exe /c "`"$VcVars`" && cd /d `"$ProjectDir`" && `"$CMake`" --build `"$BuildDir`" --config Release"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Output "=== outputs ==="
Get-ChildItem -Path $BuildDir -Recurse -Filter "hikcamera_native*.pyd" |
    Select-Object FullName, Length |
    Format-List
