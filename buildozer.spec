[app]
title = Pokerherz
package.name = kartenwalzen
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,json,wav
source.exclude_dirs = hello,hello221,tools,.github,bin,.buildozer
version = 0.1
requirements = python3,kivy==2.2.1
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
