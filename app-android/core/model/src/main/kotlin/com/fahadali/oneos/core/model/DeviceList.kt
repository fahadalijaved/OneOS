package com.fahadali.oneos.core.model

/**
 * docs/devices.json (0.4.59, owner: people in the group keep asking whether their phone works):
 * every phone the app knows, with its model number, codename and chip, and each system it can
 * switch to and whether a session has run there (the "tested" of [ImageChoice]). From
 * [Profiles.BUILT_IN] itself, so it is never out of step with the app; DeviceListTest compares
 * the checked-in file. reports/devices.py adds the testers' reports and writes docs/devices.md
 * and the group bot's filters.
 */
object DeviceList {
    fun json(images: List<ImageRef> = Images.ALL, profiles: List<PhoneProfile> = Profiles.BUILT_IN): String =
        Json.write(
            mapOf(
                "generatedFrom" to "Profiles.BUILT_IN (DeviceList.kt)",
                "phones" to profiles.map { p ->
                    mapOf(
                        "id" to p.id,
                        "label" to p.label,
                        "model" to p.modelPrefix,
                        "codename" to p.codename,
                        "chip" to p.socModel,
                        "form" to p.form.name.lowercase(),
                        "enabled" to p.enabled,
                        "disabledReason" to p.disabledReason,
                        "systems" to p.choices.mapNotNull { c ->
                            val image = Images.byId(c.imageId, images) ?: return@mapNotNull null
                            mapOf("image" to image.id, "label" to image.label, "set" to c.packageSetId, "tested" to c.tested)
                        },
                    )
                },
            ),
        )
}
