package com.fahadali.oneos.ui

import android.app.admin.DevicePolicyManager
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.FragmentActivity
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.ImageIdentifier
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.ImageState
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.PhoneProfile
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.SpaceRule
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.model.SwitchGates
import com.fahadali.oneos.core.root.RootProbe
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.SetupPlan
import com.fahadali.oneos.session.LogJob
import com.fahadali.oneos.session.PrepareJob
import com.fahadali.oneos.session.Readiness
import com.fahadali.oneos.session.SessionPrefs
import com.fahadali.oneos.session.StageCheck

/**
 * Runs the one action of a plain message or of Home's button (the redesign,
 * step 3). Nothing here is less strict than before: an action only opens the
 * place where the user fixes it, or starts the same job, which checks
 * everything again before it writes (and root once more). Choosing a system
 * or a file opens Choose a system (SystemsActivity), and a setup that starts
 * opens Setting up (SetupProgressActivity); the fix Free up space opens
 * the Free up space screen (OldStagesActivity).
 */
internal object FixActions {
    fun run(a: FragmentActivity, action: FixAction, image: ImageRef?) {
        if (action == FixAction.OPEN_LOCK_SETTINGS || action == FixAction.OPEN_ROOT_APP || action == FixAction.OPEN_OLD_SWITCHER_INFO) {
            Readiness.recheckOnResume()
        }
        when (action) {
            FixAction.NONE, FixAction.ACKNOWLEDGE -> Unit
            FixAction.TRY_AGAIN -> Readiness.tick(a, force = true)
            FixAction.SWITCH -> SwitchConfirm.show(a)
            FixAction.SHOW_PROGRESS -> a.startActivity(Intent(a, SetupProgressActivity::class.java))
            FixAction.OPEN_LOCK_SETTINGS -> open(a, Intent(DevicePolicyManager.ACTION_SET_NEW_PASSWORD), Intent(Settings.ACTION_SECURITY_SETTINGS))
            FixAction.OPEN_ROOT_APP -> {
                val pm = a.packageManager
                val launch = RootProbe(a).managerPackages().firstNotNullOfOrNull { pm.getLaunchIntentForPackage(it) }
                if (launch != null) open(a, launch) else toast(a, a.getString(R.string.fix_open_root_app))
            }
            FixAction.OPEN_OLD_SWITCHER_INFO -> open(
                a,
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", SwitchGates.OLD_SWITCHER_PACKAGE, null)),
                Intent(Settings.ACTION_MANAGE_APPLICATIONS_SETTINGS),
            )
            FixAction.RESTORE -> LogJob.recover(a)
            FixAction.FREE_UP_SPACE -> a.startActivity(Intent(a, OldStagesActivity::class.java))
            FixAction.CHOOSE_SYSTEM, FixAction.CHOOSE_FILE, FixAction.SET_UP_AGAIN -> a.startActivity(Intent(a, SystemsActivity::class.java))
            FixAction.DOWNLOAD_AGAIN -> {
                val url = image?.downloadUrl
                if (url != null) open(a, Intent(Intent.ACTION_VIEW, Uri.parse(url)).addCategory(Intent.CATEGORY_BROWSABLE)) else a.startActivity(Intent(a, SystemsActivity::class.java))
            }
            FixAction.UPDATE, FixAction.REPAIR -> setUpAgain(a)
            FixAction.SET_UP -> setUp(a)
            FixAction.SEND_PHONE_DETAILS -> a.startActivity(Intent(a, RunTestsActivity::class.java))
            FixAction.SEND_REPORT -> {
                val zip = LogJob.latestZip(a)
                if (zip != null) {
                    a.startActivity(Intent(a, FindingsActivity::class.java).putExtra(FindingsActivity.EXTRA_ZIP, zip.path))
                } else {
                    a.startActivity(Intent(a, RunTestsActivity::class.java))
                }
            }
        }
    }

    /** The downloaded file the user chose, when its size says it is a system [profile] takes (not yet one found damaged). */
    fun pickedImage(ctx: Context, profile: PhoneProfile?): ImageRef? {
        val p = SessionPrefs.picked(ctx) ?: return null
        if (profile == null) return null
        val id = ImageIdentifier.identify(p.check, profile)
        if (id.state != ImageState.VERIFIED && id.state != ImageState.NOT_CHECKED) return null
        return id.image?.takeIf { profile.choice(it.id) != null }
    }

    /**
     * Set up the system of the chosen file (the protective confirm: it writes
     * 10 to 22 GB). What happens to what is set up now is decided by
     * [SetupPlan] and said here; PrepareJob decides it again from a fresh check.
     */
    private fun setUp(a: FragmentActivity) {
        val r = StageCheck.state.result ?: return Readiness.tick(a, force = true)
        val profile = Profiles.resolve(r.facts).profile ?: return
        val image = pickedImage(a, profile) ?: return a.startActivity(Intent(a, SystemsActivity::class.java))
        val set = profile.choice(image.id)?.packageSetId?.let { PackageSets.byId(it) }
        val plan = SetupPlan.decide(r.status, image, profile, BuildConfig.VERSION_CODE, hasDownload = true)
        val msg = buildString {
            append(a.getString(R.string.confirm_new_setup_msg, Units.bytes(SpaceRule.toStage(image, set))))
            when {
                plan == null -> Unit
                plan.keepsData -> append("\n\n").append(a.getString(R.string.confirm_setup_keep_data, image.name))
                plan.setsAsideData -> {
                    val old = plan.asideImageId?.let { Images.byId(it) }
                    append("\n\n").append(
                        if (old != null) a.getString(R.string.confirm_setup_aside, old.name) else a.getString(R.string.confirm_setup_aside_unknown),
                    )
                }
            }
        }
        AlertDialog.Builder(a)
            .setTitle(a.getString(R.string.confirm_setup_title, image.name))
            .setMessage(msg)
            .setPositiveButton(R.string.confirm_setup_go) { _, _ -> startSetup(a, PrepareJob.Plan.AUTO) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    /** Starts the setup job and, when it started, opens Setting up (SettingUp.dc.html) over the screen that asked. */
    private fun startSetup(a: FragmentActivity, plan: PrepareJob.Plan, updating: Boolean = false) {
        PrepareJob.start(a, plan)
        if (PrepareJob.state.busy && a !is SetupProgressActivity) {
            val fromChecks = a is EnvironmentActivity
            val intent = Intent(a, SetupProgressActivity::class.java)
                .putExtra(SetupProgressActivity.EXTRA_UPDATE, updating)
                .putExtra(SetupProgressActivity.EXTRA_REUSE_IMAGE, plan.source == SessionPrefs.Source.ON_PHONE)
                .putExtra(SetupProgressActivity.EXTRA_IMAGE, if (updating) StageCheck.state.result?.let(ImageMaintenance::identifiedImage)?.id else null)
                .putExtra(SetupProgressActivity.EXTRA_RETURN_TO_CHECKS, fromChecks)
            ArtworkTransitions.start(a, intent, if (fromChecks) a.findViewById(R.id.environment_artwork) else null)
        }
    }

    /**
     * Finish updating or repair the system that is set up, keeping its apps
     * and data: with the system already on the phone when root vouches for it
     * (no download), else with the picked download of that same system, else
     * the user picks it first. The confirm is the protective one (it writes).
     */
    private fun setUpAgain(a: FragmentActivity) {
        val r = StageCheck.state.result ?: return Readiness.tick(a, force = true)
        val profile = Profiles.resolve(r.facts).profile ?: return
        val st = r.status
        val image = st.staged(profile)?.first
            ?: st.marker?.takeIf { st.ours && it.profileId == profile.id }?.let { m -> Images.byId(m.imageId)?.takeIf { profile.choice(it.id) != null } }
            ?: ImageMaintenance.identifiedImage(r)?.takeIf { profile.choice(it.id) != null }
            ?: return a.startActivity(Intent(a, SystemsActivity::class.java))
        val system = image.name
        when {
            // One tap (the redesign: "Update now", about 2 minutes): the system stays, only OneOS's files are written.
            SetupPlan.reusesInstalled(st, image, profile, BuildConfig.VERSION_CODE) ->
                startSetup(a, PrepareJob.Plan(RootScript.BeginMode.KEEP, SessionPrefs.Source.ON_PHONE), updating = true)
            // The download is written into the stage (10 GB): confirmed first.
            SessionPrefs.picked(a)?.let { ImageIdentifier.identify(it.check, profile).image?.id == image.id } == true ->
                AlertDialog.Builder(a)
                    .setTitle(a.getString(R.string.confirm_setup_title, system))
                    .setMessage(a.getString(R.string.confirm_setup_file, system))
                    .setPositiveButton(R.string.confirm_setup_go) { _, _ ->
                        startSetup(a, PrepareJob.Plan(RootScript.BeginMode.KEEP, SessionPrefs.Source.GZ), updating = true)
                    }
                    .setNegativeButton(android.R.string.cancel, null)
                    .show()
            else -> {
                toast(a, a.getString(R.string.confirm_choose_download, system))
                a.startActivity(Intent(a, SystemsActivity::class.java))
            }
        }
    }

    private fun open(a: FragmentActivity, intent: Intent, fallback: Intent? = null) {
        try {
            a.startActivity(intent)
        } catch (_: ActivityNotFoundException) {
            try {
                if (fallback != null) a.startActivity(fallback) else toast(a, a.getString(R.string.fix_no_app))
            } catch (_: ActivityNotFoundException) {
                toast(a, a.getString(R.string.fix_no_app))
            }
        } catch (_: SecurityException) {
            toast(a, a.getString(R.string.fix_no_app))
        }
    }

    private fun toast(a: FragmentActivity, text: String) = Toast.makeText(a, text, Toast.LENGTH_LONG).show()
}
