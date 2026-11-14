#pragma once

#include <cstddef>
#include <cstdint>

extern "C" int32_t facehal_preview_render_nv21(
        void* window, const uint8_t* frame, size_t frame_size, int32_t width, int32_t height,
        int32_t sensor_orientation, int32_t configure_window);
