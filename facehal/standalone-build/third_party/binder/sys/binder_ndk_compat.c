#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct AIBinder AIBinder;
typedef struct AIBinder_Class AIBinder_Class;
typedef struct AParcel AParcel;
typedef int32_t binder_status_t;

typedef void (*set_thread_count_fn)(uint32_t);
typedef void (*void_fn)(void);
typedef binder_status_t (*add_service_fn)(AIBinder*, const char*);
typedef void (*set_requesting_sid_fn)(AIBinder*, bool);
typedef void (*mark_vintf_stability_fn)(AIBinder*);
typedef const char* (*get_class_descriptor_fn)(const AIBinder_Class*);
typedef AParcel* (*parcel_create_fn)(void);
typedef int32_t (*parcel_get_data_size_fn)(const AParcel*);
typedef binder_status_t (*parcel_append_from_fn)(const AParcel*, AParcel*, int32_t, int32_t);

static void* binder_ndk_handle(void) {
    static void* handle;
    if (handle == NULL) {
        // The target service already has this SONAME in its dependency graph.
        // RTLD_NEXT also handles vendor builds which export it from a loaded
        // linker namespace without allowing a second load.
        handle = dlopen("libbinder_ndk.so", RTLD_NOW | RTLD_LOCAL);
    }
    return handle;
}

static void* binder_ndk_symbol(const char* name) {
    void* symbol = dlsym(RTLD_NEXT, name);
    if (symbol == NULL) {
        void* handle = binder_ndk_handle();
        if (handle != NULL) {
            symbol = dlsym(handle, name);
        }
    }
    return symbol;
}

static void missing_symbol(const char* name) {
    const char prefix[] = "facehal: missing baseline libbinder_ndk symbol: ";
    (void)write(STDERR_FILENO, prefix, sizeof(prefix) - 1);
    (void)write(STDERR_FILENO, name, __builtin_strlen(name));
    (void)write(STDERR_FILENO, "\n", 1);
    abort();
}

bool facehal_binder_ndk_has_api31(void) {
    return binder_ndk_symbol("AParcel_create") != NULL &&
            binder_ndk_symbol("AParcel_getDataSize") != NULL &&
            binder_ndk_symbol("AParcel_appendFrom") != NULL;
}

void ABinderProcess_setThreadPoolMaxThreadCount(uint32_t num_threads) {
    set_thread_count_fn function =
            (set_thread_count_fn)binder_ndk_symbol("ABinderProcess_setThreadPoolMaxThreadCount");
    if (function == NULL) {
        missing_symbol("ABinderProcess_setThreadPoolMaxThreadCount");
    }
    function(num_threads);
}

void ABinderProcess_startThreadPool(void) {
    void_fn function = (void_fn)binder_ndk_symbol("ABinderProcess_startThreadPool");
    if (function == NULL) {
        missing_symbol("ABinderProcess_startThreadPool");
    }
    function();
}

void ABinderProcess_joinThreadPool(void) {
    void_fn function = (void_fn)binder_ndk_symbol("ABinderProcess_joinThreadPool");
    if (function == NULL) {
        missing_symbol("ABinderProcess_joinThreadPool");
    }
    function();
}

binder_status_t AServiceManager_addService(AIBinder* binder, const char* instance) {
    add_service_fn function =
            (add_service_fn)binder_ndk_symbol("AServiceManager_addService");
    if (function == NULL) {
        missing_symbol("AServiceManager_addService");
    }
    return function(binder, instance);
}

void AIBinder_setRequestingSid(AIBinder* binder, bool requesting_sid) {
    set_requesting_sid_fn function =
            (set_requesting_sid_fn)binder_ndk_symbol("AIBinder_setRequestingSid");
    if (function != NULL) {
        function(binder, requesting_sid);
    }
}

void AIBinder_markVintfStability(AIBinder* binder) {
    mark_vintf_stability_fn function =
            (mark_vintf_stability_fn)binder_ndk_symbol("AIBinder_markVintfStability");
    if (function != NULL) {
        function(binder);
    }
}

const char* AIBinder_Class_getDescriptor(const AIBinder_Class* clazz) {
    get_class_descriptor_fn function =
            (get_class_descriptor_fn)binder_ndk_symbol("AIBinder_Class_getDescriptor");
    if (function != NULL) {
        return function(clazz);
    }
    return "";
}

AParcel* AParcel_create(void) {
    parcel_create_fn function = (parcel_create_fn)binder_ndk_symbol("AParcel_create");
    return function != NULL ? function() : NULL;
}

int32_t AParcel_getDataSize(const AParcel* parcel) {
    parcel_get_data_size_fn function =
            (parcel_get_data_size_fn)binder_ndk_symbol("AParcel_getDataSize");
    return function != NULL ? function(parcel) : -1;
}

binder_status_t AParcel_appendFrom(
        const AParcel* from, AParcel* to, int32_t start, int32_t size) {
    parcel_append_from_fn function =
            (parcel_append_from_fn)binder_ndk_symbol("AParcel_appendFrom");
    return function != NULL ? function(from, to, start, size) : -38;
}
