package android.content;

import java.util.Objects;

public final class ComponentName {
    private final String packageName;
    private final String className;

    public ComponentName(Context context, Class<?> type) {
        this(context.getPackageName(), type.getName());
    }

    public ComponentName(String packageName, String className) {
        this.packageName = Objects.requireNonNull(packageName);
        this.className = Objects.requireNonNull(className);
    }

    public String getPackageName() { return packageName; }
    public String getClassName() { return className; }

    @Override public boolean equals(Object other) {
        if (!(other instanceof ComponentName)) return false;
        ComponentName name = (ComponentName) other;
        return packageName.equals(name.packageName) && className.equals(name.className);
    }

    @Override public int hashCode() { return Objects.hash(packageName, className); }
}
