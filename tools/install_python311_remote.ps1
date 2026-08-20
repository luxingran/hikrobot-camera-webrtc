$ErrorActionPreference = "Stop"

$pythonRoot = "D:\Program\Python311"
$installerDir = "D:\Installers"
$installerPath = Join-Path $installerDir "python-3.11.7-amd64.exe"
$installerUrl = "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
$proxy = "http://192.168.0.250:7890"

if (Test-Path (Join-Path $pythonRoot "python.exe")) {
    & (Join-Path $pythonRoot "python.exe") -c "import sys; print(sys.executable); print(sys.version)"
    exit 0
}

New-Item -ItemType Directory -Force -Path $installerDir | Out-Null
New-Item -ItemType Directory -Force -Path $pythonRoot | Out-Null

if (-not (Test-Path $installerPath)) {
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -Proxy $proxy
    } catch {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
    }
}

$args = @(
    "/quiet",
    "InstallAllUsers=0",
    "PrependPath=0",
    "Include_test=0",
    "Include_doc=0",
    "Include_launcher=0",
    "Include_tcltk=0",
    "TargetDir=$pythonRoot"
)

$proc = Start-Process -FilePath $installerPath -ArgumentList $args -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    throw "Python installer failed with exit code $($proc.ExitCode)"
}

& (Join-Path $pythonRoot "python.exe") -c "import sys, platform; print(sys.executable); print(sys.version); print(platform.architecture()); print(platform.machine())"
