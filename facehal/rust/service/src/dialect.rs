use std::ffi::CString;
use std::os::raw::{c_char, c_int};

/// How a guest's Settings screen expects an enrollment to be reported.
///
/// The AOSP contract is one `onEnrollmentProgress(remaining)` countdown; the
/// vendor screens each interpret that callback differently, so the HAL has to
/// speak the dialect of the framework it registers under.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Dialect {
    Aosp,
    /// ColorOS, OxygenOS, realme UI, OriginOS (the BBK family). The ring advances
    /// on vendor help 19 and the progress countdown is shown beside it, so every
    /// accepted sample sends both.
    Oplus,
    /// HyperOS and MIUI. `MiuiNormalCameraMultiFaceInput` advances one ring stage
    /// per help 19 and treats the *first* `onEnrollmentProgress` as success, so
    /// progress is withheld until the fifth stage and sent once, at the end.
    Miui,
}

impl Dialect {
    pub fn detect() -> Self {
        if let Ok(value) = std::env::var("FACEHAL_DIALECT") {
            match value.trim().to_ascii_lowercase().as_str() {
                "aosp" => return Self::Aosp,
                "oplus" | "coloros" | "oxygenos" | "realme" | "originos" => return Self::Oplus,
                "miui" | "hyperos" => return Self::Miui,
                _ => {}
            }
        }
        const MIUI_MARKERS: [&str; 2] = ["ro.mi.os.version.name", "ro.miui.ui.version.name"];
        if MIUI_MARKERS.iter().any(|key| !property(key).is_empty()) {
            return Self::Miui;
        }
        const OPLUS_MARKERS: [&str; 3] = [
            "ro.build.version.oplusrom",
            "ro.build.version.opporom",
            "ro.vivo.os.version",
        ];
        if OPLUS_MARKERS.iter().any(|key| !property(key).is_empty()) {
            return Self::Oplus;
        }
        Self::Aosp
    }

    /// Vendor help 19 (visible to the framework as help id 1019) advances one
    /// ring stage on both vendor families.
    pub fn sends_vendor_steps(self) -> bool {
        matches!(self, Self::Oplus | Self::Miui)
    }

    /// The BBK screens draw a countdown from `onEnrollmentProgress` while the
    /// ring advances; MIUI reads the first progress callback as success.
    pub fn progress_per_stage(self) -> bool {
        matches!(self, Self::Oplus)
    }
}

fn property(key: &str) -> String {
    let Ok(key) = CString::new(key) else {
        return String::new();
    };
    let mut buffer = [0 as c_char; 128];
    let length = unsafe { __system_property_get(key.as_ptr(), buffer.as_mut_ptr()) };
    if length <= 0 {
        return String::new();
    }
    let bytes = buffer[..length as usize].iter().map(|byte| *byte as u8).collect();
    String::from_utf8(bytes).unwrap_or_default()
}

extern "C" {
    fn __system_property_get(name: *const c_char, value: *mut c_char) -> c_int;
}
