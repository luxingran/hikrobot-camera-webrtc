cmake_minimum_required(VERSION 3.20)

project(hikcamera_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(MVS_ROOT "C:/Program Files (x86)/MVS" CACHE PATH "Hikrobot MVS installation root")
set(MVS_RUNTIME_DIR "C:/Program Files (x86)/Common Files/MVS/Runtime/Win64_x64" CACHE PATH "Hikrobot MVS runtime DLL directory")

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

add_library(hikcamera_core STATIC
    src/hikrobot_camera.cpp
)

target_include_directories(hikcamera_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        "${MVS_ROOT}/Development/Includes"
)

target_link_directories(hikcamera_core
    PUBLIC
        "${MVS_ROOT}/Development/Libraries/win64"
)

pybind11_add_module(hikcamera_native NO_EXTRAS
    src/bindings.cpp
)

target_link_libraries(hikcamera_native
    PRIVATE
        hikcamera_core
)

pybind11_add_module(smoke_native NO_EXTRAS
    src/smoke.cpp
)
