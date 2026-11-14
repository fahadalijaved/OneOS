#pragma once

#include <cstddef>
#include <cstdint>

struct FacehalCamera;

extern "C" int32_t facehal_camera_worker_main(
        int32_t width, int32_t height, int32_t socket_fd, int32_t frame_fd,
        int32_t window_mode);
extern "C" FacehalCamera* facehal_camera_open(int32_t width, int32_t height);
extern "C" void facehal_camera_close(FacehalCamera* camera);
extern "C" int32_t facehal_camera_next_nv21(
        FacehalCamera* camera, uint8_t* output, size_t capacity, int32_t timeout_ms);
extern "C" int32_t facehal_camera_frame_size(const FacehalCamera* camera);
extern "C" int32_t facehal_camera_sensor_orientation(const FacehalCamera* camera);
