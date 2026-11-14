/*
 * Copyright (C) 2020 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

//! Generated Rust bindings to libbinder_ndk

use std::error::Error;
use std::fmt;

#[cfg(not(target_os = "trusty"))]
#[allow(bad_style)]
mod bindings {
    include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
}

// Trusty puts the full path to the auto-generated file in BINDGEN_INC_FILE
// and builds it with warnings-as-errors, so we need to use #[allow(bad_style)].
// We need to use cfg(target_os) instead of cfg(trusty) here because of
// the difference between the two build systems, which we cannot mock.
#[cfg(target_os = "trusty")]
#[allow(bad_style)]
mod bindings {
    include!(env!("BINDGEN_INC_FILE"));
}

pub use bindings::*;

impl Error for android_c_interface_StatusCode {}

impl fmt::Display for android_c_interface_StatusCode {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "StatusCode::{:?}", self)
    }
}
