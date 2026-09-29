#!/bin/zsh
# Builds PhoneCapture.app (screen shot / screen+audio recording of the USB iPhone) and the `frames`
# extractor. Rebuilding PhoneCapture changes its ad-hoc signature, so macOS asks for camera access
# again — only rebuild when someone can click Allow.
cd "${0:A:h}" || exit 1
mkdir -p build
APP=build/PhoneCapture.app
if [ "$1" != "frames-only" ]; then
  rm -rf $APP && mkdir -p $APP/Contents/MacOS
  swiftc -O capture.swift -o $APP/Contents/MacOS/PhoneCapture && cp Info.plist $APP/Contents/Info.plist && codesign --force --sign - $APP
fi
swiftc -O frames.swift -o build/frames
