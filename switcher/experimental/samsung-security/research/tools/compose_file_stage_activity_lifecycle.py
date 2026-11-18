"""Keep each started tester screen attached to the one preparation attempt."""

import hashlib

from compose_file_stage_late_stop_ack import derive as derive_late_ack


ACTIVITY = 'PrepareActivity.java'
BASE_SHA = '1b49d37103f51f31caed5963972ccf97e60cbfb0e95920c38cc01702b5717c63'
EDITS = (
    (b'import java.lang.ref.WeakReference;\n',
     b'import java.util.Map;\n'
     b'import java.util.WeakHashMap;\n'),
    (b'        implements View.OnClickListener, DialogInterface.OnClickListener {\n',
     b'        implements View.OnClickListener, DialogInterface.OnClickListener, DialogInterface.OnDismissListener {\n'),
    (b'    private static WeakReference<PrepareActivity> visible = new WeakReference<>(null);\n',
     b'    // Accessed only on the main thread, like the shared operation.\n'
     b'    private static final Map<PrepareActivity, Object> started = new WeakHashMap<>();\n'),
    (b'        visible = new WeakReference<>(this);\n',
     b'        started.put(this, new Object());\n'),
    (b'        if (visible.get() == this) visible.clear();\n'
     b'        if (confirmation != null) {\n'
     b'            confirmation.dismiss();\n'
     b'            confirmation = null;\n'
     b'        }\n',
     b'        started.remove(this);\n'
     b'        AlertDialog pending = confirmation;\n'
     b'        confirmation = null;\n'
     b'        if (pending != null) pending.dismiss();\n'),
    (b'        if (visible.get() != this) return;\n',
     b'        if (Looper.myLooper() != Looper.getMainLooper()) return;\n'
     b'        Object startOwner = started.get(this);\n'
     b'        if (startOwner == null) return;\n'),
    (b'        if ((!start && !end) || (confirmation != null && confirmation.isShowing())) return;\n'
     b'        confirmingPrepare = start;\n'
     b'        confirmation = new AlertDialog.Builder(this)\n',
     b'        if ((!start && !end) || confirmation != null) return;\n'
     b'        AlertDialog dialog = new AlertDialog.Builder(this)\n'),
    (b'                .show();\n',
     b'                .create();\n'
     b'        if (started.get(this) != startOwner || confirmation != null) return;\n'
     b'        confirmingPrepare = start;\n'
     b'        confirmation = dialog;\n'
     b'        dialog.setOnDismissListener(this);\n'
     b'        try {\n'
     b'            dialog.show();\n'
     b'        } catch (RuntimeException | Error failure) {\n'
     b'            if (confirmation == dialog) confirmation = null;\n'
     b'            throw failure;\n'
     b'        }\n'
     b'        if (confirmation != dialog && dialog.isShowing()) dialog.dismiss();\n'),
    (b'        if (dialog != confirmation || which != DialogInterface.BUTTON_POSITIVE || visible.get() != this) return;\n',
     b'        if (Looper.myLooper() != Looper.getMainLooper() || dialog == null || dialog != confirmation\n'
     b'                || which != DialogInterface.BUTTON_POSITIVE || !started.containsKey(this)) return;\n'),
    (b'            current.bind();\n'
     b'        } else if (!confirmingPrepare && current != null) {\n'
     b'            current.stop();\n'
     b'        }\n'
     b'        render();\n',
     b'            current.bind();\n'
     b'            changed();\n'
     b'        } else if (!confirmingPrepare && current != null) {\n'
     b'            current.stop();\n'
     b'        }\n'),
    (b'    private void render() {\n',
     b'    @Override public void onDismiss(DialogInterface dialog) {\n'
     b'        if (Looper.myLooper() == Looper.getMainLooper() && dialog == confirmation) confirmation = null;\n'
     b'    }\n'
     b'\n'
     b'    private void render() {\n'),
    (b'        PrepareActivity screen = visible.get();\n'
     b'        if (screen != null) screen.render();\n',
     b'        for (PrepareActivity screen : started.keySet().toArray(new PrepareActivity[0])) {\n'
     b'            if (started.containsKey(screen)) screen.render();\n'
     b'        }\n'),
)


def derive():
    sources = derive_late_ack()
    original = sources[ACTIVITY]
    if hashlib.sha256(original).hexdigest() != BASE_SHA:
        raise ValueError('Expected exact late-acknowledgment Activity source')
    successor = original
    for before, after in EDITS:
        if successor.count(before) != 1 or after in successor:
            raise ValueError('Activity lifecycle source anchor differs')
        successor = successor.replace(before, after, 1)
    inverse = successor
    for before, after in reversed(EDITS):
        if inverse.count(after) != 1:
            raise ValueError('Activity lifecycle source inverse differs')
        inverse = inverse.replace(after, before, 1)
    if inverse != original:
        raise ValueError('Activity lifecycle source inverse failed')
    sources[ACTIVITY] = successor
    return sources
