fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

## iOS

### ios create_app

```sh
[bundle exec] fastlane ios create_app
```

App Store Connect'te app kaydını oluştur

### ios release

```sh
[bundle exec] fastlane ios release
```

Archive + upload + metadata + screenshots + submit for review

### ios upload_privacy

```sh
[bundle exec] fastlane ios upload_privacy
```

SADECE App Privacy (nutrition label) yukle — release'i upload_meta+upload_build'e boldugunde SART

### ios upload_build

```sh
[bundle exec] fastlane ios upload_build
```

Sadece binary yukle (revizyon) — metadata/screenshot'a dokunmaz

### ios upload_meta

```sh
[bundle exec] fastlane ios upload_meta
```

Sadece metadata + screenshot güncelle (binary yok)

### ios upload_meta_only

```sh
[bundle exec] fastlane ios upload_meta_only
```

SADECE metadata (screenshot YOK, binary YOK) — deliver bu makinede screenshot yukleyemiyor

### ios upload_shots

```sh
[bundle exec] fastlane ios upload_shots
```

SADECE screenshot yukle — metadata/keywords'a DOKUNMAZ

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
