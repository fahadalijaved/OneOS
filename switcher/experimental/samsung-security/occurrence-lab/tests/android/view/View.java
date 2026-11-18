package android.view;

/** Minimal JVM fixture for the attachment readback. */
public final class View {
    private boolean attached = true;

    public boolean isAttachedToWindow() {
        return attached;
    }

    public void setAttached(boolean attached) {
        this.attached = attached;
    }
}
