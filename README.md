# Hikrobot Camera Native + WebRTC Demo

This project contains:

- C++/pybind11 bindings for Hikrobot MVS cameras.
- Python camera tests and utilities.
- `camera_web/`, a WebRTC-oriented camera preview/update version.

Large third-party binaries are intentionally not committed:

- `camera_web/third_party/ffmpeg/bin/ffmpeg.exe`
- `camera_web/third_party/mediamtx/mediamtx.exe`

Place those binaries back in the paths above on the Windows target machine when running the WebRTC demo.

## Typical Windows layout

```text
D:\camera_service_native
├── build or build_py311
├── camera_web
├── include
├── src
├── tests
└── tools
```

The native module must match the Python version:

- Python 3.11: `hikcamera_native.cp311-win_amd64.pyd`
- Python 3.12: `hikcamera_native.cp312-win_amd64.pyd`

MVS Runtime must be installed on the target machine.
