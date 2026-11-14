#include "CameraBridge.h"

#include <android/native_window.h>
#include <android/hardware_buffer.h>
#include <camera/NdkCameraCaptureSession.h>
#include <camera/NdkCameraDevice.h>
#include <camera/NdkCameraManager.h>
#include <camera/NdkCameraMetadata.h>
#include <camera/NdkCameraMetadataTags.h>
#include <camera/NdkCaptureRequest.h>
#include <media/NdkImage.h>
#include <media/NdkImageReader.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <linux/memfd.h>
#include <limits.h>
#include <memory>
#include <mutex>
#include <limits>
#include <optional>
#include <poll.h>
#include <signal.h>
#include <spawn.h>
#include <string>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

extern char** environ;

#if defined(FACEHAL_VENDOR_CAMERA_NDK) && !defined(__ANDROID_VNDK__)
extern "C" media_status_t AImageReader_getWindowNativeHandle(
        AImageReader* reader, void** handle);
#endif

namespace {

constexpr int32_t kInvalidArgument = -1;
constexpr int32_t kCameraUnavailable = -2;
constexpr int32_t kTimeout = -3;
constexpr int32_t kBadFrame = -4;
constexpr int32_t kWorkerNextFrame = 1;
constexpr int32_t kWorkerClose = 2;
constexpr int kWorkerSocketFd = 300;
constexpr int kWorkerFrameFd = 301;
constexpr int32_t kWorkerStartupTimeoutMs = 25'000;
constexpr int32_t kCandidateProbeTimeoutMs = 2'000;
constexpr int32_t kCandidateProbeFrames = 4;
constexpr int32_t kWorkerExitTimeoutMs = 2'000;
constexpr size_t kMaxSizesPerCamera = 3;
constexpr size_t kMaxCameraCandidates = 5;
constexpr int32_t kWindowModeVendorHandle = 0;
constexpr int32_t kWindowModeStandard = 1;
constexpr char kXiaomiCameraRoleTag[] = "com.xiaomi.cameraid.role.cameraId";
constexpr int32_t kXiaomiFaceCameraRole = 201;

struct WorkerHello {
    int32_t status;
    int32_t frameSize;
    int32_t sensorOrientation;
};

struct WorkerRequest {
    int32_t command;
    int32_t timeoutMs;
};

#if defined(FACEHAL_VENDOR_CAMERA_NDK)
struct NativeHandleHeader {
    int32_t version;
    int32_t numFds;
    int32_t numInts;
    int32_t data[];
};

bool validVendorWindowHandle(void* opaqueHandle) {
    if (opaqueHandle == nullptr) {
        return false;
    }
    const auto* handle = static_cast<const NativeHandleHeader*>(opaqueHandle);
    if (handle->version < static_cast<int32_t>(sizeof(NativeHandleHeader)) ||
        handle->numFds < 0 || handle->numFds > 64 || handle->numInts < 0 ||
        handle->numInts > 1024) {
        return false;
    }
    for (int32_t index = 0; index < handle->numFds; ++index) {
        if (handle->data[index] < 0 || fcntl(handle->data[index], F_GETFD) < 0) {
            return false;
        }
    }
    return true;
}
#endif

struct ImageDeleter {
    void operator()(AImage* image) const {
        if (image != nullptr) {
            AImage_delete(image);
        }
    }
};

struct CallbackState {
    std::mutex mutex;
    std::condition_variable condition;
    uint64_t frameSequence = 0;
    uint64_t consumedSequence = 0;
    size_t callbacksInFlight = 0;
    bool failed = false;
    bool closing = false;
    bool sessionClosed = false;
};

class CallbackGuard {
  public:
    explicit CallbackGuard(CallbackState* state) : state_(state) {
        std::lock_guard lock(state_->mutex);
        ++state_->callbacksInFlight;
    }

    ~CallbackGuard() {
        std::lock_guard lock(state_->mutex);
        --state_->callbacksInFlight;
        state_->condition.notify_all();
    }

  private:
    CallbackState* state_;
};

}  // namespace

struct LocalCamera {
    int32_t outputWidth;
    int32_t outputHeight;
    int32_t captureWidth;
    int32_t captureHeight;
    std::string cameraId;
    int32_t sensorOrientation = -1;
    bool firstFrameLogged = false;
    bool frameTimeoutLogged = false;
    ACameraManager* manager = nullptr;
    ACameraDevice* device = nullptr;
    AImageReader* reader = nullptr;
    ANativeWindow* window = nullptr;
    ACameraCaptureSession* session = nullptr;
    ACaptureRequest* request = nullptr;
    ACameraOutputTarget* target = nullptr;
    ACaptureSessionOutput* output = nullptr;
    ACaptureSessionOutputContainer* outputs = nullptr;
    std::unique_ptr<CallbackState> callbacks = std::make_unique<CallbackState>();

    LocalCamera(
            int32_t frameWidth, int32_t frameHeight, int32_t streamWidth,
            int32_t streamHeight, std::string selectedCameraId)
        : outputWidth(frameWidth),
          outputHeight(frameHeight),
          captureWidth(streamWidth),
          captureHeight(streamHeight),
          cameraId(std::move(selectedCameraId)) {}

    ~LocalCamera() {
        {
            std::lock_guard lock(callbacks->mutex);
            callbacks->closing = true;
            callbacks->failed = true;
            callbacks->condition.notify_all();
        }
        if (session != nullptr) {
            ACameraCaptureSession_stopRepeating(session);
            ACameraCaptureSession_abortCaptures(session);
        }
        if (reader != nullptr) {
            AImageReader_setImageListener(reader, nullptr);
        }
        if (session != nullptr) {
            ACameraCaptureSession_close(session);
            {
                std::unique_lock lock(callbacks->mutex);
                callbacks->condition.wait_for(
                        lock, std::chrono::seconds(2),
                        [this] { return callbacks->sessionClosed; });
            }
            session = nullptr;
        }
        if (device != nullptr) {
            ACameraDevice_close(device);
            device = nullptr;
        }
        if (reader != nullptr) {
            AImageReader_delete(reader);
            reader = nullptr;
        }
        {
            std::unique_lock lock(callbacks->mutex);
            callbacks->condition.wait(
                lock, [this] { return callbacks->callbacksInFlight == 0; });
        }
        if (request != nullptr && target != nullptr) {
            ACaptureRequest_removeTarget(request, target);
        }
        if (request != nullptr) {
            ACaptureRequest_free(request);
            request = nullptr;
        }
        if (target != nullptr) {
            ACameraOutputTarget_free(target);
            target = nullptr;
        }
        if (outputs != nullptr && output != nullptr) {
            ACaptureSessionOutputContainer_remove(outputs, output);
        }
        if (output != nullptr) {
            ACaptureSessionOutput_free(output);
            output = nullptr;
        }
        if (outputs != nullptr) {
            ACaptureSessionOutputContainer_free(outputs);
            outputs = nullptr;
        }
        if (manager != nullptr) {
            ACameraManager_delete(manager);
            manager = nullptr;
        }
        if (window != nullptr) {
            ANativeWindow_release(window);
            window = nullptr;
        }
    }
};

namespace {

void onDeviceDisconnected(void* context, ACameraDevice*) {
    auto* state = static_cast<CallbackState*>(context);
    CallbackGuard guard(state);
    std::lock_guard lock(state->mutex);
    if (!state->closing) {
        state->failed = true;
        state->condition.notify_all();
    }
}

void onDeviceError(void* context, ACameraDevice*, int) {
    onDeviceDisconnected(context, nullptr);
}

void onSessionClosed(void* context, ACameraCaptureSession*) {
    auto* state = static_cast<CallbackState*>(context);
    CallbackGuard guard(state);
    std::lock_guard lock(state->mutex);
    state->sessionClosed = true;
    state->condition.notify_all();
}

void onSessionReady(void*, ACameraCaptureSession*) {}
void onSessionActive(void*, ACameraCaptureSession*) {}

void onImageAvailable(void* context, AImageReader*) {
    auto* state = static_cast<CallbackState*>(context);
    CallbackGuard guard(state);
    std::lock_guard lock(state->mutex);
    if (!state->closing) {
        ++state->frameSequence;
        state->condition.notify_one();
    }
}

struct CameraSelection {
    std::string id;
    int32_t sensorOrientation;
    int32_t captureWidth;
    int32_t captureHeight;
    bool supportsContinuousPictureAf;
    bool backwardCompatible;
    bool monochrome;
    bool depthOnly;
    bool xiaomiFaceRole;
    int64_t score;
};

bool hasXiaomiFaceCameraRole(
        ACameraManager* manager, const char* cameraId, ACameraMetadata* metadata) {
    using GetTagFromName = camera_status_t (*)(
            ACameraManager*, const char*, const char*, uint32_t*);
    static const auto getTagFromName = reinterpret_cast<GetTagFromName>(
            dlsym(RTLD_DEFAULT, "ACameraManager_getTagFromName"));
    if (getTagFromName == nullptr) {
        return false;
    }
    uint32_t roleTag = 0;
    if (getTagFromName(manager, cameraId, kXiaomiCameraRoleTag, &roleTag) != ACAMERA_OK) {
        return false;
    }
    ACameraMetadata_const_entry role{};
    return ACameraMetadata_getConstEntry(metadata, roleTag, &role) == ACAMERA_OK &&
            role.count > 0 && role.data.i32 != nullptr &&
            role.data.i32[0] == kXiaomiFaceCameraRole;
}

std::vector<std::pair<int32_t, int32_t>> outputSizes(
        ACameraMetadata* metadata, int32_t format) {
    std::vector<std::pair<int32_t, int32_t>> sizes;
    ACameraMetadata_const_entry configurations{};
    if (ACameraMetadata_getConstEntry(
                metadata, ACAMERA_SCALER_AVAILABLE_STREAM_CONFIGURATIONS, &configurations) !=
                ACAMERA_OK ||
        configurations.data.i32 == nullptr || configurations.count % 4 != 0) {
        return sizes;
    }
    for (uint32_t index = 0; index < configurations.count; index += 4) {
        const int32_t* configuration = configurations.data.i32 + index;
        if (configuration[0] == format && configuration[1] > 0 && configuration[2] > 0 &&
            (configuration[1] & 1) == 0 && (configuration[2] & 1) == 0 &&
            configuration[3] == ACAMERA_SCALER_AVAILABLE_STREAM_CONFIGURATIONS_OUTPUT) {
            sizes.emplace_back(configuration[1], configuration[2]);
        }
    }
    return sizes;
}

int64_t streamScore(int32_t width, int32_t height, int32_t targetWidth, int32_t targetHeight) {
    if (width == targetWidth && height == targetHeight) {
        return 1'000'000'000LL;
    }
    const int64_t area = static_cast<int64_t>(width) * height;
    const int64_t targetArea = static_cast<int64_t>(targetWidth) * targetHeight;
    const int64_t aspectError = std::llabs(
            static_cast<int64_t>(width) * targetHeight -
            static_cast<int64_t>(height) * targetWidth);
    int64_t score = 0;
    if (aspectError == 0) {
        score += 300'000'000LL;
    } else {
        score -= aspectError * 1'000LL;
    }
    if (width >= targetWidth && height >= targetHeight) {
        score += 100'000'000LL;
    }
    if (width <= 1920 && height <= 1080) {
        score += 20'000'000LL;
    }
    score -= std::llabs(area - targetArea);
    return score;
}

std::vector<std::pair<int32_t, int32_t>> rankedOutputSizes(
        ACameraMetadata* metadata, int32_t targetWidth, int32_t targetHeight) {
    auto sizes = outputSizes(metadata, AIMAGE_FORMAT_YUV_420_888);
    std::sort(sizes.begin(), sizes.end());
    sizes.erase(std::unique(sizes.begin(), sizes.end()), sizes.end());
    std::stable_sort(
            sizes.begin(), sizes.end(),
            [targetWidth, targetHeight](const auto& left, const auto& right) {
                return streamScore(left.first, left.second, targetWidth, targetHeight) >
                        streamScore(right.first, right.second, targetWidth, targetHeight);
            });
    if (sizes.size() > kMaxSizesPerCamera) {
        sizes.resize(kMaxSizesPerCamera);
    }
    return sizes;
}

bool hasCapability(ACameraMetadata* metadata, uint8_t capability) {
    ACameraMetadata_const_entry capabilities{};
    if (ACameraMetadata_getConstEntry(
                metadata, ACAMERA_REQUEST_AVAILABLE_CAPABILITIES, &capabilities) != ACAMERA_OK ||
        capabilities.data.u8 == nullptr) {
        return false;
    }
    return std::find(
                   capabilities.data.u8, capabilities.data.u8 + capabilities.count, capability) !=
            capabilities.data.u8 + capabilities.count;
}

std::vector<CameraSelection> findFrontCameras(
        ACameraManager* manager, int32_t width, int32_t height) {
    ACameraIdList* ids = nullptr;
    if (ACameraManager_getCameraIdList(manager, &ids) != ACAMERA_OK || ids == nullptr) {
        return {};
    }
    std::vector<CameraSelection> candidates;
    for (int index = 0; index < ids->numCameras; ++index) {
        ACameraMetadata* metadata = nullptr;
        if (ACameraManager_getCameraCharacteristics(manager, ids->cameraIds[index], &metadata) !=
                    ACAMERA_OK ||
            metadata == nullptr) {
            continue;
        }
        ACameraMetadata_const_entry facing{};
        const bool front = ACameraMetadata_getConstEntry(metadata, ACAMERA_LENS_FACING, &facing) ==
                                   ACAMERA_OK &&
                           facing.count > 0 && facing.data.u8 != nullptr &&
                           facing.data.u8[0] == ACAMERA_LENS_FACING_FRONT;
        ACameraMetadata_const_entry orientation{};
        const bool hasOrientation =
                ACameraMetadata_getConstEntry(metadata, ACAMERA_SENSOR_ORIENTATION, &orientation) ==
                        ACAMERA_OK &&
                orientation.count > 0 && orientation.data.i32 != nullptr;
        const int32_t sensorOrientation = hasOrientation ? orientation.data.i32[0] : -1;
        const auto selectedSizes = rankedOutputSizes(metadata, width, height);
        const bool backwardCompatible = hasCapability(
                metadata, ACAMERA_REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE);
        const bool monochrome = hasCapability(
                metadata, ACAMERA_REQUEST_AVAILABLE_CAPABILITIES_MONOCHROME);
        const bool depthOnly =
                hasCapability(metadata, ACAMERA_REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT) &&
                !backwardCompatible;
        const bool xiaomiFaceRole =
                hasXiaomiFaceCameraRole(manager, ids->cameraIds[index], metadata);
        ACameraMetadata_const_entry autofocusModes{};
        const bool supportsContinuousPictureAf =
                ACameraMetadata_getConstEntry(metadata, ACAMERA_CONTROL_AF_AVAILABLE_MODES,
                                              &autofocusModes) == ACAMERA_OK &&
                autofocusModes.data.u8 != nullptr &&
                std::find(autofocusModes.data.u8,
                          autofocusModes.data.u8 + autofocusModes.count,
                          ACAMERA_CONTROL_AF_MODE_CONTINUOUS_PICTURE) !=
                        autofocusModes.data.u8 + autofocusModes.count;
        if ((front || xiaomiFaceRole) && !selectedSizes.empty() &&
            (sensorOrientation == 0 || sensorOrientation == 90 || sensorOrientation == 180 ||
             sensorOrientation == 270)) {
            for (const auto& selectedSize : selectedSizes) {
                int64_t score = streamScore(
                        selectedSize.first, selectedSize.second, width, height);
                if (backwardCompatible) {
                    score += 500'000'000LL;
                }
                if (monochrome) {
                    score -= 1'500'000'000LL;
                }
                if (depthOnly) {
                    score -= 1'000'000'000LL;
                }
                if (xiaomiFaceRole) {
                    score += 3'000'000'000LL;
                }
                if (std::string(ids->cameraIds[index]) == "1") {
                    const bool exactOutput = selectedSize.first == width &&
                            selectedSize.second == height;
                    score += exactOutput ? 6'000'000'000LL : 10'000'000LL;
                }
                candidates.push_back(CameraSelection{
                        ids->cameraIds[index], sensorOrientation, selectedSize.first,
                        selectedSize.second, supportsContinuousPictureAf, backwardCompatible,
                        monochrome, depthOnly, xiaomiFaceRole, score});
            }
        }
        ACameraMetadata_free(metadata);
    }
    ACameraManager_deleteCameraIdList(ids);
    std::stable_sort(
            candidates.begin(), candidates.end(),
            [](const CameraSelection& left, const CameraSelection& right) {
                return left.score > right.score;
            });
    if (candidates.size() > kMaxCameraCandidates) {
        candidates.resize(kMaxCameraCandidates);
    }
    return candidates;
}

bool initialize(
        LocalCamera* camera, const CameraSelection& selection,
        int32_t windowMode, int32_t requestTemplate) {
#if !defined(FACEHAL_VENDOR_CAMERA_NDK)
    (void)windowMode;
#endif
    camera->manager = ACameraManager_create();
    if (camera->manager == nullptr) {
        std::fprintf(stderr, "FaceHAL camera worker v2: ACameraManager_create failed\n");
        return false;
    }
    camera->sensorOrientation = selection.sensorOrientation;
    if (AImageReader_new(camera->captureWidth, camera->captureHeight,
                         AIMAGE_FORMAT_YUV_420_888, 4,
                         &camera->reader) != AMEDIA_OK ||
        camera->reader == nullptr) {
        std::fprintf(stderr, "FaceHAL camera worker v2: AImageReader_new failed\n");
        return false;
    }
    AImageReader_ImageListener imageListener{camera->callbacks.get(), onImageAvailable};
    if (AImageReader_setImageListener(camera->reader, &imageListener) != AMEDIA_OK) {
        std::fprintf(stderr, "FaceHAL camera worker v2: AImageReader_setImageListener failed\n");
        return false;
    }
    if (AImageReader_getWindow(camera->reader, &camera->window) != AMEDIA_OK ||
        camera->window == nullptr) {
        std::fprintf(stderr, "FaceHAL camera worker v2: AImageReader_getWindow failed\n");
        return false;
    }
    ANativeWindow_acquire(camera->window);
    void* cameraOutputWindow = camera->window;
#if defined(FACEHAL_VENDOR_CAMERA_NDK)
    void* vendorWindowHandle = nullptr;
#if defined(__ANDROID_VNDK__)
    native_handle_t* platformWindowHandle = nullptr;
    const media_status_t nativeHandleStatus =
            AImageReader_getWindowNativeHandle(camera->reader, &platformWindowHandle);
    vendorWindowHandle = platformWindowHandle;
#else
    const media_status_t nativeHandleStatus =
            AImageReader_getWindowNativeHandle(camera->reader, &vendorWindowHandle);
#endif
    if (windowMode == kWindowModeVendorHandle &&
        (nativeHandleStatus != AMEDIA_OK || !validVendorWindowHandle(vendorWindowHandle))) {
        std::fprintf(
                stderr,
                "FaceHAL camera worker v2: vendor ImageReader native handle unavailable status=%d\n",
                nativeHandleStatus);
        return false;
    }
    if (windowMode == kWindowModeVendorHandle) {
        const auto* nativeHandle = static_cast<const NativeHandleHeader*>(vendorWindowHandle);
        std::fprintf(
                stderr, "FaceHAL camera worker v2: vendor native handle ready fds=%d ints=%d\n",
                nativeHandle->numFds, nativeHandle->numInts);
        cameraOutputWindow = vendorWindowHandle;
    } else {
        std::fprintf(stderr, "FaceHAL camera worker v2: using standard ANativeWindow ABI\n");
    }
#endif
#if defined(FACEHAL_VENDOR_CAMERA_NDK) && defined(__ANDROID_VNDK__)
    auto* captureWindow = static_cast<native_handle_t*>(cameraOutputWindow);
#else
    auto* captureWindow = static_cast<ANativeWindow*>(cameraOutputWindow);
#endif
    ACameraDevice_StateCallbacks deviceCallbacks{
            camera->callbacks.get(), onDeviceDisconnected, onDeviceError};
    if (ACameraManager_openCamera(camera->manager, selection.id.c_str(), &deviceCallbacks,
                                  &camera->device) != ACAMERA_OK ||
        camera->device == nullptr) {
        std::fprintf(stderr, "FaceHAL camera worker v2: openCamera failed id=%s\n",
                     selection.id.c_str());
        return false;
    }
    if (ACaptureSessionOutputContainer_create(&camera->outputs) != ACAMERA_OK ||
        ACaptureSessionOutput_create(captureWindow, &camera->output) != ACAMERA_OK ||
        ACaptureSessionOutputContainer_add(camera->outputs, camera->output) != ACAMERA_OK ||
        ACameraOutputTarget_create(captureWindow, &camera->target) != ACAMERA_OK ||
        ACameraDevice_createCaptureRequest(
                camera->device,
                static_cast<ACameraDevice_request_template>(requestTemplate),
                &camera->request) !=
                ACAMERA_OK ||
        ACaptureRequest_addTarget(camera->request, camera->target) != ACAMERA_OK) {
        std::fprintf(stderr, "FaceHAL camera worker v2: capture request setup failed\n");
        return false;
    }
    const uint8_t controlMode = ACAMERA_CONTROL_MODE_AUTO;
    if (ACaptureRequest_setEntry_u8(
                camera->request, ACAMERA_CONTROL_MODE, 1, &controlMode) != ACAMERA_OK) {
        std::fprintf(stderr, "FaceHAL camera worker v2: control auto unavailable\n");
    }
    const uint8_t exposureMode = ACAMERA_CONTROL_AE_MODE_ON;
    if (ACaptureRequest_setEntry_u8(
                camera->request, ACAMERA_CONTROL_AE_MODE, 1, &exposureMode) != ACAMERA_OK) {
        std::fprintf(stderr, "FaceHAL camera worker v2: auto exposure unavailable\n");
    }
    const uint8_t whiteBalanceMode = ACAMERA_CONTROL_AWB_MODE_AUTO;
    if (ACaptureRequest_setEntry_u8(
                camera->request, ACAMERA_CONTROL_AWB_MODE, 1, &whiteBalanceMode) != ACAMERA_OK) {
        std::fprintf(stderr, "FaceHAL camera worker v2: auto white balance unavailable\n");
    }
    if (selection.supportsContinuousPictureAf) {
        const uint8_t autofocusMode = ACAMERA_CONTROL_AF_MODE_CONTINUOUS_PICTURE;
        if (ACaptureRequest_setEntry_u8(camera->request, ACAMERA_CONTROL_AF_MODE, 1,
                                        &autofocusMode) != ACAMERA_OK) {
            std::fprintf(stderr, "FaceHAL camera worker v2: continuous autofocus unavailable\n");
        }
    }
    ACameraCaptureSession_stateCallbacks sessionCallbacks{
            camera->callbacks.get(), onSessionClosed, onSessionReady, onSessionActive};
    if (ACameraDevice_createCaptureSession(camera->device, camera->outputs, &sessionCallbacks,
                                           &camera->session) != ACAMERA_OK ||
        camera->session == nullptr) {
        std::fprintf(stderr, "FaceHAL camera worker v2: capture session setup failed\n");
        return false;
    }
    int sequenceId = 0;
    ACaptureRequest* request = camera->request;
    const camera_status_t repeatingStatus = ACameraCaptureSession_setRepeatingRequest(
            camera->session, nullptr, 1, &request, &sequenceId);
    if (repeatingStatus != ACAMERA_OK) {
        std::fprintf(stderr, "FaceHAL camera worker v2: repeating request failed status=%d\n",
                     repeatingStatus);
        return false;
    }
    return true;
}

bool planeSample(
        const uint8_t* data, int dataLength, int32_t rowStride, int32_t pixelStride,
        int32_t x, int32_t y, uint8_t* output) {
    if (data == nullptr || dataLength <= 0 || rowStride <= 0 || pixelStride <= 0 || x < 0 || y < 0) {
        return false;
    }
    const size_t index = static_cast<size_t>(y) * rowStride +
                         static_cast<size_t>(x) * pixelStride;
    if (index >= static_cast<size_t>(dataLength)) {
        return false;
    }
    *output = data[index];
    return true;
}

int32_t copyNv21(
        const AImage* image, uint8_t* output, size_t capacity,
        int32_t outputWidth, int32_t outputHeight) {
    int32_t width = 0;
    int32_t height = 0;
    int32_t planes = 0;
    if (AImage_getWidth(image, &width) != AMEDIA_OK ||
        AImage_getHeight(image, &height) != AMEDIA_OK ||
        AImage_getNumberOfPlanes(image, &planes) != AMEDIA_OK || width <= 0 || height <= 0 ||
        outputWidth <= 0 || outputHeight <= 0 || (width & 1) != 0 || (height & 1) != 0 ||
        (outputWidth & 1) != 0 || (outputHeight & 1) != 0 || planes < 3) {
        return kBadFrame;
    }
    uint8_t* y = nullptr;
    uint8_t* u = nullptr;
    uint8_t* v = nullptr;
    int yLength = 0;
    int uLength = 0;
    int vLength = 0;
    int32_t yRowStride = 0;
    int32_t uRowStride = 0;
    int32_t vRowStride = 0;
    int32_t yPixelStride = 0;
    int32_t uPixelStride = 0;
    int32_t vPixelStride = 0;
    if (AImage_getPlaneData(image, 0, &y, &yLength) != AMEDIA_OK ||
        AImage_getPlaneData(image, 1, &u, &uLength) != AMEDIA_OK ||
        AImage_getPlaneData(image, 2, &v, &vLength) != AMEDIA_OK || u == nullptr || v == nullptr ||
        y == nullptr ||
        AImage_getPlaneRowStride(image, 0, &yRowStride) != AMEDIA_OK ||
        AImage_getPlaneRowStride(image, 1, &uRowStride) != AMEDIA_OK ||
        AImage_getPlaneRowStride(image, 2, &vRowStride) != AMEDIA_OK ||
        AImage_getPlanePixelStride(image, 0, &yPixelStride) != AMEDIA_OK ||
        AImage_getPlanePixelStride(image, 1, &uPixelStride) != AMEDIA_OK ||
        AImage_getPlanePixelStride(image, 2, &vPixelStride) != AMEDIA_OK) {
        return kBadFrame;
    }

    const size_t outputYSize = static_cast<size_t>(outputWidth) * outputHeight;
    const size_t frameSize = outputYSize + outputYSize / 2;
    if (capacity < frameSize) {
        return kInvalidArgument;
    }
    int32_t cropWidth = width;
    int32_t cropHeight = height;
    if (static_cast<int64_t>(width) * outputHeight >
        static_cast<int64_t>(height) * outputWidth) {
        cropWidth = static_cast<int32_t>(
                static_cast<int64_t>(height) * outputWidth / outputHeight);
    } else {
        cropHeight = static_cast<int32_t>(
                static_cast<int64_t>(width) * outputHeight / outputWidth);
    }
    cropWidth &= ~1;
    cropHeight &= ~1;
    const int32_t cropLeft = ((width - cropWidth) / 2) & ~1;
    const int32_t cropTop = ((height - cropHeight) / 2) & ~1;

    for (int32_t row = 0; row < outputHeight; ++row) {
        const int32_t sourceY = cropTop + static_cast<int32_t>(
                static_cast<int64_t>(row) * cropHeight / outputHeight);
        for (int32_t column = 0; column < outputWidth; ++column) {
            const int32_t sourceX = cropLeft + static_cast<int32_t>(
                    static_cast<int64_t>(column) * cropWidth / outputWidth);
            if (!planeSample(
                        y, yLength, yRowStride, yPixelStride, sourceX, sourceY,
                        &output[static_cast<size_t>(row) * outputWidth + column])) {
                return kBadFrame;
            }
        }
    }
    size_t destination = outputYSize;
    for (int32_t row = 0; row < outputHeight / 2; ++row) {
        const int32_t sourceY = cropTop / 2 + static_cast<int32_t>(
                static_cast<int64_t>(row) * (cropHeight / 2) / (outputHeight / 2));
        for (int32_t column = 0; column < outputWidth / 2; ++column) {
            const int32_t sourceX = cropLeft / 2 + static_cast<int32_t>(
                    static_cast<int64_t>(column) * (cropWidth / 2) / (outputWidth / 2));
            if (!planeSample(
                        v, vLength, vRowStride, vPixelStride, sourceX, sourceY,
                        &output[destination++]) ||
                !planeSample(
                        u, uLength, uRowStride, uPixelStride, sourceX, sourceY,
                        &output[destination++])) {
                return kBadFrame;
            }
        }
    }
    return static_cast<int32_t>(frameSize);
}

int32_t nextLocalNv21(
        LocalCamera* camera, uint8_t* output, size_t capacity, int32_t timeoutMs) {
    if (camera == nullptr || output == nullptr || timeoutMs < 0) {
        return kInvalidArgument;
    }
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
    for (;;) {
        {
            std::unique_lock lock(camera->callbacks->mutex);
            while (camera->callbacks->frameSequence == camera->callbacks->consumedSequence &&
                   !camera->callbacks->failed && !camera->callbacks->closing) {
                if (camera->callbacks->condition.wait_until(lock, deadline) ==
                    std::cv_status::timeout) {
                    if (!camera->frameTimeoutLogged) {
                        camera->frameTimeoutLogged = true;
                        std::fprintf(
                                stderr,
                                "FaceHAL camera worker v2: ImageReader produced no frame\n");
                        std::fflush(stderr);
                    }
                    return kTimeout;
                }
            }
            if (camera->callbacks->failed || camera->callbacks->closing) {
                return kCameraUnavailable;
            }
            camera->callbacks->consumedSequence = camera->callbacks->frameSequence;
        }
        AImage* rawImage = nullptr;
        const media_status_t status = AImageReader_acquireLatestImage(camera->reader, &rawImage);
        if (status == AMEDIA_IMGREADER_NO_BUFFER_AVAILABLE) {
            continue;
        }
        if (status != AMEDIA_OK || rawImage == nullptr) {
            return kBadFrame;
        }
        std::unique_ptr<AImage, ImageDeleter> image(rawImage);
        const int32_t result = copyNv21(
                image.get(), output, capacity, camera->outputWidth, camera->outputHeight);
        if (result > 0 && !camera->firstFrameLogged) {
            camera->firstFrameLogged = true;
            std::fprintf(stderr, "FaceHAL camera worker v2: first NV21 frame acquired\n");
            std::fflush(stderr);
        }
        return result;
    }
}

bool hasUsableLuma(
        const uint8_t* nv21, int32_t width, int32_t height,
        int32_t* minimum, int32_t* maximum, int32_t* average) {
    if (nv21 == nullptr || width <= 0 || height <= 0) {
        return false;
    }
    const int32_t rowStep = std::max(1, height / 24);
    const int32_t columnStep = std::max(1, width / 32);
    int32_t minLuma = 255;
    int32_t maxLuma = 0;
    int64_t sum = 0;
    int32_t samples = 0;
    for (int32_t row = rowStep / 2; row < height; row += rowStep) {
        for (int32_t column = columnStep / 2; column < width; column += columnStep) {
            const int32_t luma = nv21[static_cast<size_t>(row) * width + column];
            minLuma = std::min(minLuma, luma);
            maxLuma = std::max(maxLuma, luma);
            sum += luma;
            ++samples;
        }
    }
    if (samples == 0) {
        return false;
    }
    const int32_t meanLuma = static_cast<int32_t>(sum / samples);
    if (minimum != nullptr) {
        *minimum = minLuma;
    }
    if (maximum != nullptr) {
        *maximum = maxLuma;
    }
    if (average != nullptr) {
        *average = meanLuma;
    }
    return maxLuma > 4 && minLuma < 251 &&
            !((maxLuma - minLuma) <= 3 && (meanLuma <= 24 || meanLuma >= 232));
}

int32_t probeCandidateNv21(
        LocalCamera* camera, uint8_t* output, size_t capacity,
        int32_t width, int32_t height) {
    const auto deadline = std::chrono::steady_clock::now() +
            std::chrono::milliseconds(kCandidateProbeTimeoutMs);
    int32_t lastResult = kTimeout;
    for (int32_t frame = 0; frame < kCandidateProbeFrames; ++frame) {
        const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
                deadline - std::chrono::steady_clock::now());
        if (remaining.count() <= 0) {
            break;
        }
        lastResult = nextLocalNv21(
                camera, output, capacity, static_cast<int32_t>(remaining.count()));
        if (lastResult != static_cast<int32_t>(capacity)) {
            if (lastResult == kTimeout || lastResult == kCameraUnavailable) {
                break;
            }
            continue;
        }
        int32_t minimum = 0;
        int32_t maximum = 0;
        int32_t average = 0;
        if (hasUsableLuma(output, width, height, &minimum, &maximum, &average)) {
            std::fprintf(
                    stderr,
                    "FaceHAL camera worker v2: candidate frame usable index=%d luma=%d..%d "
                    "mean=%d\n",
                    frame + 1, minimum, maximum, average);
            std::fflush(stderr);
            return lastResult;
        }
        std::fprintf(
                stderr,
                "FaceHAL camera worker v2: rejected blank warmup frame index=%d luma=%d..%d "
                "mean=%d\n",
                frame + 1, minimum, maximum, average);
        std::fflush(stderr);
        lastResult = kBadFrame;
    }
    return lastResult;
}

bool sendExact(int fd, const void* data, size_t size) {
    const auto* bytes = static_cast<const uint8_t*>(data);
    size_t sent = 0;
    while (sent < size) {
        const ssize_t result = send(fd, bytes + sent, size - sent, MSG_NOSIGNAL);
        if (result > 0) {
            sent += static_cast<size_t>(result);
            continue;
        }
        if (result < 0 && errno == EINTR) {
            continue;
        }
        return false;
    }
    return true;
}

bool receiveExact(int fd, void* data, size_t size, int32_t timeoutMs) {
    auto* bytes = static_cast<uint8_t*>(data);
    size_t received = 0;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
    while (received < size) {
        const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
                deadline - std::chrono::steady_clock::now());
        if (remaining.count() < 0) {
            return false;
        }
        pollfd descriptor{fd, POLLIN, 0};
        const int pollResult = poll(&descriptor, 1, static_cast<int>(remaining.count()));
        if (pollResult == 0) {
            return false;
        }
        if (pollResult < 0) {
            if (errno == EINTR) {
                continue;
            }
            return false;
        }
        if ((descriptor.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0 &&
            (descriptor.revents & POLLIN) == 0) {
            return false;
        }
        const ssize_t result = recv(fd, bytes + received, size - received, 0);
        if (result > 0) {
            received += static_cast<size_t>(result);
            continue;
        }
        if (result < 0 && errno == EINTR) {
            continue;
        }
        return false;
    }
    return true;
}

std::optional<std::string> currentExecutable() {
    char path[PATH_MAX + 1]{};
    const ssize_t length = readlink("/proc/self/exe", path, PATH_MAX);
    if (length <= 0 || length > PATH_MAX) {
        return std::nullopt;
    }
    path[length] = '\0';
    return std::string(path);
}

bool waitForWorker(pid_t pid, int32_t timeoutMs) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
    for (;;) {
        int status = 0;
        const pid_t result = waitpid(pid, &status, WNOHANG);
        if (result == pid || (result < 0 && errno == ECHILD)) {
            return true;
        }
        if (result < 0 && errno != EINTR) {
            return false;
        }
        if (std::chrono::steady_clock::now() >= deadline) {
            return false;
        }
        usleep(10'000);
    }
}

}  // namespace

struct FacehalCamera {
    pid_t workerPid = -1;
    int socketFd = -1;
    int frameFd = -1;
    uint8_t* frame = nullptr;
    size_t frameSize = 0;
    int32_t sensorOrientation = -1;

    void stopWorker(bool graceful) {
        if (workerPid <= 0) {
            if (socketFd >= 0) {
                close(socketFd);
                socketFd = -1;
            }
            return;
        }
        const pid_t pid = workerPid;
        bool forced = false;
        if (graceful && socketFd >= 0) {
            const WorkerRequest request{kWorkerClose, 0};
            (void)sendExact(socketFd, &request, sizeof(request));
        }
        if (!waitForWorker(pid, kWorkerExitTimeoutMs)) {
            forced = true;
            (void)kill(pid, SIGKILL);
            (void)waitpid(pid, nullptr, 0);
        }
        workerPid = -1;
        if (socketFd >= 0) {
            close(socketFd);
            socketFd = -1;
        }
        std::fprintf(
                stderr, "FaceHAL camera worker v2: stopped pid=%d forced=%d graceful=%d\n", pid,
                forced ? 1 : 0, graceful ? 1 : 0);
        std::fflush(stderr);
        usleep(100'000);
    }

    ~FacehalCamera() {
        stopWorker(true);
        if (frame != nullptr && frameSize > 0) {
            munmap(frame, frameSize);
        }
        if (frameFd >= 0) {
            close(frameFd);
        }
    }
};

extern "C" int32_t facehal_camera_worker_main(
        int32_t width, int32_t height, int32_t socketFd, int32_t frameFd,
        int32_t windowMode) {
    const pid_t parent = getppid();
    if (width <= 0 || height <= 0 || socketFd < 0 || frameFd < 0 ||
        (windowMode != kWindowModeVendorHandle && windowMode != kWindowModeStandard) ||
        prctl(PR_SET_PDEATHSIG, SIGKILL) != 0 || getppid() != parent) {
        _exit(2);
    }
    const size_t frameSize = static_cast<size_t>(width) * height * 3 / 2;
    void* mapping = mmap(nullptr, frameSize, PROT_READ | PROT_WRITE, MAP_SHARED, frameFd, 0);
    if (mapping == MAP_FAILED) {
        const WorkerHello hello{kCameraUnavailable, 0, -1};
        (void)sendExact(socketFd, &hello, sizeof(hello));
        _exit(3);
    }
    ACameraManager* discoveryManager = ACameraManager_create();
    if (discoveryManager == nullptr) {
        const WorkerHello hello{kCameraUnavailable, 0, -1};
        (void)sendExact(socketFd, &hello, sizeof(hello));
        _exit(4);
    }
    const std::vector<CameraSelection> candidates =
            findFrontCameras(discoveryManager, width, height);
    ACameraManager_delete(discoveryManager);
    if (candidates.empty()) {
        std::fprintf(stderr, "FaceHAL camera worker v2: no compatible front camera\n");
        const WorkerHello hello{kCameraUnavailable, 0, -1};
        (void)sendExact(socketFd, &hello, sizeof(hello));
        _exit(4);
    }
    std::unique_ptr<LocalCamera> camera;
    std::fprintf(
            stderr, "FaceHAL camera worker v2: initializing Camera2 candidates=%zu\n",
            candidates.size());
    std::fflush(stderr);
    for (const CameraSelection& candidate : candidates) {
        const int32_t preferredTemplate =
                candidate.id == "1" && candidate.captureWidth == width &&
                                candidate.captureHeight == height
                        ? TEMPLATE_RECORD
                        : TEMPLATE_PREVIEW;
        const int32_t alternateTemplate =
                preferredTemplate == TEMPLATE_RECORD ? TEMPLATE_PREVIEW : TEMPLATE_RECORD;
        for (const int32_t requestTemplate : {preferredTemplate, alternateTemplate}) {
            std::fprintf(
                    stderr,
                    "FaceHAL camera worker v2: trying id=%s capture=%dx%d output=%dx%d "
                    "orientation=%d backward=%d mono=%d depth_only=%d xiaomi_role=%d "
                    "score=%lld window=%s template=%d\n",
                    candidate.id.c_str(), candidate.captureWidth, candidate.captureHeight, width,
                    height, candidate.sensorOrientation, candidate.backwardCompatible ? 1 : 0,
                    candidate.monochrome ? 1 : 0, candidate.depthOnly ? 1 : 0,
                    candidate.xiaomiFaceRole ? 1 : 0,
                    static_cast<long long>(candidate.score),
                    windowMode == kWindowModeVendorHandle ? "native-handle" : "standard",
                    requestTemplate);
            auto attempt = std::make_unique<LocalCamera>(
                    width, height, candidate.captureWidth, candidate.captureHeight, candidate.id);
            if (initialize(attempt.get(), candidate, windowMode, requestTemplate)) {
                const int32_t firstFrame = probeCandidateNv21(
                        attempt.get(), static_cast<uint8_t*>(mapping), frameSize, width, height);
                if (firstFrame != static_cast<int32_t>(frameSize)) {
                    std::fprintf(
                            stderr,
                            "FaceHAL camera worker v2: candidate produced no usable first frame "
                            "id=%s result=%d\n",
                            candidate.id.c_str(), firstFrame);
                    continue;
                }
                camera = std::move(attempt);
                break;
            }
            std::fprintf(
                    stderr,
                    "FaceHAL camera worker v2: attempt failed id=%s capture=%dx%d "
                    "window=%s template=%d\n",
                    candidate.id.c_str(), candidate.captureWidth, candidate.captureHeight,
                    windowMode == kWindowModeVendorHandle ? "native-handle" : "standard",
                    requestTemplate);
        }
        if (camera != nullptr) {
            break;
        }
    }
    if (camera == nullptr) {
        const WorkerHello hello{kCameraUnavailable, 0, -1};
        (void)sendExact(socketFd, &hello, sizeof(hello));
        _exit(4);
    }
    const WorkerHello hello{
            0, static_cast<int32_t>(frameSize), camera->sensorOrientation};
    std::fprintf(
            stderr, "FaceHAL camera worker v2: Camera2 initialized id=%s capture=%dx%d\n",
            camera->cameraId.c_str(), camera->captureWidth, camera->captureHeight);
    std::fflush(stderr);
    if (!sendExact(socketFd, &hello, sizeof(hello))) {
        camera.reset();
        _exit(5);
    }
    bool primedFrame = true;
    for (;;) {
        WorkerRequest request{};
        if (!receiveExact(socketFd, &request, sizeof(request), INT32_MAX)) {
            camera.reset();
            _exit(0);
        }
        if (request.command == kWorkerClose) {
            camera.reset();
            _exit(0);
        }
        int32_t result = kInvalidArgument;
        if (request.command == kWorkerNextFrame) {
            if (primedFrame) {
                primedFrame = false;
                result = static_cast<int32_t>(frameSize);
            } else {
                result = nextLocalNv21(
                        camera.get(), static_cast<uint8_t*>(mapping), frameSize,
                        request.timeoutMs);
            }
        }
        if (!sendExact(socketFd, &result, sizeof(result))) {
            camera.reset();
            _exit(0);
        }
    }
}

extern "C" FacehalCamera* facehal_camera_open(int32_t width, int32_t height) {
    if (width <= 0 || height <= 0 || (width & 1) != 0 || (height & 1) != 0) {
        return nullptr;
    }
    const std::optional<std::string> executable = currentExecutable();
    if (!executable.has_value()) {
        return nullptr;
    }
    auto camera = std::make_unique<FacehalCamera>();
    camera->frameSize = static_cast<size_t>(width) * height * 3 / 2;
    camera->frameFd = static_cast<int>(
            syscall(__NR_memfd_create, "facehal-frame", MFD_CLOEXEC));
    if (camera->frameFd < 0 || ftruncate(camera->frameFd, camera->frameSize) != 0) {
        return nullptr;
    }
    void* mapping = mmap(
            nullptr, camera->frameSize, PROT_READ | PROT_WRITE, MAP_SHARED, camera->frameFd, 0);
    if (mapping == MAP_FAILED) {
        return nullptr;
    }
    camera->frame = static_cast<uint8_t*>(mapping);

    const std::string widthArgument = std::to_string(width);
    const std::string heightArgument = std::to_string(height);
    const std::string socketArgument = std::to_string(kWorkerSocketFd);
    const std::string frameArgument = std::to_string(kWorkerFrameFd);
    for (const int32_t windowMode : {kWindowModeVendorHandle, kWindowModeStandard}) {
        int sockets[2]{-1, -1};
        if (socketpair(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0, sockets) != 0) {
            continue;
        }
        camera->socketFd = sockets[0];
        const int childSocketSource = fcntl(sockets[1], F_DUPFD_CLOEXEC, 200);
        const int childFrameSource = fcntl(camera->frameFd, F_DUPFD_CLOEXEC, 200);
        if (childSocketSource < 0 || childFrameSource < 0) {
            if (childSocketSource >= 0) {
                close(childSocketSource);
            }
            if (childFrameSource >= 0) {
                close(childFrameSource);
            }
            close(sockets[0]);
            close(sockets[1]);
            camera->socketFd = -1;
            continue;
        }
        posix_spawn_file_actions_t actions;
        if (posix_spawn_file_actions_init(&actions) != 0) {
            close(childSocketSource);
            close(childFrameSource);
            close(sockets[0]);
            close(sockets[1]);
            camera->socketFd = -1;
            continue;
        }
        int actionStatus = posix_spawn_file_actions_addclose(&actions, sockets[0]);
        if (actionStatus == 0) {
            actionStatus =
                    posix_spawn_file_actions_adddup2(&actions, childSocketSource, kWorkerSocketFd);
        }
        if (actionStatus == 0) {
            actionStatus =
                    posix_spawn_file_actions_adddup2(&actions, childFrameSource, kWorkerFrameFd);
        }
        if (actionStatus == 0) {
            actionStatus = posix_spawn_file_actions_addclose(&actions, childSocketSource);
        }
        if (actionStatus == 0) {
            actionStatus = posix_spawn_file_actions_addclose(&actions, childFrameSource);
        }
        if (actionStatus == 0 && sockets[1] != kWorkerSocketFd && sockets[1] != kWorkerFrameFd) {
            actionStatus = posix_spawn_file_actions_addclose(&actions, sockets[1]);
        }
        if (actionStatus == 0 && camera->frameFd != kWorkerSocketFd &&
            camera->frameFd != kWorkerFrameFd) {
            actionStatus = posix_spawn_file_actions_addclose(&actions, camera->frameFd);
        }
        const std::string windowModeArgument = std::to_string(windowMode);
        char* arguments[] = {
                const_cast<char*>(executable->c_str()),
                const_cast<char*>("--facehal-camera-worker"),
                const_cast<char*>(widthArgument.c_str()),
                const_cast<char*>(heightArgument.c_str()),
                const_cast<char*>(socketArgument.c_str()),
                const_cast<char*>(frameArgument.c_str()),
                const_cast<char*>(windowModeArgument.c_str()),
                nullptr};
        int spawnStatus = actionStatus;
        if (spawnStatus == 0) {
            spawnStatus = posix_spawn(
                    &camera->workerPid, executable->c_str(), &actions, nullptr, arguments, environ);
        }
        posix_spawn_file_actions_destroy(&actions);
        close(childSocketSource);
        close(childFrameSource);
        close(sockets[1]);
        if (spawnStatus != 0) {
            camera->workerPid = -1;
            close(camera->socketFd);
            camera->socketFd = -1;
            continue;
        }
        WorkerHello hello{};
        if (receiveExact(camera->socketFd, &hello, sizeof(hello), kWorkerStartupTimeoutMs) &&
            hello.status == 0 && hello.frameSize == static_cast<int32_t>(camera->frameSize) &&
            (hello.sensorOrientation == 0 || hello.sensorOrientation == 90 ||
             hello.sensorOrientation == 180 || hello.sensorOrientation == 270)) {
            camera->sensorOrientation = hello.sensorOrientation;
            std::fprintf(
                    stderr,
                    "FaceHAL camera worker v2: started pid=%d frame=%zu orientation=%d "
                    "window=%s\n",
                    camera->workerPid, camera->frameSize, camera->sensorOrientation,
                    windowMode == kWindowModeVendorHandle ? "native-handle" : "standard");
            std::fflush(stderr);
            return camera.release();
        }
        std::fprintf(
                stderr, "FaceHAL camera worker v2: startup failed window=%s\n",
                windowMode == kWindowModeVendorHandle ? "native-handle" : "standard");
        camera->stopWorker(false);
    }
    return nullptr;
}

extern "C" void facehal_camera_close(FacehalCamera* camera) {
    delete camera;
}

extern "C" int32_t facehal_camera_frame_size(const FacehalCamera* camera) {
    if (camera == nullptr || camera->frameSize > static_cast<size_t>(INT32_MAX)) {
        return kInvalidArgument;
    }
    return static_cast<int32_t>(camera->frameSize);
}

extern "C" int32_t facehal_camera_sensor_orientation(const FacehalCamera* camera) {
    if (camera == nullptr) {
        return kInvalidArgument;
    }
    return camera->sensorOrientation;
}

extern "C" int32_t facehal_camera_next_nv21(
        FacehalCamera* camera, uint8_t* output, size_t capacity, int32_t timeoutMs) {
    if (camera == nullptr || output == nullptr || capacity < camera->frameSize || timeoutMs < 0) {
        return kInvalidArgument;
    }
    const WorkerRequest request{kWorkerNextFrame, timeoutMs};
    if (!sendExact(camera->socketFd, &request, sizeof(request))) {
        std::fprintf(stderr, "FaceHAL camera worker v2: request transport failed\n");
        std::fflush(stderr);
        camera->stopWorker(false);
        return kCameraUnavailable;
    }
    int32_t result = kCameraUnavailable;
    if (!receiveExact(camera->socketFd, &result, sizeof(result), timeoutMs + 1'000)) {
        std::fprintf(stderr, "FaceHAL camera worker v2: response transport timed out\n");
        std::fflush(stderr);
        camera->stopWorker(false);
        return kCameraUnavailable;
    }
    if (result == static_cast<int32_t>(camera->frameSize)) {
        std::memcpy(output, camera->frame, camera->frameSize);
    }
    return result;
}
