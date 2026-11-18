package android.content;

public final class Intent {
    private ComponentName component;

    public Intent setComponent(ComponentName value) {
        component = value;
        return this;
    }

    public ComponentName getComponent() { return component; }
}
