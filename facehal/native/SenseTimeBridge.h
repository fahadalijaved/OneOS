#pragma once

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct FacehalAlgorithm FacehalAlgorithm;

enum FacehalAlgorithmAction {
    FACEHAL_ALGORITHM_AUTHENTICATE = 0,
    FACEHAL_ALGORITHM_ENROLL = 1,
};

enum FacehalAlgorithmError {
    FACEHAL_ALGORITHM_ERROR_INVALID_ARGUMENT = -1,
    FACEHAL_ALGORITHM_ERROR_LIBRARY_UNAVAILABLE = -2,
    FACEHAL_ALGORITHM_ERROR_SYMBOL_MISSING = -3,
    FACEHAL_ALGORITHM_ERROR_INITIALIZATION = -4,
};

FacehalAlgorithm* facehal_algorithm_open(const char* template_directory);
void facehal_algorithm_close(FacehalAlgorithm* algorithm);

int32_t facehal_algorithm_process_nv21(
        FacehalAlgorithm* algorithm, const uint8_t* image, size_t image_size, int32_t width,
        int32_t height, int32_t stride, int32_t action, int32_t config);
int32_t facehal_algorithm_current_face_id(const FacehalAlgorithm* algorithm);
int32_t facehal_algorithm_enumerate(
        const FacehalAlgorithm* algorithm, int32_t* enrollment_ids, size_t capacity);
int32_t facehal_algorithm_slots(
        const FacehalAlgorithm* algorithm, int32_t* enrollment_ids, size_t capacity);
int32_t facehal_algorithm_remove(FacehalAlgorithm* algorithm, int32_t enrollment_id);
int32_t facehal_algorithm_remove_all(FacehalAlgorithm* algorithm);
int32_t facehal_algorithm_set_active_slot(FacehalAlgorithm* algorithm, int32_t slot);
int32_t facehal_algorithm_reset(FacehalAlgorithm* algorithm);
void facehal_algorithm_set_orientation(FacehalAlgorithm* algorithm, int32_t orientation);

#ifdef __cplusplus
}
#endif
