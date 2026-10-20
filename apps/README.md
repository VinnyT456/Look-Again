# Mobile apps

iOS and Android clients for Look Again will live here.

Suggested layout:

```text
apps/
├── ios/       # Xcode project or Swift package
└── android/   # Gradle / Android Studio project
```

Model exports for on-device inference come from `../ml/checkpoints/`:

- iOS: `coreml/community_forensics_vit_rich_probe.mlpackage`
- Android: `tflite/community_forensics_vit_rich_probe.tflite` (LiteRT / TensorFlow Lite)
