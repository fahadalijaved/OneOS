#include "SenseTimeBridge.h"

#include <android/log.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <cstdlib>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <memory>
#include <mutex>
#include <string>

namespace {

constexpr char kTag[] = "FaceHalSenseTime";
constexpr size_t kTemplatePathCapacity = 128;
constexpr char kTemplateFileSuffix[] = "/template_file.xiaomi";
constexpr size_t kTemplateCount = 2;
constexpr size_t kTemplateRecordSize = 0x760;
constexpr size_t kTemplateFileSize = kTemplateCount * kTemplateRecordSize;
constexpr int32_t kNv21Format = 3;

struct STImage {
    const uint8_t* data;
    int32_t format;
    int32_t width;
    int32_t height;
    int32_t stride;
};

static_assert(sizeof(STImage) == 24);

using ManagerInit = void (*)();
using ManagerReset = void (*)();
using TeeCreateHandle = int32_t (*)(void**, void*);
using TeeInitialize = int32_t (*)(void*, const char*);
using ManagerUpgradeVersion = int32_t (*)(void*);
using ManagerImageProcess = int32_t (*)(void*, STImage, int32_t, int32_t);
using ManagerDeleteFace = void (*)(int32_t);
using ManagerDeleteAllFaces = void (*)();
using TeeUninitialize = int32_t (*)(void*);
using TeeDestroyHandle = int32_t (*)(void*);

std::mutex gAlgorithmMutex;

enum class TemplateFileState {
    Missing,
    Valid,
    Invalid,
};

bool readFully(int file, uint8_t* output, size_t size) {
    size_t offset = 0;
    while (offset < size) {
        const ssize_t result = read(file, output + offset, size - offset);
        if (result > 0) {
            offset += static_cast<size_t>(result);
            continue;
        }
        if (result < 0 && errno == EINTR) {
            continue;
        }
        return false;
    }
    uint8_t trailing = 0;
    return read(file, &trailing, sizeof(trailing)) == 0;
}

bool writeFully(int file, const uint8_t* input, size_t size) {
    size_t offset = 0;
    while (offset < size) {
        const ssize_t result = write(file, input + offset, size - offset);
        if (result > 0) {
            offset += static_cast<size_t>(result);
            continue;
        }
        if (result < 0 && errno == EINTR) {
            continue;
        }
        return false;
    }
    return true;
}

bool validTemplateRecords(const std::array<uint8_t, kTemplateFileSize>& bytes) {
    for (size_t index = 0; index < kTemplateCount; ++index) {
        int32_t enrollmentId = 0;
        std::memcpy(&enrollmentId, bytes.data() + index * kTemplateRecordSize,
                    sizeof(enrollmentId));
        if (enrollmentId < -1) {
            return false;
        }
    }
    return true;
}

TemplateFileState loadTemplateFile(
        const std::string& path, std::array<uint8_t, kTemplateFileSize>* output) {
    const int file = open(path.c_str(), O_RDONLY | O_CLOEXEC);
    if (file < 0) {
        return errno == ENOENT ? TemplateFileState::Missing : TemplateFileState::Invalid;
    }
    const bool valid = readFully(file, output->data(), output->size()) &&
                       validTemplateRecords(*output);
    close(file);
    return valid ? TemplateFileState::Valid : TemplateFileState::Invalid;
}

bool syncDirectory(const std::string& directory) {
    const int file = open(directory.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (file < 0) {
        return false;
    }
    const bool success = fsync(file) == 0;
    close(file);
    return success;
}

bool writeTemplateFileAtomically(
        const std::string& path, const std::string& directory,
        const std::array<uint8_t, kTemplateFileSize>& bytes) {
    const std::string temporaryPath = path + ".tmp";
    const int file = open(temporaryPath.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (file < 0) {
        return false;
    }
    const bool written = writeFully(file, bytes.data(), bytes.size());
    const bool synced = written && fsync(file) == 0;
    const bool closed = close(file) == 0;
    if (!synced || !closed || rename(temporaryPath.c_str(), path.c_str()) != 0 ||
        !syncDirectory(directory)) {
        unlink(temporaryPath.c_str());
        return false;
    }
    return true;
}

template <typename T>
T resolve(void* library, const char* symbol) {
    return reinterpret_cast<T>(dlsym(library, symbol));
}

void* openLibrary() {
    if (const char* overridePath = std::getenv("FACEHAL_ALGORITHM_LIBRARY");
        overridePath != nullptr && overridePath[0] != '\0') {
        if (void* library = dlopen(overridePath, RTLD_NOW | RTLD_LOCAL); library != nullptr) {
            __android_log_print(ANDROID_LOG_INFO, kTag, "loaded test override %s", overridePath);
            return library;
        }
        __android_log_print(
                ANDROID_LOG_ERROR, kTag, "unable to load test override %s: %s", overridePath,
                dlerror());
        return nullptr;
    }
    constexpr std::array<const char*, 2> candidates = {
            "/vendor/lib64/facehal/libjni_stfaceunlock_api.so",
            "libjni_stfaceunlock_api.so",
    };
    for (const char* candidate : candidates) {
        if (void* library = dlopen(candidate, RTLD_NOW | RTLD_LOCAL); library != nullptr) {
            __android_log_print(ANDROID_LOG_INFO, kTag, "loaded %s", candidate);
            return library;
        }
    }
    __android_log_print(ANDROID_LOG_ERROR, kTag, "unable to load algorithm: %s", dlerror());
    return nullptr;
}

}  // namespace

struct FacehalAlgorithm {
    void* library = nullptr;
    void* engine = nullptr;
    void** globalEngineSlot = nullptr;
    ManagerInit managerInit = nullptr;
    ManagerReset managerReset = nullptr;
    ManagerImageProcess process = nullptr;
    ManagerDeleteFace deleteFace = nullptr;
    ManagerDeleteAllFaces deleteAllFaces = nullptr;
    TeeUninitialize uninitialize = nullptr;
    TeeDestroyHandle destroyHandle = nullptr;
    int32_t* currentFaceId = nullptr;
    int32_t* activeTemplates = nullptr;
    int32_t* orientation = nullptr;
    int32_t* imageFormat = nullptr;
    uint8_t* templateFile = nullptr;
    std::string templateDirectory;
    std::string templatePath;
    std::string backupPath;
};

namespace {

bool restoreOrProtectTemplate(FacehalAlgorithm* algorithm) {
    std::array<uint8_t, kTemplateFileSize> primary{};
    const TemplateFileState primaryState = loadTemplateFile(algorithm->templatePath, &primary);
    std::array<uint8_t, kTemplateFileSize> backup{};
    const TemplateFileState backupState = loadTemplateFile(algorithm->backupPath, &backup);

    if (primaryState == TemplateFileState::Valid) {
        return writeTemplateFileAtomically(
                algorithm->backupPath, algorithm->templateDirectory, primary);
    }
    if (backupState == TemplateFileState::Valid) {
        return writeTemplateFileAtomically(
                algorithm->templatePath, algorithm->templateDirectory, backup);
    }
    return primaryState == TemplateFileState::Missing && backupState == TemplateFileState::Missing;
}

bool validateAndBackupTemplate(FacehalAlgorithm* algorithm) {
    std::array<uint8_t, kTemplateFileSize> bytes{};
    if (loadTemplateFile(algorithm->templatePath, &bytes) != TemplateFileState::Valid) {
        return false;
    }
    return writeTemplateFileAtomically(
            algorithm->backupPath, algorithm->templateDirectory, bytes);
}

bool rollbackTemplate(FacehalAlgorithm* algorithm) {
    std::array<uint8_t, kTemplateFileSize> backup{};
    if (loadTemplateFile(algorithm->backupPath, &backup) != TemplateFileState::Valid ||
        !writeTemplateFileAtomically(
                algorithm->templatePath, algorithm->templateDirectory, backup)) {
        return false;
    }
    algorithm->managerInit();
    return true;
}

}  // namespace

extern "C" FacehalAlgorithm* facehal_algorithm_open(const char* templateDirectory) {
    std::lock_guard runtimeLock(gAlgorithmMutex);
    if (templateDirectory == nullptr || templateDirectory[0] == '\0' ||
        std::strlen(templateDirectory) + std::strlen(kTemplateFileSuffix) >=
                kTemplatePathCapacity) {
        return nullptr;
    }
    std::fprintf(stderr, "FaceHAL algorithm: opening template directory %s\n", templateDirectory);
    std::fflush(stderr);

    auto algorithm = std::make_unique<FacehalAlgorithm>();
    algorithm->library = openLibrary();
    if (algorithm->library == nullptr) {
        return nullptr;
    }

    algorithm->managerInit = resolve<ManagerInit>(algorithm->library, "_Z15st_manager_initv");
    algorithm->managerReset = resolve<ManagerReset>(algorithm->library, "_Z16st_manager_resetv");
    const auto createHandle =
            resolve<TeeCreateHandle>(algorithm->library, "st_tee_create_handle");
    const auto initialize = resolve<TeeInitialize>(algorithm->library, "st_tee_initialize");
    const auto upgrade = resolve<ManagerUpgradeVersion>(
            algorithm->library, "_Z26st_manager_upgrade_versionPv");
    algorithm->process = resolve<ManagerImageProcess>(
            algorithm->library, "_Z24st_manager_image_processPv7STImageii");
    algorithm->deleteFace = resolve<ManagerDeleteFace>(
            algorithm->library, "_Z25st_manager_delete_face_idi");
    algorithm->deleteAllFaces = resolve<ManagerDeleteAllFaces>(
            algorithm->library, "_Z26st_manager_delete_all_facev");
    algorithm->uninitialize =
            resolve<TeeUninitialize>(algorithm->library, "st_tee_uninitialize");
    algorithm->destroyHandle =
            resolve<TeeDestroyHandle>(algorithm->library, "st_tee_destroy_handle");
    algorithm->currentFaceId =
            resolve<int32_t*>(algorithm->library, "cur_face_id");
    algorithm->activeTemplates =
            resolve<int32_t*>(algorithm->library, "my_template_aut");
    algorithm->orientation = resolve<int32_t*>(algorithm->library, "mi_orientation");
    algorithm->imageFormat = resolve<int32_t*>(algorithm->library, "mi_image_format");
    algorithm->templateFile = resolve<uint8_t*>(algorithm->library, "my_template_file");
    algorithm->globalEngineSlot = resolve<void**>(algorithm->library, "xiaomi_handler");
    char* contextPath = resolve<char*>(algorithm->library, "context_file_path");
    char* templatePath = resolve<char*>(algorithm->library, "template_file_path");

    if (algorithm->managerInit == nullptr || algorithm->managerReset == nullptr ||
        createHandle == nullptr || initialize == nullptr || upgrade == nullptr ||
        algorithm->process == nullptr || algorithm->deleteFace == nullptr ||
        algorithm->deleteAllFaces == nullptr || algorithm->uninitialize == nullptr ||
        algorithm->destroyHandle == nullptr || algorithm->currentFaceId == nullptr ||
        algorithm->activeTemplates == nullptr || algorithm->orientation == nullptr ||
        algorithm->imageFormat == nullptr || algorithm->templateFile == nullptr ||
        algorithm->globalEngineSlot == nullptr || contextPath == nullptr ||
        templatePath == nullptr) {
        __android_log_print(ANDROID_LOG_ERROR, kTag, "required algorithm symbol is missing: %s",
                            dlerror());
        dlclose(algorithm->library);
        return nullptr;
    }

    if (*algorithm->globalEngineSlot != nullptr) {
        __android_log_print(ANDROID_LOG_ERROR, kTag, "algorithm runtime is already active");
        dlclose(algorithm->library);
        return nullptr;
    }

    std::strncpy(contextPath, templateDirectory, kTemplatePathCapacity - 1);
    contextPath[kTemplatePathCapacity - 1] = '\0';
    *algorithm->currentFaceId = -1;
    algorithm->activeTemplates[0] = 1;
    algorithm->activeTemplates[1] = 1;
    *algorithm->orientation = 15;
    *algorithm->imageFormat = kNv21Format;

    algorithm->templateDirectory = templateDirectory;
    algorithm->templatePath = std::string(templateDirectory) + kTemplateFileSuffix;
    algorithm->backupPath = algorithm->templatePath + ".bak";
    if (!restoreOrProtectTemplate(algorithm.get())) {
        __android_log_print(ANDROID_LOG_ERROR, kTag, "template file is corrupt and unrecoverable");
        dlclose(algorithm->library);
        return nullptr;
    }

    algorithm->managerInit();
    std::array<char, kTemplatePathCapacity> expectedTemplatePath{};
    const int expectedLength = std::snprintf(
            expectedTemplatePath.data(), expectedTemplatePath.size(), "%s%s", templateDirectory,
            kTemplateFileSuffix);
    if (expectedLength < 0 || static_cast<size_t>(expectedLength) >= expectedTemplatePath.size() ||
        std::strcmp(templatePath, expectedTemplatePath.data()) != 0) {
        __android_log_print(ANDROID_LOG_ERROR, kTag,
                            "algorithm template path initialization failed");
        dlclose(algorithm->library);
        return nullptr;
    }

    int32_t status = createHandle(algorithm->globalEngineSlot, nullptr);
    const bool createdHandle = status == 0 && *algorithm->globalEngineSlot != nullptr;
    algorithm->engine = createdHandle ? *algorithm->globalEngineSlot : nullptr;
    if (status == 0) {
        status = initialize(algorithm->engine, templateDirectory);
    }
    if (status == 0) {
        status = upgrade(algorithm->engine);
    }
    if (status == 0 && !validateAndBackupTemplate(algorithm.get())) {
        status = FACEHAL_ALGORITHM_ERROR_INITIALIZATION;
    }
    if (status != 0 || algorithm->engine == nullptr) {
        std::fprintf(stderr, "FaceHAL algorithm: initialization failed status=%d engine=%p\n", status,
                     algorithm->engine);
        std::fflush(stderr);
        __android_log_print(ANDROID_LOG_ERROR, kTag, "algorithm initialization failed: %d",
                            status);
        if (createdHandle) {
            const int32_t uninitializeStatus = algorithm->uninitialize(algorithm->engine);
            const int32_t destroyStatus = algorithm->destroyHandle(algorithm->engine);
            __android_log_print(ANDROID_LOG_WARN, kTag,
                                "cleanup after initialization failure: uninitialize=%d destroy=%d",
                                uninitializeStatus, destroyStatus);
            *algorithm->globalEngineSlot = nullptr;
        }
        dlclose(algorithm->library);
        return nullptr;
    }
    std::fprintf(stderr, "FaceHAL algorithm: initialization complete engine=%p\n", algorithm->engine);
    std::fflush(stderr);
    return algorithm.release();
}

extern "C" void facehal_algorithm_close(FacehalAlgorithm* algorithm) {
    if (algorithm == nullptr) {
        return;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    if (algorithm->engine != nullptr) {
        const int32_t uninitializeStatus = algorithm->uninitialize(algorithm->engine);
        const int32_t destroyStatus = algorithm->destroyHandle(algorithm->engine);
        if (uninitializeStatus != 0 || destroyStatus != 0) {
            __android_log_print(ANDROID_LOG_WARN, kTag,
                                "algorithm shutdown failed: uninitialize=%d destroy=%d",
                                uninitializeStatus, destroyStatus);
        }
        algorithm->engine = nullptr;
        *algorithm->globalEngineSlot = nullptr;
    }
    if (algorithm->library != nullptr) {
        dlclose(algorithm->library);
    }
    delete algorithm;
}

extern "C" int32_t facehal_algorithm_process_nv21(
        FacehalAlgorithm* algorithm, const uint8_t* image, size_t imageSize, int32_t width,
        int32_t height, int32_t stride, int32_t action, int32_t config) {
    if (algorithm == nullptr || image == nullptr || width <= 0 || height <= 0 || stride < width ||
        stride != width || (width & 1) != 0 || (height & 1) != 0 ||
        imageSize < static_cast<size_t>(width) * static_cast<size_t>(height) * 3 / 2 ||
        (action != FACEHAL_ALGORITHM_AUTHENTICATE && action != FACEHAL_ALGORITHM_ENROLL)) {
        return FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    if (action == FACEHAL_ALGORITHM_ENROLL) {
        algorithm->activeTemplates[0] = 1;
        algorithm->activeTemplates[1] = 1;
    }
    *algorithm->imageFormat = kNv21Format;
    const STImage stImage{image, kNv21Format, width, height, stride};
    const int32_t status = algorithm->process(algorithm->engine, stImage, action, config);
    if (action == FACEHAL_ALGORITHM_ENROLL && (status == 0 || status == 0x65) &&
        !validateAndBackupTemplate(algorithm)) {
        if (!rollbackTemplate(algorithm)) {
            __android_log_print(ANDROID_LOG_ERROR, kTag, "unable to roll back corrupt enrollment");
        }
        return FACEHAL_ALGORITHM_ERROR_INITIALIZATION;
    }
    return status;
}

extern "C" int32_t facehal_algorithm_current_face_id(const FacehalAlgorithm* algorithm) {
    if (algorithm == nullptr || algorithm->currentFaceId == nullptr) {
        return FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    return *algorithm->currentFaceId;
}

extern "C" int32_t facehal_algorithm_enumerate(
        const FacehalAlgorithm* algorithm, int32_t* enrollmentIds, size_t capacity) {
    if (algorithm == nullptr || (capacity > 0 && enrollmentIds == nullptr)) {
        return FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    size_t count = 0;
    for (size_t index = 0; index < kTemplateCount; ++index) {
        int32_t enrollmentId = 0;
        std::memcpy(&enrollmentId, algorithm->templateFile + index * kTemplateRecordSize,
                    sizeof(enrollmentId));
        if (enrollmentId < 1) {
            continue;
        }
        if (count < capacity) {
            enrollmentIds[count] = enrollmentId;
        }
        ++count;
    }
    return static_cast<int32_t>(count);
}

extern "C" int32_t facehal_algorithm_slots(
        const FacehalAlgorithm* algorithm, int32_t* enrollmentIds, size_t capacity) {
    if (algorithm == nullptr || enrollmentIds == nullptr || capacity < kTemplateCount) {
        return FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    for (size_t index = 0; index < kTemplateCount; ++index) {
        std::memcpy(&enrollmentIds[index], algorithm->templateFile + index * kTemplateRecordSize,
                    sizeof(enrollmentIds[index]));
        if (enrollmentIds[index] < 1) {
            enrollmentIds[index] = 0;
        }
    }
    return static_cast<int32_t>(kTemplateCount);
}

extern "C" int32_t facehal_algorithm_remove(
        FacehalAlgorithm* algorithm, int32_t enrollmentId) {
    if (algorithm == nullptr || enrollmentId < 1) {
        return FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    if (!restoreOrProtectTemplate(algorithm)) {
        return FACEHAL_ALGORITHM_ERROR_INITIALIZATION;
    }
    algorithm->deleteFace(enrollmentId);
    if (!validateAndBackupTemplate(algorithm)) {
        if (!rollbackTemplate(algorithm)) {
            __android_log_print(ANDROID_LOG_ERROR, kTag, "unable to roll back corrupt removal");
        }
        return FACEHAL_ALGORITHM_ERROR_INITIALIZATION;
    }
    return 0;
}

extern "C" int32_t facehal_algorithm_remove_all(FacehalAlgorithm* algorithm) {
    if (algorithm == nullptr) {
        return FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    if (!restoreOrProtectTemplate(algorithm)) {
        return FACEHAL_ALGORITHM_ERROR_INITIALIZATION;
    }
    algorithm->deleteAllFaces();
    if (!validateAndBackupTemplate(algorithm)) {
        if (!rollbackTemplate(algorithm)) {
            __android_log_print(ANDROID_LOG_ERROR, kTag,
                                "unable to roll back corrupt remove-all");
        }
        return FACEHAL_ALGORITHM_ERROR_INITIALIZATION;
    }
    return 0;
}

extern "C" int32_t facehal_algorithm_set_active_slot(
        FacehalAlgorithm* algorithm, int32_t slot) {
    if (algorithm == nullptr || slot < -1 || slot >= static_cast<int32_t>(kTemplateCount)) {
        return FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    for (size_t index = 0; index < kTemplateCount; ++index) {
        algorithm->activeTemplates[index] =
                slot == -1 || slot == static_cast<int32_t>(index) ? 1 : 0;
    }
    return 0;
}

extern "C" int32_t facehal_algorithm_reset(FacehalAlgorithm* algorithm) {
    if (algorithm == nullptr || algorithm->managerReset == nullptr ||
        algorithm->currentFaceId == nullptr) {
        return FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    algorithm->managerReset();
    *algorithm->currentFaceId = -1;
    return 0;
}

extern "C" void facehal_algorithm_set_orientation(
        FacehalAlgorithm* algorithm, int32_t orientation) {
    if (algorithm == nullptr) {
        return;
    }
    std::lock_guard runtimeLock(gAlgorithmMutex);
    switch (orientation) {
        case 1:
        case 2:
        case 4:
        case 8:
            *algorithm->orientation = orientation;
            break;
        default:
            *algorithm->orientation = 15;
            break;
    }
}
