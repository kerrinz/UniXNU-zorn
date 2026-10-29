// SPDX-License-Identifier: BSD-2-Clause-Patent
// Explicit default-off personality for this owned touchscreen only. Registered
// before IOHIDDevice publishes its interface; no existing driver is terminated.
#pragma once
static const char zornTouchKernelPersonality[] = R"plist(
<dict>
 <key>CFBundleIdentifier</key><string>com.apple.iokit.IOHIDFamily</string>
 <key>IOClass</key><string>IOHIDEventDriver</string>
 <key>IOProviderClass</key><string>IOHIDInterface</string>
 <key>IOProbeScore</key><integer>100000</integer>
 <key>IOMatchDefer</key><false/>
 <key>HIDDefaultBehavior</key><string></string>
 <key>Product</key><string>Redmi K80 FT3683 Touchscreen</string>
 <key>Transport</key><string>SPI</string>
 <key>IOPropertyMatch</key><dict>
  <key>Product</key><string>Redmi K80 FT3683 Touchscreen</string>
  <key>Transport</key><string>SPI</string>
 </dict>
 <key>DeviceUsagePairs</key><array><dict>
  <key>DeviceUsagePage</key><integer>13</integer>
  <key>DeviceUsage</key><integer>4</integer>
 </dict></array>
</dict>
)plist";
