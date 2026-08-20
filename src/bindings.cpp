#include "hikrobot_camera.hpp"

#include <PixelType.h>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;
using namespace pybind11::literals;

PYBIND11_MODULE(hikcamera_native, m) {
    m.doc() = "Minimal Hikrobot MVS camera bindings";

    py::class_<hikcamera::DeviceInfo>(m, "DeviceInfo")
        .def_readonly("index", &hikcamera::DeviceInfo::index)
        .def_readonly("transport", &hikcamera::DeviceInfo::transport)
        .def_readonly("model", &hikcamera::DeviceInfo::model)
        .def_readonly("serial", &hikcamera::DeviceInfo::serial)
        .def_readonly("user_defined_name", &hikcamera::DeviceInfo::user_defined_name)
        .def_readonly("ip", &hikcamera::DeviceInfo::ip)
        .def("__repr__", [](const hikcamera::DeviceInfo& d) {
            return "<DeviceInfo index=" + std::to_string(d.index) +
                   " transport='" + d.transport +
                   "' model='" + d.model +
                   "' serial='" + d.serial + "'>";
        });

    py::class_<hikcamera::IntParameter>(m, "IntParameter")
        .def_readonly("value", &hikcamera::IntParameter::value)
        .def_readonly("min", &hikcamera::IntParameter::min)
        .def_readonly("max", &hikcamera::IntParameter::max)
        .def_readonly("increment", &hikcamera::IntParameter::increment);

    py::class_<hikcamera::FloatParameter>(m, "FloatParameter")
        .def_readonly("value", &hikcamera::FloatParameter::value)
        .def_readonly("min", &hikcamera::FloatParameter::min)
        .def_readonly("max", &hikcamera::FloatParameter::max);

    py::class_<hikcamera::EnumParameter>(m, "EnumParameter")
        .def_readonly("value", &hikcamera::EnumParameter::value)
        .def_readonly("supported_values", &hikcamera::EnumParameter::supported_values);

    py::class_<hikcamera::Frame>(m, "Frame");

    py::class_<hikcamera::ConvertedFrame>(m, "ConvertedFrame");

    py::dict pixel_formats;
    pixel_formats["Mono8"] = static_cast<uint32_t>(PixelType_Gvsp_Mono8);
    pixel_formats["BayerGR8"] = static_cast<uint32_t>(PixelType_Gvsp_BayerGR8);
    pixel_formats["BayerRG8"] = static_cast<uint32_t>(PixelType_Gvsp_BayerRG8);
    pixel_formats["BayerGB8"] = static_cast<uint32_t>(PixelType_Gvsp_BayerGB8);
    pixel_formats["BayerBG8"] = static_cast<uint32_t>(PixelType_Gvsp_BayerBG8);
    pixel_formats["RGB8"] = static_cast<uint32_t>(PixelType_Gvsp_RGB8_Packed);
    pixel_formats["BGR8"] = static_cast<uint32_t>(PixelType_Gvsp_BGR8_Packed);
    m.attr("PIXEL_FORMATS") = pixel_formats;

    py::class_<hikcamera::HikrobotCamera>(m, "HikrobotCamera")
        .def(py::init<std::string>(), py::arg("serial") = "")
        .def_static("enum_devices", &hikcamera::HikrobotCamera::enum_devices)
        .def("open", &hikcamera::HikrobotCamera::open)
        .def("start", &hikcamera::HikrobotCamera::start)
        .def("configure_software_trigger", &hikcamera::HikrobotCamera::configure_software_trigger)
        .def("trigger", &hikcamera::HikrobotCamera::trigger)
        .def("set_int", &hikcamera::HikrobotCamera::set_int)
        .def("set_float", &hikcamera::HikrobotCamera::set_float)
        .def("set_enum", &hikcamera::HikrobotCamera::set_enum)
        .def("get_int", &hikcamera::HikrobotCamera::get_int)
        .def("get_float", &hikcamera::HikrobotCamera::get_float)
        .def("get_enum", &hikcamera::HikrobotCamera::get_enum)
        .def("set_exposure", &hikcamera::HikrobotCamera::set_exposure, py::arg("exposure_us"))
        .def("set_gain", &hikcamera::HikrobotCamera::set_gain, py::arg("gain"))
        .def("set_roi", &hikcamera::HikrobotCamera::set_roi,
             py::arg("width"), py::arg("height"), py::arg("offset_x") = 0, py::arg("offset_y") = 0)
        .def("set_pixel_format", &hikcamera::HikrobotCamera::set_pixel_format, py::arg("pixel_format"))
        .def("stop", &hikcamera::HikrobotCamera::stop)
        .def("close", &hikcamera::HikrobotCamera::close)
        .def("is_open", &hikcamera::HikrobotCamera::is_open)
        .def("is_grabbing", &hikcamera::HikrobotCamera::is_grabbing)
        .def("serial", &hikcamera::HikrobotCamera::serial)
        .def("get_frame", [](hikcamera::HikrobotCamera& camera, uint32_t timeout_ms) {
            auto frame = camera.get_frame(timeout_ms);
            return py::dict(
                "width"_a = frame.width,
                "height"_a = frame.height,
                "pixel_type"_a = frame.pixel_type,
                "frame_num"_a = frame.frame_num,
                "frame_len"_a = frame.frame_len,
                "exposure_us"_a = frame.exposure_us,
                "gain"_a = frame.gain,
                "average_brightness"_a = frame.average_brightness,
                "data"_a = py::bytes(
                    reinterpret_cast<const char*>(frame.data.data()),
                    frame.data.size()));
        }, py::arg("timeout_ms") = 1000)
        .def("convert_frame", [](hikcamera::HikrobotCamera& camera, py::dict frame_dict, uint32_t dst_pixel_format) {
            hikcamera::Frame frame;
            frame.width = frame_dict["width"].cast<uint16_t>();
            frame.height = frame_dict["height"].cast<uint16_t>();
            frame.pixel_type = frame_dict["pixel_type"].cast<uint32_t>();
            frame.frame_num = frame_dict["frame_num"].cast<uint32_t>();
            frame.frame_len = frame_dict["frame_len"].cast<uint32_t>();
            auto data = frame_dict["data"].cast<py::bytes>();
            auto data_str = static_cast<std::string>(data);
            frame.data.assign(data_str.begin(), data_str.end());

            auto converted = camera.convert_frame(frame, dst_pixel_format);
            return py::dict(
                "width"_a = converted.width,
                "height"_a = converted.height,
                "pixel_type"_a = converted.pixel_type,
                "data_len"_a = converted.data_len,
                "data"_a = py::bytes(
                    reinterpret_cast<const char*>(converted.data.data()),
                    converted.data.size()));
        }, py::arg("frame"), py::arg("dst_pixel_format"))
        .def("save_frame", [](hikcamera::HikrobotCamera& camera, py::dict frame_dict, const std::string& path, const std::string& image_type, uint32_t quality) {
            hikcamera::Frame frame;
            frame.width = frame_dict["width"].cast<uint16_t>();
            frame.height = frame_dict["height"].cast<uint16_t>();
            frame.pixel_type = frame_dict["pixel_type"].cast<uint32_t>();
            frame.frame_num = frame_dict["frame_num"].cast<uint32_t>();
            frame.frame_len = frame_dict["frame_len"].cast<uint32_t>();
            auto data = frame_dict["data"].cast<py::bytes>();
            auto data_str = static_cast<std::string>(data);
            frame.data.assign(data_str.begin(), data_str.end());
            camera.save_frame(frame, path, image_type, quality);
        }, py::arg("frame"), py::arg("path"), py::arg("image_type") = "png", py::arg("quality") = 3)
        .def("capture_burst", [](hikcamera::HikrobotCamera& camera, int count, uint32_t timeout_ms) {
            auto frames = camera.capture_burst(count, timeout_ms);
            py::list result;
            for (auto& frame : frames) {
                result.append(py::dict(
                    "width"_a = frame.width,
                    "height"_a = frame.height,
                    "pixel_type"_a = frame.pixel_type,
                    "frame_num"_a = frame.frame_num,
                    "frame_len"_a = frame.frame_len,
                    "exposure_us"_a = frame.exposure_us,
                    "gain"_a = frame.gain,
                    "average_brightness"_a = frame.average_brightness,
                    "data"_a = py::bytes(
                        reinterpret_cast<const char*>(frame.data.data()),
                        frame.data.size())));
            }
            return result;
        }, py::arg("count"), py::arg("timeout_ms") = 1000);
}
