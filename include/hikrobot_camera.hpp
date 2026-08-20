#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace hikcamera {

struct DeviceInfo {
    int index = -1;
    std::string transport;
    std::string model;
    std::string serial;
    std::string user_defined_name;
    std::string ip;
};

struct Frame {
    uint16_t width = 0;
    uint16_t height = 0;
    uint32_t pixel_type = 0;
    uint32_t frame_num = 0;
    uint32_t frame_len = 0;
    float exposure_us = 0.0f;
    float gain = 0.0f;
    uint32_t average_brightness = 0;
    std::vector<uint8_t> data;
};

struct ConvertedFrame {
    uint16_t width = 0;
    uint16_t height = 0;
    uint32_t pixel_type = 0;
    uint32_t data_len = 0;
    std::vector<uint8_t> data;
};

struct IntParameter {
    int64_t value = 0;
    int64_t min = 0;
    int64_t max = 0;
    int64_t increment = 0;
};

struct FloatParameter {
    float value = 0.0f;
    float min = 0.0f;
    float max = 0.0f;
};

struct EnumParameter {
    uint32_t value = 0;
    std::vector<uint32_t> supported_values;
};

class HikrobotCamera {
public:
    explicit HikrobotCamera(std::string serial = "");
    ~HikrobotCamera();

    HikrobotCamera(const HikrobotCamera&) = delete;
    HikrobotCamera& operator=(const HikrobotCamera&) = delete;

    static std::vector<DeviceInfo> enum_devices();

    void open();
    void start();
    void configure_software_trigger();
    void trigger();
    void set_int(const std::string& name, int64_t value);
    void set_float(const std::string& name, float value);
    void set_enum(const std::string& name, uint32_t value);
    IntParameter get_int(const std::string& name);
    FloatParameter get_float(const std::string& name);
    EnumParameter get_enum(const std::string& name);
    void set_exposure(float exposure_us);
    void set_gain(float gain);
    void set_roi(int64_t width, int64_t height, int64_t offset_x = 0, int64_t offset_y = 0);
    void set_pixel_format(uint32_t pixel_format);
    Frame get_frame(uint32_t timeout_ms);
    ConvertedFrame convert_frame(const Frame& frame, uint32_t dst_pixel_format);
    void save_frame(const Frame& frame, const std::string& path, const std::string& image_type = "png", uint32_t quality = 3);
    std::vector<Frame> capture_burst(int count, uint32_t timeout_ms);
    void stop();
    void close();

    bool is_open() const;
    bool is_grabbing() const;
    std::string serial() const;

private:
    void* handle_ = nullptr;
    std::string serial_;
    bool open_ = false;
    bool grabbing_ = false;
};

}  // namespace hikcamera
