package android.app;

import android.content.Context;
import android.os.Bundle;
import android.view.View;

public class Activity extends Context {
    private View content;

    protected void onCreate(Bundle state) {}
    protected void onStart() {}
    protected void onStop() {}

    public void setContentView(View view) { content = view; }

    public final View contentViewForTest() { return content; }
    public final void createForTest() { onCreate(new Bundle()); }
    public final void startForTest() { onStart(); }
    public final void stopForTest() { onStop(); }
}
