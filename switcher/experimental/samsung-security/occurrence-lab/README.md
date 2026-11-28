# Presentation occurrence lab

This package-private helper correlates one keypad presentation with the exact
displayed view and selected-user record. Retirement invalidates that occurrence.
Overlapping transitions keep a replacement unavailable until their own
settlements finish.

Run from the OneOS repository root in a POSIX shell with JDK 17 or newer:

```sh
lab=switcher/experimental/samsung-security/occurrence-lab
pkg=com/appleexploit/oneos/security/transport
output="$(mktemp -d /tmp/oneos-occurrence.XXXXXX)"
javac -proc:none -classpath "$output" -d "$output" \
  "$lab/src/$pkg/GuestPinSourceOccurrence.java" \
  "$lab/tests/android/os/Looper.java" "$lab/tests/android/view/View.java" \
  "$lab/tests/$pkg/OccurrenceTest.java" &&
java -cp "$output" com.appleexploit.oneos.security.transport.OccurrenceTest
```

The tests use authored JVM fixtures for the display, selected record and Android
API declarations. The lab has no OneOS app integration. Its observations confer
no authentication authority and depend on the actual presentation and user
owners supplying and settling their transitions in a future integration.
