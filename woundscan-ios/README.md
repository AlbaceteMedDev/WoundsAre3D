# WoundScan iOS

iPhone Pro app for clinical wound capture. Requires iPhone 12 Pro or
later (LiDAR sensor) running iOS 17+.

## Architecture

- SwiftUI + ARKit + AVFoundation
- Single-target app, no plugins, MVVM
- Networking via async/await + URLSession
- All capture is local-first; uploads queue when offline

## Project layout

```
WoundScan/
├── App/                Entry point, app state
├── Capture/            ARKit + AVFoundation capture pipeline
├── Models/             Domain models (Wound, Measurement, Probe, etc.)
├── Networking/         API client (matches engine /measurements API)
├── Services/           Auth, Upload, Local storage
├── UI/Screens/         Full-screen flows
└── UI/Components/      Reusable views
```

## Build

This is a SwiftUI app. The repo includes the source; you generate the
Xcode project locally with [xcodegen](https://github.com/yonaskolb/XcodeGen):

```bash
brew install xcodegen
cd woundscan-ios
xcodegen generate
open WoundScan.xcodeproj
```

The `project.yml` is the source of truth for project configuration.

## Required device capabilities

- LiDAR Scanner (`arkit.lidar` capability)
- TrueDepth front camera (optional, for IR multispectral)
- Camera permission (`NSCameraUsageDescription`)
- ARKit (`NSCameraUsageDescription` covers this on iOS 17)

## Running tests

```bash
xcodebuild test \
  -scheme WoundScan \
  -destination 'platform=iOS Simulator,name=iPhone 15 Pro'
```
