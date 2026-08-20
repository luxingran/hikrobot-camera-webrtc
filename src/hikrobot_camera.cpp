#include "hikrobot_camera.hpp"

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <MvCameraControl.h>

#include <cstring>
#include <filesystem>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace hikcamera {
namespace {

class MvsApi {
public:
    using EnumDevicesFn = int(__stdcall*)(unsigned int, MV_CC_DEVICE_INFO_LIST*);
    using CreateHandleFn = int(__stdcall*)(void**, const MV_CC_DEVICE_INFO*);
    using DestroyHandleFn = int(__stdcall*)(void*);
    using OpenDeviceFn = int(__stdcall*)(void*, unsigned int, unsigned short);
    using CloseDeviceFn = int(__stdcall*)(void*);
    using StartGrabbingFn = int(__stdcall*)(void*);
    using StopGrabbingFn = int(__stdcall*)(void*);
    using ClearImageBufferFn = int(__stdcall*)(void*);
    using GetIntValueExFn = int(__stdcall*)(void*, const char*, MVCC_INTVALUE_EX*);
    using SetIntValueExFn = int(__stdcall*)(void*, const char*, int64_t);
    using GetFloatValueFn = int(__stdcall*)(void*, const char*, MVCC_FLOATVALUE*);
    using SetFloatValueFn = int(__stdcall*)(void*, const char*, float);
    using GetEnumValueFn = int(__stdcall*)(void*, const char*, MVCC_ENUMVALUE*);
    using SetEnumValueFn = int(__stdcall*)(void*, const char*, unsigned int);
    using SetCommandValueFn = int(__stdcall*)(void*, const char*);
    using GetImageBufferFn = int(__stdcall*)(void*, MV_FRAME_OUT*, unsigned int);
    using FreeImageBufferFn = int(__stdcall*)(void*, MV_FRAME_OUT*);
    using ConvertPixelTypeFn = int(__stdcall*)(void*, MV_CC_PIXEL_CONVERT_PARAM*);
    using SaveImageToFileFn = int(__stdcall*)(void*, MV_SAVE_IMG_TO_FILE_PARAM*);

    MvsApi() {
        const wchar_t* candidates[] = {
            L"C:\\Program Files (x86)\\Common Files\\MVS\\Runtime\\Win64_x64\\MvCameraControl.dll",
            L"MvCameraControl.dll",
        };

        for (const auto* candidate : candidates) {
            module_ = LoadLibraryW(candidate);
            if (module_ != nullptr) {
                break;
            }
        }

        if (module_ == nullptr) {
            throw std::runtime_error("Failed to load MvCameraControl.dll");
        }

        enum_devices = load<EnumDevicesFn>("MV_CC_EnumDevices");
        create_handle = load<CreateHandleFn>("MV_CC_CreateHandle");
        destroy_handle = load<DestroyHandleFn>("MV_CC_DestroyHandle");
        open_device = load<OpenDeviceFn>("MV_CC_OpenDevice");
        close_device = load<CloseDeviceFn>("MV_CC_CloseDevice");
        start_grabbing = load<StartGrabbingFn>("MV_CC_StartGrabbing");
        stop_grabbing = load<StopGrabbingFn>("MV_CC_StopGrabbing");
        clear_image_buffer = load<ClearImageBufferFn>("MV_CC_ClearImageBuffer");
        get_int_value_ex = load<GetIntValueExFn>("MV_CC_GetIntValueEx");
        set_int_value_ex = load<SetIntValueExFn>("MV_CC_SetIntValueEx");
        get_float_value = load<GetFloatValueFn>("MV_CC_GetFloatValue");
        set_float_value = load<SetFloatValueFn>("MV_CC_SetFloatValue");
        get_enum_value = load<GetEnumValueFn>("MV_CC_GetEnumValue");
        set_enum_value = load<SetEnumValueFn>("MV_CC_SetEnumValue");
        set_command_value = load<SetCommandValueFn>("MV_CC_SetCommandValue");
        get_image_buffer = load<GetImageBufferFn>("MV_CC_GetImageBuffer");
        free_image_buffer = load<FreeImageBufferFn>("MV_CC_FreeImageBuffer");
        convert_pixel_type = load<ConvertPixelTypeFn>("MV_CC_ConvertPixelType");
        save_image_to_file = load<SaveImageToFileFn>("MV_CC_SaveImageToFile");
    }

    ~MvsApi() {
        if (module_ != nullptr) {
            FreeLibrary(module_);
        }
    }

    MvsApi(const MvsApi&) = delete;
    MvsApi& operator=(const MvsApi&) = delete;

    EnumDevicesFn enum_devices = nullptr;
    CreateHandleFn create_handle = nullptr;
    DestroyHandleFn destroy_handle = nullptr;
    OpenDeviceFn open_device = nullptr;
    CloseDeviceFn close_device = nullptr;
    StartGrabbingFn start_grabbing = nullptr;
    StopGrabbingFn stop_grabbing = nullptr;
    ClearImageBufferFn clear_image_buffer = nullptr;
    GetIntValueExFn get_int_value_ex = nullptr;
    SetIntValueExFn set_int_value_ex = nullptr;
    GetFloatValueFn get_float_value = nullptr;
    SetFloatValueFn set_float_value = nullptr;
    GetEnumValueFn get_enum_value = nullptr;
    SetEnumValueFn set_enum_value = nullptr;
    SetCommandValueFn set_command_value = nullptr;
    GetImageBufferFn get_image_buffer = nullptr;
    FreeImageBufferFn free_image_buffer = nullptr;
    ConvertPixelTypeFn convert_pixel_type = nullptr;
    SaveImageToFileFn save_image_to_file = nullptr;

private:
    template <typename Fn>
    Fn load(const char* name) {
        auto* address = GetProcAddress(module_, name);
        if (address == nullptr) {
            throw std::runtime_error(std::string("Missing MVS SDK symbol: ") + name);
        }
        return reinterpret_cast<Fn>(address);
    }

    HMODULE module_ = nullptr;
};

MvsApi& mvs() {
    static MvsApi api;
    return api;
}

std::string error_message(const std::string& action, int code) {
    std::ostringstream oss;
    oss << action << " failed, ret=0x" << std::hex << std::nouppercase << code;
    return oss.str();
}

void check_ok(int code, const std::string& action) {
    if (code != MV_OK) {
        throw std::runtime_error(error_message(action, code));
    }
}

template <typename Array>
std::string chars_to_string(const Array& values) {
    std::string result;
    for (auto value : values) {
        if (value == 0) {
            break;
        }
        result.push_back(static_cast<char>(value));
    }
    return result;
}

DeviceInfo to_device_info(int index, const MV_CC_DEVICE_INFO* device) {
    DeviceInfo info;
    info.index = index;

    if (device == nullptr) {
        return info;
    }

    if (device->nTLayerType == MV_GIGE_DEVICE) {
        const auto& gige = device->SpecialInfo.stGigEInfo;
        info.transport = "GigE";
        info.model = chars_to_string(gige.chModelName);
        info.serial = chars_to_string(gige.chSerialNumber);
        info.user_defined_name = chars_to_string(gige.chUserDefinedName);

        const auto ip = gige.nCurrentIp;
        std::ostringstream oss;
        oss << ((ip & 0xff000000) >> 24) << "."
            << ((ip & 0x00ff0000) >> 16) << "."
            << ((ip & 0x0000ff00) >> 8) << "."
            << (ip & 0x000000ff);
        info.ip = oss.str();
    } else if (device->nTLayerType == MV_USB_DEVICE) {
        const auto& usb = device->SpecialInfo.stUsb3VInfo;
        info.transport = "USB3Vision";
        info.model = chars_to_string(usb.chModelName);
        info.serial = chars_to_string(usb.chSerialNumber);
        info.user_defined_name = chars_to_string(usb.chUserDefinedName);
    } else {
        info.transport = "Unknown";
    }

    return info;
}

uint32_t bytes_per_pixel(uint32_t pixel_format) {
    switch (pixel_format) {
        case PixelType_Gvsp_RGB8_Packed:
        case PixelType_Gvsp_BGR8_Packed:
            return 3;
        case PixelType_Gvsp_Mono8:
        case PixelType_Gvsp_BayerGR8:
        case PixelType_Gvsp_BayerRG8:
        case PixelType_Gvsp_BayerGB8:
        case PixelType_Gvsp_BayerBG8:
            return 1;
        default:
            return 3;
    }
}

MV_SAVE_IAMGE_TYPE parse_image_type(const std::string& image_type) {
    if (image_type == "bmp" || image_type == "BMP") {
        return MV_Image_Bmp;
    }
    if (image_type == "jpg" || image_type == "jpeg" || image_type == "JPG" || image_type == "JPEG") {
        return MV_Image_Jpeg;
    }
    if (image_type == "png" || image_type == "PNG") {
        return MV_Image_Png;
    }
    if (image_type == "tif" || image_type == "tiff" || image_type == "TIF" || image_type == "TIFF") {
        return MV_Image_Tif;
    }
    throw std::runtime_error("Unsupported image type: " + image_type);
}

struct ImageBufferGuard {
    void* handle = nullptr;
    MV_FRAME_OUT* frame = nullptr;
    bool active = false;

    ~ImageBufferGuard() {
        if (active && handle != nullptr && frame != nullptr) {
            mvs().free_image_buffer(handle, frame);
        }
    }
};

}  // namespace

HikrobotCamera::HikrobotCamera(std::string serial) : serial_(std::move(serial)) {}

HikrobotCamera::~HikrobotCamera() {
    try {
        close();
    } catch (...) {
    }
}

std::vector<DeviceInfo> HikrobotCamera::enum_devices() {
    MV_CC_DEVICE_INFO_LIST device_list;
    std::memset(&device_list, 0, sizeof(device_list));

    check_ok(
        mvs().enum_devices(MV_GIGE_DEVICE | MV_USB_DEVICE, &device_list),
        "MV_CC_EnumDevices");

    std::vector<DeviceInfo> devices;
    devices.reserve(device_list.nDeviceNum);

    for (unsigned int i = 0; i < device_list.nDeviceNum; ++i) {
        devices.push_back(to_device_info(static_cast<int>(i), device_list.pDeviceInfo[i]));
    }

    return devices;
}

void HikrobotCamera::open() {
    if (open_) {
        return;
    }

    MV_CC_DEVICE_INFO_LIST device_list;
    std::memset(&device_list, 0, sizeof(device_list));

    check_ok(
        mvs().enum_devices(MV_GIGE_DEVICE | MV_USB_DEVICE, &device_list),
        "MV_CC_EnumDevices");

    const MV_CC_DEVICE_INFO* selected = nullptr;
    for (unsigned int i = 0; i < device_list.nDeviceNum; ++i) {
        const auto* candidate = device_list.pDeviceInfo[i];
        const auto info = to_device_info(static_cast<int>(i), candidate);
        if (serial_.empty() || info.serial == serial_) {
            selected = candidate;
            if (serial_.empty()) {
                serial_ = info.serial;
            }
            break;
        }
    }

    if (selected == nullptr) {
        throw std::runtime_error(
            serial_.empty() ? "No Hikrobot MVS device found"
                            : "No Hikrobot MVS device found for serial " + serial_);
    }

    check_ok(mvs().create_handle(&handle_, selected), "MV_CC_CreateHandle");

    const int open_ret = mvs().open_device(handle_, MV_ACCESS_Exclusive, 0);
    if (open_ret != MV_OK) {
        mvs().destroy_handle(handle_);
        handle_ = nullptr;
        throw std::runtime_error(error_message("MV_CC_OpenDevice", open_ret));
    }

    open_ = true;
}

void HikrobotCamera::start() {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    if (grabbing_) {
        return;
    }
    check_ok(mvs().start_grabbing(handle_), "MV_CC_StartGrabbing");
    grabbing_ = true;
}

void HikrobotCamera::configure_software_trigger() {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }

    check_ok(
        mvs().set_enum_value(handle_, "AcquisitionMode", 2),
        "MV_CC_SetEnumValue(AcquisitionMode=Continuous)");
    check_ok(
        mvs().set_enum_value(handle_, "TriggerMode", MV_TRIGGER_MODE_ON),
        "MV_CC_SetEnumValue(TriggerMode=On)");
    check_ok(
        mvs().set_enum_value(handle_, "TriggerSource", MV_TRIGGER_SOURCE_SOFTWARE),
        "MV_CC_SetEnumValue(TriggerSource=Software)");
}

void HikrobotCamera::trigger() {
    if (!grabbing_) {
        throw std::runtime_error("Camera is not grabbing");
    }
    check_ok(mvs().set_command_value(handle_, "TriggerSoftware"), "MV_CC_SetCommandValue(TriggerSoftware)");
}

void HikrobotCamera::set_int(const std::string& name, int64_t value) {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    check_ok(mvs().set_int_value_ex(handle_, name.c_str(), value), "MV_CC_SetIntValueEx(" + name + ")");
}

void HikrobotCamera::set_float(const std::string& name, float value) {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    check_ok(mvs().set_float_value(handle_, name.c_str(), value), "MV_CC_SetFloatValue(" + name + ")");
}

void HikrobotCamera::set_enum(const std::string& name, uint32_t value) {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    check_ok(mvs().set_enum_value(handle_, name.c_str(), value), "MV_CC_SetEnumValue(" + name + ")");
}

IntParameter HikrobotCamera::get_int(const std::string& name) {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    MVCC_INTVALUE_EX value;
    std::memset(&value, 0, sizeof(value));
    check_ok(mvs().get_int_value_ex(handle_, name.c_str(), &value), "MV_CC_GetIntValueEx(" + name + ")");
    return IntParameter{value.nCurValue, value.nMin, value.nMax, value.nInc};
}

FloatParameter HikrobotCamera::get_float(const std::string& name) {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    MVCC_FLOATVALUE value;
    std::memset(&value, 0, sizeof(value));
    check_ok(mvs().get_float_value(handle_, name.c_str(), &value), "MV_CC_GetFloatValue(" + name + ")");
    return FloatParameter{value.fCurValue, value.fMin, value.fMax};
}

EnumParameter HikrobotCamera::get_enum(const std::string& name) {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    MVCC_ENUMVALUE value;
    std::memset(&value, 0, sizeof(value));
    check_ok(mvs().get_enum_value(handle_, name.c_str(), &value), "MV_CC_GetEnumValue(" + name + ")");

    EnumParameter result;
    result.value = value.nCurValue;
    result.supported_values.reserve(value.nSupportedNum);
    for (unsigned int i = 0; i < value.nSupportedNum; ++i) {
        result.supported_values.push_back(value.nSupportValue[i]);
    }
    return result;
}

void HikrobotCamera::set_exposure(float exposure_us) {
    set_float("ExposureTime", exposure_us);
}

void HikrobotCamera::set_gain(float gain) {
    set_float("Gain", gain);
}

void HikrobotCamera::set_roi(int64_t width, int64_t height, int64_t offset_x, int64_t offset_y) {
    if (grabbing_) {
        throw std::runtime_error("ROI cannot be changed while grabbing");
    }

    // Some cameras require offsets to be reduced before shrinking width/height.
    set_int("OffsetX", 0);
    set_int("OffsetY", 0);
    set_int("Width", width);
    set_int("Height", height);
    set_int("OffsetX", offset_x);
    set_int("OffsetY", offset_y);
}

void HikrobotCamera::set_pixel_format(uint32_t pixel_format) {
    if (grabbing_) {
        throw std::runtime_error("PixelFormat cannot be changed while grabbing");
    }
    set_enum("PixelFormat", pixel_format);
}

Frame HikrobotCamera::get_frame(uint32_t timeout_ms) {
    if (!grabbing_) {
        throw std::runtime_error("Camera is not grabbing");
    }

    MV_FRAME_OUT frame;
    std::memset(&frame, 0, sizeof(frame));

    check_ok(mvs().get_image_buffer(handle_, &frame, timeout_ms), "MV_CC_GetImageBuffer");

    ImageBufferGuard guard{handle_, &frame, true};

    Frame result;
    result.width = frame.stFrameInfo.nWidth;
    result.height = frame.stFrameInfo.nHeight;
    result.pixel_type = static_cast<uint32_t>(frame.stFrameInfo.enPixelType);
    result.frame_num = frame.stFrameInfo.nFrameNum;
    result.frame_len = frame.stFrameInfo.nFrameLen;
    result.exposure_us = frame.stFrameInfo.fExposureTime;
    result.gain = frame.stFrameInfo.fGain;
    result.average_brightness = frame.stFrameInfo.nAverageBrightness;

    if (frame.pBufAddr != nullptr && frame.stFrameInfo.nFrameLen > 0) {
        const auto* begin = reinterpret_cast<const uint8_t*>(frame.pBufAddr);
        result.data.assign(begin, begin + frame.stFrameInfo.nFrameLen);
    }

    const int free_ret = mvs().free_image_buffer(handle_, &frame);
    guard.active = false;
    check_ok(free_ret, "MV_CC_FreeImageBuffer");

    return result;
}

ConvertedFrame HikrobotCamera::convert_frame(const Frame& frame, uint32_t dst_pixel_format) {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    if (frame.data.empty()) {
        throw std::runtime_error("Frame data is empty");
    }

    ConvertedFrame result;
    result.width = frame.width;
    result.height = frame.height;
    result.pixel_type = dst_pixel_format;

    const auto output_size =
        static_cast<size_t>(frame.width) *
        static_cast<size_t>(frame.height) *
        static_cast<size_t>(bytes_per_pixel(dst_pixel_format));
    result.data.resize(output_size);

    MV_CC_PIXEL_CONVERT_PARAM param;
    std::memset(&param, 0, sizeof(param));
    param.nWidth = frame.width;
    param.nHeight = frame.height;
    param.enSrcPixelType = static_cast<MvGvspPixelType>(frame.pixel_type);
    param.pSrcData = const_cast<unsigned char*>(reinterpret_cast<const unsigned char*>(frame.data.data()));
    param.nSrcDataLen = frame.frame_len;
    param.enDstPixelType = static_cast<MvGvspPixelType>(dst_pixel_format);
    param.pDstBuffer = result.data.data();
    param.nDstBufferSize = static_cast<unsigned int>(result.data.size());

    check_ok(mvs().convert_pixel_type(handle_, &param), "MV_CC_ConvertPixelType");

    result.data_len = param.nDstLen;
    result.data.resize(result.data_len);
    return result;
}

void HikrobotCamera::save_frame(
    const Frame& frame,
    const std::string& path,
    const std::string& image_type,
    uint32_t quality) {
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }
    if (frame.data.empty()) {
        throw std::runtime_error("Frame data is empty");
    }
    if (path.size() >= 256) {
        throw std::runtime_error("Image path is too long for MVS SDK");
    }

    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }

    MV_SAVE_IMG_TO_FILE_PARAM param;
    std::memset(&param, 0, sizeof(param));
    param.enPixelType = static_cast<MvGvspPixelType>(frame.pixel_type);
    param.pData = const_cast<unsigned char*>(reinterpret_cast<const unsigned char*>(frame.data.data()));
    param.nDataLen = frame.frame_len;
    param.nWidth = frame.width;
    param.nHeight = frame.height;
    param.enImageType = parse_image_type(image_type);
    param.nQuality = quality;
    std::strncpy(param.pImagePath, path.c_str(), sizeof(param.pImagePath) - 1);
    param.iMethodValue = 2;

    check_ok(mvs().save_image_to_file(handle_, &param), "MV_CC_SaveImageToFile");
}

std::vector<Frame> HikrobotCamera::capture_burst(int count, uint32_t timeout_ms) {
    if (count <= 0) {
        throw std::runtime_error("capture_burst count must be positive");
    }
    if (!open_) {
        throw std::runtime_error("Camera is not open");
    }

    configure_software_trigger();

    if (!grabbing_) {
        start();
    }

    check_ok(mvs().clear_image_buffer(handle_), "MV_CC_ClearImageBuffer");

    std::vector<Frame> frames;
    frames.reserve(static_cast<size_t>(count));

    for (int i = 0; i < count; ++i) {
        trigger();
        frames.push_back(get_frame(timeout_ms));
    }

    return frames;
}

void HikrobotCamera::stop() {
    if (!grabbing_) {
        return;
    }
    check_ok(mvs().stop_grabbing(handle_), "MV_CC_StopGrabbing");
    grabbing_ = false;
}

void HikrobotCamera::close() {
    if (grabbing_) {
        stop();
    }
    if (!open_) {
        if (handle_ != nullptr) {
            mvs().destroy_handle(handle_);
            handle_ = nullptr;
        }
        return;
    }

    const int close_ret = mvs().close_device(handle_);
    const int destroy_ret = mvs().destroy_handle(handle_);
    handle_ = nullptr;
    open_ = false;

    check_ok(close_ret, "MV_CC_CloseDevice");
    check_ok(destroy_ret, "MV_CC_DestroyHandle");
}

bool HikrobotCamera::is_open() const {
    return open_;
}

bool HikrobotCamera::is_grabbing() const {
    return grabbing_;
}

std::string HikrobotCamera::serial() const {
    return serial_;
}

}  // namespace hikcamera
