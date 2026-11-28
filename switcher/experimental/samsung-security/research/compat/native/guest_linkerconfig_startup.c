#define _GNU_SOURCE
#include "guest_linkerconfig_startup.h"

#include "guest_readback_identity.h"
#include "guest_tree_sha256.h"

#include <string.h>
#include <sys/statvfs.h>

enum slot {
    ROOT, DEV, PROPERTY_DIR, INFO, VNDK, DEBUG, SERIAL,
    APEX, XML, RUNTIME, MANIFEST, RUNTIME_ETC, RUNTIME_CONFIG,
    OUTPUT_DIR, BASE, COMPANION, SYSTEM, SYSTEM_BIN, SYSTEM_ETC, APP, RUNTIME_BIN, LINKER, SLOTS
};

_Static_assert((int)OUTPUT_DIR == GUEST_LINKERCONFIG_STARTUP_INPUT_COUNT, "immutable input slots");

static const struct {
    enum slot parent;
    const char *name;
} names[SLOTS] = {
    [DEV] = { ROOT, "dev" }, [PROPERTY_DIR] = { DEV, "__properties__" },
    [INFO] = { PROPERTY_DIR, "property_info" }, [VNDK] = { PROPERTY_DIR, GUEST_TREE_VNDK_PROP_AREA },
    [DEBUG] = { PROPERTY_DIR, GUEST_TREE_DEBUG_PROP_AREA }, [SERIAL] = { PROPERTY_DIR, "properties_serial" },
    [APEX] = { ROOT, "apex" }, [XML] = { APEX, "apex-info-list.xml" },
    [RUNTIME] = { APEX, "com.android.runtime" }, [MANIFEST] = { RUNTIME, "apex_manifest.pb" },
    [RUNTIME_ETC] = { RUNTIME, "etc" }, [RUNTIME_CONFIG] = { RUNTIME_ETC, "linker.config.pb" },
    [OUTPUT_DIR] = { ROOT, "linkerconfig" }, [BASE] = { OUTPUT_DIR, "ld.config.txt" },
    [COMPANION] = { OUTPUT_DIR, "apex.libraries.config.txt" },
    [SYSTEM] = { ROOT, "system" }, [SYSTEM_BIN] = { SYSTEM, "bin" }, [SYSTEM_ETC] = { SYSTEM, "etc" },
    [APP] = { SYSTEM_BIN, "app_process64" }, [RUNTIME_BIN] = { RUNTIME, "bin" }, [LINKER] = { RUNTIME_BIN, "linker64" },
};

static void input_slots(const struct guest_linkerconfig_startup_files *files, int fd[SLOTS]) {
    const struct guest_linkerconfig_property_files *p = &files->properties;
    const struct guest_apex_runtime_files *a = &files->runtime;
    const int inputs[COMPANION] = {
        p->root_fd, p->dev_fd, p->directory_fd, p->info_fd, p->vndk_fd, p->debug_fd, p->serial_fd,
        a->apex_fd, a->xml_fd, a->runtime_fd, a->manifest_fd, a->etc_fd, a->config_fd,
        files->output_directory_fd, files->output_base_fd,
    };
    memcpy(fd, inputs, sizeof(inputs));
}

static int validate_scratch(const struct guest_linkerconfig_startup_scratch *scratch) {
    if (!scratch || !scratch->xml || !scratch->xml_capacity || !scratch->work) return guest_readback_refuse(EINVAL);
    if (scratch->work_capacity < GUEST_LINKERCONFIG_PROPERTY_SCRATCH_BYTES) return guest_readback_refuse(EFBIG);
    const uintptr_t xml = (uintptr_t)scratch->xml, work = (uintptr_t)scratch->work;
    if (xml <= work ? work - xml < scratch->xml_capacity : xml - work < scratch->work_capacity)
        return guest_readback_refuse(EINVAL);
    return 0;
}

static int distinct_slots(const int fd[SLOTS], unsigned count) {
    for (unsigned i = 0; i < count; ++i) {
        if (fd[i] < 0) return guest_readback_refuse(EINVAL);
        for (unsigned j = 0; j < i; ++j) {
            if (fd[i] == fd[j]) return guest_readback_refuse(EINVAL);
        }
    }
    return 0;
}

static int snapshot(const int fd[SLOTS], struct statx held[SLOTS], unsigned count) {
    for (unsigned i = 0; i < count; ++i) {
        if (guest_readback_stat(fd[i], "", &held[i]) < 0) return -1;
        if (i != ROOT) {
            struct statx named;
            if (guest_readback_stat(fd[names[i].parent], names[i].name, &named) < 0) return -1;
            if (!guest_readback_same_node(&held[i], &named)) return guest_readback_refuse(ESTALE);
        }
        for (unsigned j = 0; j < i; ++j) {
            if (held[i].stx_ino == held[j].stx_ino && held[i].stx_dev_major == held[j].stx_dev_major
                    && held[i].stx_dev_minor == held[j].stx_dev_minor)
                return guest_readback_refuse(EPERM);
        }
    }
    return 0;
}

static int stable(const struct statx before[SLOTS], const struct statx after[SLOTS], unsigned count) {
    for (unsigned i = 0; i < count; ++i) {
        if (!guest_readback_same_node(&before[i], &after[i])) return guest_readback_refuse(ESTALE);
    }
    return 0;
}

static void input_identity(const struct statx held[SLOTS], unsigned char digest[32]) {
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    for (unsigned i = 0; i < OUTPUT_DIR; ++i) {
        const struct statx *node = &held[i];
        /* Compare the same fixed field order inside this owner. No struct padding. */
        const uint64_t fields[] = {
            node->stx_mnt_id, node->stx_dev_major, node->stx_dev_minor, node->stx_ino,
            node->stx_mode, node->stx_uid, node->stx_gid, node->stx_nlink, node->stx_size,
            (uint64_t)node->stx_mtime.tv_sec, node->stx_mtime.tv_nsec,
            (uint64_t)node->stx_ctime.tv_sec, node->stx_ctime.tv_nsec,
        };
        guest_tree_sha256_update(&hash, fields, sizeof(fields));
    }
    guest_tree_sha256_final(&hash, digest);
}

static int input_samples_match(const struct statx held[SLOTS], const struct guest_linkerconfig_property_sample *p,
        const struct guest_apex_runtime_sample *a) {
    return p->root_mount_id == held[ROOT].stx_mnt_id && p->root_inode == held[ROOT].stx_ino
            && p->dev_mount_id == held[DEV].stx_mnt_id && p->directory_inode == held[PROPERTY_DIR].stx_ino
            && a->xml.mount_id == held[APEX].stx_mnt_id && a->xml.directory_inode == held[APEX].stx_ino
            && a->xml.device_major == held[APEX].stx_dev_major && a->xml.device_minor == held[APEX].stx_dev_minor
            && a->xml.file_inode == held[XML].stx_ino && a->xml.bytes == held[XML].stx_size
            && a->runtime_mount_id == held[RUNTIME].stx_mnt_id && a->runtime_inode == held[RUNTIME].stx_ino
            && a->manifest_inode == held[MANIFEST].stx_ino && a->etc_inode == held[RUNTIME_ETC].stx_ino
            && a->config_inode == held[RUNTIME_CONFIG].stx_ino;
}

static int generation_node_matches(const struct guest_linkerconfig_generation_node *sample, const struct statx *node) {
    return sample->mount_id == node->stx_mnt_id && sample->inode == node->stx_ino
            && sample->device_major == node->stx_dev_major && sample->device_minor == node->stx_dev_minor
            && sample->mode == node->stx_mode && sample->uid == node->stx_uid && sample->gid == node->stx_gid;
}

int guest_linkerconfig_startup_begin(const struct guest_linkerconfig_startup_files *files,
        const struct guest_linkerconfig_startup_scratch *scratch, struct guest_linkerconfig_startup_start *out) {
    if (!files || !out) return guest_readback_refuse(EINVAL);
    if (validate_scratch(scratch) < 0) return -1;
    int fd[SLOTS];
    input_slots(files, fd);
    struct statx before[SLOTS], after[SLOTS];
    struct guest_linkerconfig_startup_start result;
    if (distinct_slots(fd, COMPANION) < 0 || snapshot(fd, before, COMPANION) < 0
            || guest_linkerconfig_property_readback(&files->properties, scratch->work, scratch->work_capacity,
                    &result.properties) < 0
            || guest_apex_info_readback_runtime(&files->runtime, scratch->xml, scratch->xml_capacity, &result.runtime) < 0
            || guest_linkerconfig_generation_begin(fd[ROOT], fd[OUTPUT_DIR], fd[BASE], &result.generation) < 0
            || snapshot(fd, after, COMPANION) < 0 || stable(before, after, COMPANION) < 0) return -1;
    if (!input_samples_match(before, &result.properties, &result.runtime)
            || !generation_node_matches(&result.generation.root, &before[ROOT])
            || !generation_node_matches(&result.generation.directory, &before[OUTPUT_DIR])
            || !generation_node_matches(&result.generation.base, &before[BASE])) return guest_readback_refuse(ESTALE);
    memcpy(result.input_fds, fd, sizeof(result.input_fds));
    input_identity(before, result.input_identity_sha256);
    *out = result;
    return 0;
}

static int entry_names(const int fd[SLOTS], struct statx *symlink) {
    struct statx override;
    if (guest_readback_stat(fd[SYSTEM_ETC], "ld.config.arm64.txt", &override) == 0) return guest_readback_refuse(EEXIST);
    if (errno != ENOENT) return -1;
    return guest_readback_stat(fd[SYSTEM_BIN], "linker64", symlink);
}

static int app_sample_matches(const struct statx held[SLOTS], const struct guest_linkerconfig_app_process_sample *app) {
    const struct guest_linkerconfig_output_sample *out = &app->output;
    return out->root_mount_id == held[ROOT].stx_mnt_id && out->root_inode == held[ROOT].stx_ino
            && out->directory_mount_id == held[OUTPUT_DIR].stx_mnt_id && out->directory_inode == held[OUTPUT_DIR].stx_ino
            && out->directory_device_major == held[OUTPUT_DIR].stx_dev_major
            && out->directory_device_minor == held[OUTPUT_DIR].stx_dev_minor
            && out->base.inode == held[BASE].stx_ino && out->base.bytes == held[BASE].stx_size
            && out->companion.inode == held[COMPANION].stx_ino && out->companion.bytes == held[COMPANION].stx_size
            && app->app_process_inode == held[APP].stx_ino && app->linker_inode == held[LINKER].stx_ino
            && app->runtime_mount_id == held[RUNTIME].stx_mnt_id;
}

static int execution_flags_match(const int fd[SLOTS], uint32_t expected) {
    struct statvfs app, linker;
    if (fstatvfs(fd[APP], &app) < 0 || fstatvfs(fd[LINKER], &linker) < 0) return -1;
    const unsigned long required = ST_RDONLY | ST_NOSUID | ST_NODEV;
    uint32_t actual = 0;
    if ((app.f_flag & required) != required || (linker.f_flag & required) != required)
        return guest_readback_refuse(ESTALE);
    if (!(app.f_flag & ST_NOEXEC)) actual |= GUEST_LINKERCONFIG_EXEC_APP;
    if (!(linker.f_flag & ST_NOEXEC)) actual |= GUEST_LINKERCONFIG_EXEC_INTERPRETER;
    return actual == expected ? 0 : guest_readback_refuse(ESTALE);
}

int guest_linkerconfig_startup_readback(const struct guest_linkerconfig_startup_start *start,
        const struct guest_linkerconfig_startup_files *files, const struct guest_linkerconfig_app_process_files *app,
        const struct guest_linkerconfig_startup_scratch *scratch, struct guest_linkerconfig_startup_sample *out) {
    if (!start || !files || !app || !out) return guest_readback_refuse(EINVAL);
    if (validate_scratch(scratch) < 0) return -1;
    int fd[SLOTS];
    input_slots(files, fd);
    if (app->output.root_fd != fd[ROOT] || app->output.directory_fd != fd[OUTPUT_DIR] || app->output.base_fd != fd[BASE]
            || app->apex_fd != fd[APEX] || app->runtime_fd != fd[RUNTIME]
            || start->generation.root_fd != fd[ROOT] || start->generation.directory_fd != fd[OUTPUT_DIR]
            || start->generation.base_fd != fd[BASE]) return guest_readback_refuse(ESTALE);
    for (unsigned i = 0; i < OUTPUT_DIR; ++i) {
        if (fd[i] != start->input_fds[i]) return guest_readback_refuse(ESTALE);
    }
    fd[COMPANION] = app->output.companion_fd;
    fd[SYSTEM] = app->system_fd;
    fd[SYSTEM_BIN] = app->system_bin_fd;
    fd[SYSTEM_ETC] = app->system_etc_fd;
    fd[APP] = app->app_process_fd;
    fd[RUNTIME_BIN] = app->runtime_bin_fd;
    fd[LINKER] = app->linker_fd;

    struct statx before[SLOTS], after[SLOTS], link, after_link;
    if (distinct_slots(fd, SLOTS) < 0 || snapshot(fd, before, SLOTS) < 0 || entry_names(fd, &link) < 0) return -1;
    unsigned char digest[32];
    input_identity(before, digest);
    if (memcmp(digest, start->input_identity_sha256, sizeof(digest))) return guest_readback_refuse(ESTALE);

    struct guest_linkerconfig_startup_sample result;
    if (guest_linkerconfig_app_process_readback_system(&start->generation, &start->runtime, app,
                    scratch->work, scratch->work_capacity, &result.app) < 0
            || guest_apex_info_readback_runtime(&files->runtime, scratch->xml, scratch->xml_capacity, &result.runtime) < 0
            || guest_linkerconfig_property_readback(&files->properties, scratch->work, scratch->work_capacity,
                    &result.properties) < 0
            || execution_flags_match(fd, result.app.entry.executable_mounts) < 0
            || snapshot(fd, after, SLOTS) < 0 || entry_names(fd, &after_link) < 0 || stable(before, after, SLOTS) < 0)
        return -1;
    if (!guest_readback_same_node(&link, &after_link) || !app_sample_matches(before, &result.app.entry)
            || !input_samples_match(before, &result.properties, &result.runtime)
            || memcmp(result.runtime.xml.sha256, start->runtime.xml.sha256, sizeof(digest))
            || memcmp(result.properties.vndk_sha256, start->properties.vndk_sha256, sizeof(digest))
            || memcmp(result.properties.debug_sha256, start->properties.debug_sha256, sizeof(digest))
            || memcmp(result.properties.serial_sha256, start->properties.serial_sha256, sizeof(digest)))
        return guest_readback_refuse(ESTALE);
    *out = result;
    return 0;
}
