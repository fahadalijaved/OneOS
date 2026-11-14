#include "PreviewBridge.h"

#include <android/native_window.h>

#include <algorithm>
#include <cstddef>
#include <cstdint>

namespace {

constexpr int32_t kInvalidArgument = -1;
constexpr int32_t kWindowError = -2;

uint8_t clampByte(int32_t value) {
    return static_cast<uint8_t>(std::clamp(value, 0, 255));
}

void mapSourcePixel(
        int32_t outputX, int32_t outputY, int32_t width, int32_t height,
        int32_t orientation, int32_t* sourceX, int32_t* sourceY) {
    switch (orientation) {
        case 90:
            *sourceX = outputY;
            *sourceY = height - 1 - outputX;
            return;
        case 180:
            *sourceX = width - 1 - outputX;
            *sourceY = height - 1 - outputY;
            return;
        case 270:
            *sourceX = width - 1 - outputY;
            *sourceY = outputX;
            return;
        default:
            *sourceX = outputX;
            *sourceY = outputY;
            return;
    }
}

void readYuv(
        const uint8_t* frame, int32_t width, int32_t height, int32_t sourceX, int32_t sourceY,
        uint8_t* red, uint8_t* green, uint8_t* blue) {
    const size_t ySize = static_cast<size_t>(width) * height;
    const size_t yIndex = static_cast<size_t>(sourceY) * width + sourceX;
    const size_t uvIndex = ySize + static_cast<size_t>(sourceY / 2) * width + (sourceX / 2) * 2;
    const int32_t y = frame[yIndex];
    const int32_t v = frame[uvIndex];
    const int32_t u = frame[uvIndex + 1];
    const int32_t c = std::max(y - 16, 0);
    const int32_t d = u - 128;
    const int32_t e = v - 128;
    *red = clampByte((298 * c + 409 * e + 128) >> 8);
    *green = clampByte((298 * c - 100 * d - 208 * e + 128) >> 8);
    *blue = clampByte((298 * c + 516 * d + 128) >> 8);
}

bool writeBuffer(
        const ANativeWindow_Buffer& buffer, const uint8_t* frame, size_t frameSize, int32_t width,
        int32_t height, int32_t orientation) {
    const int32_t outputWidth = orientation == 90 || orientation == 270 ? height : width;
    const int32_t outputHeight = orientation == 90 || orientation == 270 ? width : height;
    const size_t requiredSize = static_cast<size_t>(width) * height * 3 / 2;
    if (frameSize < requiredSize || buffer.bits == nullptr || buffer.stride < buffer.width ||
        buffer.width <= 0 || buffer.height <= 0 || outputWidth <= 0 || outputHeight <= 0) {
        return false;
    }
    size_t bytesPerPixel = 0;
    if (buffer.format == WINDOW_FORMAT_RGBA_8888 || buffer.format == WINDOW_FORMAT_RGBX_8888) {
        bytesPerPixel = 4;
    } else if (buffer.format == WINDOW_FORMAT_RGB_565) {
        bytesPerPixel = 2;
    } else {
        return false;
    }
    auto* destination = static_cast<uint8_t*>(buffer.bits);
    const float scale = std::max(
            static_cast<float>(buffer.width) / outputWidth,
            static_cast<float>(buffer.height) / outputHeight);
    const float offsetX = (buffer.width - outputWidth * scale) * 0.5f;
    const float offsetY = (buffer.height - outputHeight * scale) * 0.5f;
    for (int32_t y = 0; y < buffer.height; ++y) {
        const int32_t outputY = std::clamp(
                static_cast<int32_t>((y - offsetY) / scale), 0, outputHeight - 1);
        auto* row = destination + static_cast<size_t>(y) * buffer.stride * bytesPerPixel;
        for (int32_t x = 0; x < buffer.width; ++x) {
            const int32_t displayX = std::clamp(
                    static_cast<int32_t>((x - offsetX) / scale), 0, outputWidth - 1);
            int32_t sourceX = 0;
            int32_t sourceY = 0;
            mapSourcePixel(
                    outputWidth - 1 - displayX, outputY, width, height, orientation, &sourceX,
                    &sourceY);
            if (sourceX < 0 || sourceX >= width || sourceY < 0 || sourceY >= height) {
                return false;
            }
            uint8_t red = 0;
            uint8_t green = 0;
            uint8_t blue = 0;
            readYuv(frame, width, height, sourceX, sourceY, &red, &green, &blue);
            if (bytesPerPixel == 4) {
                uint8_t* pixel = row + static_cast<size_t>(x) * 4;
                pixel[0] = red;
                pixel[1] = green;
                pixel[2] = blue;
                pixel[3] = 255;
            } else {
                const uint16_t pixel = static_cast<uint16_t>(
                        ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3));
                auto* destinationPixel = reinterpret_cast<uint16_t*>(
                        row + static_cast<size_t>(x) * 2);
                *destinationPixel = pixel;
            }
        }
    }
    return true;
}

}  // namespace

extern "C" int32_t facehal_preview_render_nv21(
        void* window, const uint8_t* frame, size_t frameSize, int32_t width, int32_t height,
        int32_t sensorOrientation, int32_t configureWindow, int32_t portraitGeometry) {
    if (window == nullptr || frame == nullptr || width <= 0 || height <= 0 || (width & 1) != 0 ||
        (height & 1) != 0 ||
        (sensorOrientation != 0 && sensorOrientation != 90 && sensorOrientation != 180 &&
         sensorOrientation != 270)) {
        return kInvalidArgument;
    }
    auto* nativeWindow = static_cast<ANativeWindow*>(window);
    const int32_t bufferWidth = sensorOrientation == 90 || sensorOrientation == 270 ? height : width;
    const int32_t bufferHeight = sensorOrientation == 90 || sensorOrientation == 270 ? width : height;
    int32_t status = 0;
    // Reconfiguring a SurfaceView buffer queue for every frame can freeze previews on
    // older vendor graphics stacks. Configure it once, then only lock/post new buffers.
    if (configureWindow != 0) {
        int32_t geometryWidth = bufferWidth;
        int32_t geometryHeight = bufferHeight;
        const int32_t windowWidth = ANativeWindow_getWidth(nativeWindow);
        const int32_t windowHeight = ANativeWindow_getHeight(nativeWindow);
        const bool sameOrientation =
                (windowWidth > windowHeight) == (bufferWidth > bufferHeight);
        const bool useWindowSize = windowWidth > 0 && windowHeight > 0 &&
                (portraitGeometry == 0 || sameOrientation);
        if (useWindowSize) {
            geometryWidth = windowWidth;
            geometryHeight = windowHeight;
        }
        status = ANativeWindow_setBuffersGeometry(
                nativeWindow, geometryWidth, geometryHeight, WINDOW_FORMAT_RGBA_8888);
        if (status != 0) {
            status = ANativeWindow_setBuffersGeometry(nativeWindow, 0, 0, WINDOW_FORMAT_RGBA_8888);
        }
        if (status != 0) {
            return status < 0 ? status : kWindowError;
        }
    }
    ANativeWindow_Buffer buffer{};
    status = ANativeWindow_lock(nativeWindow, &buffer, nullptr);
    if (status != 0) {
        return status < 0 ? status : kWindowError;
    }
    const bool written = writeBuffer(
            buffer, frame, frameSize, width, height, sensorOrientation);
    const int32_t postStatus = ANativeWindow_unlockAndPost(nativeWindow);
    if (!written) {
        return kInvalidArgument;
    }
    return postStatus == 0 ? 0 : (postStatus < 0 ? postStatus : kWindowError);
}
