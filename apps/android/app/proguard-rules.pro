# LiteRT looks up its native bindings by name.
-keep class org.tensorflow.lite.** { *; }
-dontwarn org.tensorflow.lite.**

# LiteRT brings in WorkManager (via Play asset delivery), which starts itself
# and builds its Room database by reflection. Room 2.5's own rules predate R8
# full mode, so the generated database would be stripped and the app would
# crash on launch.
-keep class * extends androidx.room.RoomDatabase { <init>(); }
