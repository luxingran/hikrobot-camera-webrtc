# Hikrobot Dual Camera Web Service

A real-time dual industrial camera web service built on the HIKROBOT MVS SDK.

The project manages USB3 Vision and GigE Vision cameras by serial number, converts industrial camera frames for video encoding, pushes H.264 streams through FFmpeg and MediaMTX, and displays multiple live camera feeds in a browser through WebRTC.

This repository is prepared as a public source repository. Real production IP addresses, camera serial numbers, local machine paths, generated logs, certificates, and third-party executable binaries are intentionally excluded.

## Features

- HIKROBOT USB3 Vision / GigE Vision camera support
- Camera binding by serial number instead of device index
- Multi-camera lifecycle management
- Independent capture / encode workers per camera
- ROI / exposure / gain / pixel format configuration support in the camera layer
- Bayer frame conversion to BGR
- FFmpeg H.264 low-latency encoding
- RTSP publishing to MediaMTX
- MediaMTX WebRTC forwarding
- Browser-based multi-camera preview UI
- LAN access support
- Unified startup entrypoint for the web preview service

## Architecture

Overall video pipeline:

```text
HIKROBOT Camera
      │
      │ Raw Bayer Frame
      ▼
CameraManager
      │
      ▼
CameraWorker / EncodeWorker
      │
      │ Bayer -> BGR
      ▼
FFmpeg
      │
      │ H.264
      ▼
RTSP
127.0.0.1:8554
      │
      ▼
MediaMTX
      │
      │ WebRTC
      ▼
Browser
```

Dual-camera runtime:

```text
                  main_web.py
                      │
        ┌─────────────┴─────────────┐
        │                           │
     usb_side                    gige_top
        │                           │
  CameraWorker                CameraWorker
        │                           │
  Bayer -> BGR                Bayer -> BGR
        │                           │
  FFmpegEncoder               FFmpegEncoder
        │                           │
        └────────────┬──────────────┘
                     │
                   RTSP
                     │
                  MediaMTX
                     │
                  WebRTC
                     │
                Web Browser
```

## Project structure

```text
.
├── CMakeLists.txt
├── include/
├── src/
├── tests/
├── tools/
└── camera_web/
    ├── main.py
    ├── main_web.py
    ├── config.example.json
    ├── camera/
    │   ├── native_loader.py
    │   ├── camera_resource.py
    │   ├── hikrobot_camera.py
    │   └── camera_manager.py
    ├── stream/
    │   ├── camera_worker.py
    │   ├── latest_frame.py
    │   ├── stream_manager.py
    │   ├── converter/
    │   │   └── frame_converter.py
    │   ├── encoder/
    │   │   ├── ffmpeg_encoder.py
    │   │   └── h264_encoder.py
    │   └── webrtc/
    │       ├── peer.py
    │       └── server.py
    ├── web/
    │   ├── server.py
    │   └── static/
    │       └── index.html
    └── third_party/
        ├── ffmpeg/
        │   └── README.md
        └── mediamtx/
            ├── README.md
            └── mediamtx.yml
```

## Requirements

### Operating system

Recommended:

```text
Windows 10 / Windows 11 64-bit
```

### Python

Recommended:

```text
Python 3.11 x64
```

Python 3.12 can also work if the native module is built for CPython 3.12.

### HIKROBOT MVS

Install the HIKROBOT MVS SDK / Runtime and the required camera drivers from the official HIKROBOT source.

The SDK is not redistributed in this repository.

### Native module

The native `.pyd` module must match your Python version and architecture:

```text
Python 3.11 -> hikcamera_native.cp311-win_amd64.pyd
Python 3.12 -> hikcamera_native.cp312-win_amd64.pyd
```

### FFmpeg

FFmpeg is used for H.264 encoding.

Expected default path:

```text
camera_web/third_party/ffmpeg/bin/ffmpeg.exe
```

The binary is not committed. Download FFmpeg separately and place it there, or update the code/configuration to point to your system installation.

Check H.264 encoder support:

```powershell
camera_web\third_party\ffmpeg\bin\ffmpeg.exe -encoders | findstr 264
```

### MediaMTX

MediaMTX is used for:

```text
RTSP -> WebRTC
```

Expected default path:

```text
camera_web/third_party/mediamtx/mediamtx.exe
```

The binary is not committed. Download MediaMTX separately and place it there.

## Configuration

Copy the example configuration:

```powershell
copy camera_web\config.example.json camera_web\config.json
```

Edit `camera_web/config.json` with your own camera serial numbers, IP addresses, native build path, and stream settings.

Example:

```json
{
  "native": {
    "module_dir": "D:/path/to/native/build"
  },
  "cameras": {
    "usb_side": {
      "serial": "YOUR_USB_CAMERA_SERIAL",
      "transport": "USB3Vision",
      "pixel_format": "BayerRG8",
      "stream": {
        "width": 1920,
        "height": 1080
      }
    },
    "gige_top": {
      "serial": "YOUR_GIGE_CAMERA_SERIAL",
      "transport": "GigE",
      "ip": "192.168.1.100",
      "pixel_format": "BayerGB8",
      "stream": {
        "width": 1920,
        "height": 1080
      }
    }
  }
}
```

Use camera serial numbers for binding. Do not rely on USB index or enumeration order.

Do not commit your real `config.json` if it contains production camera serial numbers, IP addresses, local paths, or credentials.

## Stream mode

The web preview service is intended for continuous live preview.

For live preview, cameras should normally run with:

```text
TriggerMode = Off
```

This allows the service to continuously grab frames and feed the encoder.

Note:

> Camera ROI is cropping, not scaling.

If the configured stream size is smaller than the full sensor size, the displayed image may be a cropped sensor region unless your camera layer explicitly scales frames.

## Build native module

A typical CMake flow on Windows is:

```powershell
cmake -S . -B build -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

For a parameterized Python 3.11 build script, see:

```text
tools/build_remote_native_py311.ps1
```

## Start

Make sure no other program is occupying the cameras, such as:

- MVS Viewer
- Another Python process
- Another camera service

Then start the web preview service:

```powershell
cd <project-path>\camera_web
python main_web.py
```

After startup, open:

```text
http://<camera-server-ip>:8080
```

The page displays the configured camera streams.

## Network ports

| Port | Protocol | Description |
|---:|---|---|
| `8080` | TCP | Web UI |
| `8554` | TCP | FFmpeg -> MediaMTX RTSP |
| `8889` | TCP | MediaMTX WebRTC HTTP / signaling |
| `8189` | UDP | WebRTC media / ICE |

For normal browser access, use:

```text
http://<camera-server-ip>:8080
```

If WebRTC cannot connect from another machine, check Windows Firewall rules for TCP `8889` and UDP `8189`.

## Video pipeline

Each camera stream follows this path:

```text
Camera
 ↓
grab_frame()
 ↓
Bayer Frame
 ↓
convert_frame()
 ↓
BGR24
 ↓
FFmpeg stdin
 ↓
libx264
 ↓
H.264
 ↓
RTSP
 ↓
MediaMTX
 ↓
WebRTC
 ↓
Browser
```

The FFmpeg encoder is configured for low latency:

```text
libx264
preset=ultrafast
tune=zerolatency
B-frames=0
```

## Module responsibilities

### CameraManager

Owns camera resources and lifecycle:

```text
open
close
device lookup
camera lifecycle
```

### HikrobotCamera

Wraps the HIKROBOT native API:

```text
start
stop
grab frame
convert frame
ROI
exposure
gain
pixel format
```

### CameraWorker / EncodeWorker

Runs an independent worker per camera:

```text
grab
↓
convert
↓
encode
```

### FFmpegEncoder

Encodes raw BGR frames:

```text
BGR24
↓
H.264
↓
RTSP
```

### MediaMTX

Acts as the streaming bridge:

```text
RTSP
↓
WebRTC
↓
Browser
```

### Web server

Serves the browser UI:

```text
HTML
CSS
JavaScript
```

The web server itself does not encode video.

## Stop

Press:

```text
Ctrl + C
```

The service should stop workers, encoders, camera handles, web server, and MediaMTX in order.

## Troubleshooting

### Camera occupied

Error:

```text
MV_CC_OpenDevice failed, ret=0x80000203
```

Usually means the camera is already opened by another process.

Check:

- MVS Viewer
- Other Python programs
- Another camera service

Close the occupying program and restart this service.

### GetImageBuffer timeout

Error:

```text
MV_CC_GetImageBuffer failed, ret=0x80000007
```

Common cause:

```text
TriggerMode = On
```

but no trigger signal is being received.

For continuous web preview, use:

```text
TriggerMode = Off
```

### PixelFormat set failed

Example:

```text
MV_CC_SetEnumValue(PixelFormat) failed
```

Different camera models support different pixel formats. Prefer keeping the camera's current supported pixel format unless you have verified the target format in MVS Viewer.

### Web page opens but video is black

Check the pipeline in order:

```text
Camera
↓
FFmpeg
↓
RTSP
↓
MediaMTX
↓
WebRTC
```

First test the MediaMTX WebRTC pages directly:

```text
http://<camera-server-ip>:8889/<stream-name>
```

If MediaMTX can play the stream, the video pipeline is working and the issue is likely in the web UI.

### WebRTC cannot connect

Check Windows Firewall:

```text
TCP 8889
UDP 8189
```

WebRTC media often uses UDP `8189`.

### Native module import failed

Check that:

- Python is x64.
- The `.pyd` file matches your Python version.
- MVS Runtime is installed.
- The native build directory is included in `native.module_dir`.

## Development

Development scripts are provided for testing individual parts of the system:

```text
tests/test_import.py              Native import test
tests/test_enum_detail.py         Camera enumeration
tests/test_save_convert.py        Capture / convert / save test
camera_web/test_stream.py         Camera -> frame conversion path
camera_web/stream/test_dual_encoder.py  Dual camera encoder path
```

Production-style preview should use:

```powershell
python camera_web\main_web.py
```

## Safety notes

Industrial camera parameters may persist across sessions. Be careful with:

- `TriggerMode`
- `TriggerSource`
- `PixelFormat`
- `Width`, `Height`, `OffsetX`, `OffsetY`
- `ExposureTime`
- `Gain`

When testing with production equipment, start with read-only enumeration and avoid writing camera nodes unless the camera is not being used by another process.

## Roadmap

Possible future work:

- REST API for camera status/control
- Real-time FPS and latency dashboard
- PLC-triggered snapshot flow
- AI inference integration
- OK / NG result overlay
- Snapshot image saving
- Online camera parameter configuration
- WebSocket status push
- Windows Service / startup integration
- Log rotation and health monitoring

## License

This is an independent community project and is not affiliated with,
endorsed by, or sponsored by HIKROBOT.

HIKROBOT and MVS are trademarks and/or products of their respective owners.
The HIKROBOT MVS SDK is not distributed with this project and must be
obtained separately from HIKROBOT.

FFmpeg and MediaMTX are third-party projects and are subject to their
respective licenses.

Unless otherwise noted, the MIT License in this repository applies only
to the original source code authored for this project. It does not grant
any rights to third-party software, SDKs, trademarks, or other materials.
