package android.view;

import android.content.Context;
import java.util.ArrayList;
import java.util.List;

public abstract class ViewGroup extends View {
    private final List<View> children = new ArrayList<>();

    public ViewGroup(Context context) {
        super(context);
    }

    public void addView(View child) {
        children.add(child);
    }

    public int getChildCount() {
        return children.size();
    }

    public View getChildAt(int index) {
        return index >= 0 && index < children.size() ? children.get(index) : null;
    }
}
