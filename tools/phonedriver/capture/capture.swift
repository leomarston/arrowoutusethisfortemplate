import AVFoundation
import CoreMediaIO
import CoreImage
import AppKit

// PhoneCapture — reads the USB-connected iPhone's screen the way QuickTime does (the phone shows up
// as a camera once screen-capture devices are allowed).
//   PhoneCapture shot   <out.png>            one full-resolution frame
//   PhoneCapture record <out.mov> <seconds>  screen video + the phone's audio
// Launch it with `open -W PhoneCapture.app --args ...` (so macOS attributes the camera permission to
// this app). Progress goes to <out>.log.

let args = Array(CommandLine.arguments.dropFirst())
let mode = args.first ?? "shot"
let outPath = args.count > 1 ? args[1] : NSTemporaryDirectory() + "phone.png"
let seconds = args.count > 2 ? Double(args[2]) ?? 10 : 10

let logURL = URL(fileURLWithPath: outPath + ".log")
FileManager.default.createFile(atPath: logURL.path, contents: nil)
let logHandle = try! FileHandle(forWritingTo: logURL)
func log(_ items: Any...) {
    let line = items.map { "\($0)" }.joined(separator: " ") + "\n"
    logHandle.write(line.data(using: .utf8)!)
}

var prop = CMIOObjectPropertyAddress(mSelector: CMIOObjectPropertySelector(kCMIOHardwarePropertyAllowScreenCaptureDevices),
                                     mScope: CMIOObjectPropertyScope(kCMIOObjectPropertyScopeGlobal),
                                     mElement: CMIOObjectPropertyElement(kCMIOObjectPropertyElementMain))
var allow: UInt32 = 1
CMIOObjectSetPropertyData(CMIOObjectID(kCMIOObjectSystemObject), &prop, 0, nil, UInt32(MemoryLayout<UInt32>.size), &allow)

func findPhone() -> AVCaptureDevice? {
    AVCaptureDevice.DiscoverySession(deviceTypes: [.external], mediaType: .muxed, position: .unspecified).devices.first
}
var found: AVCaptureDevice?
for _ in 0..<40 { found = findPhone(); if found != nil { break }; RunLoop.main.run(until: Date().addingTimeInterval(0.25)) }
guard let device = found else { log("NO_SCREEN_DEVICE"); exit(2) }
log("FOUND:", device.localizedName)

if AVCaptureDevice.authorizationStatus(for: .video) != .authorized {
    var answered = false
    AVCaptureDevice.requestAccess(for: .video) { ok in log("ACCESS:", ok); answered = true }
    for _ in 0..<480 where !answered { RunLoop.main.run(until: Date().addingTimeInterval(0.25)) }
    if AVCaptureDevice.authorizationStatus(for: .video) != .authorized { log("NOT_AUTHORIZED"); exit(5) }
}

let session = AVCaptureSession()
do { session.addInput(try AVCaptureDeviceInput(device: device)) } catch { log("INPUT_ERROR", error); exit(3) }

final class FrameGrab: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    var done = false
    func captureOutput(_ o: AVCaptureOutput, didOutput sb: CMSampleBuffer, from c: AVCaptureConnection) {
        guard !done, let px = CMSampleBufferGetImageBuffer(sb) else { return }
        done = true
        let rep = NSBitmapImageRep(ciImage: CIImage(cvPixelBuffer: px))
        try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: outPath))
        log("SAVED", CVPixelBufferGetWidth(px), "x", CVPixelBufferGetHeight(px))
        exit(0)
    }
}

final class Recorder: NSObject, AVCaptureFileOutputRecordingDelegate {
    func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo url: URL, from connections: [AVCaptureConnection], error: Error?) {
        if let error { log("RECORD_ERROR", error) } else { log("SAVED", url.path) }
        exit(error == nil ? 0 : 6)
    }
}

let grab = FrameGrab()
let recorder = Recorder()
switch mode {
case "record":
    let movie = AVCaptureMovieFileOutput()
    guard session.canAddOutput(movie) else { log("NO_MOVIE_OUTPUT"); exit(7) }
    session.addOutput(movie)
    session.startRunning()
    // Let the stream settle so the first frames aren't black.
    RunLoop.main.run(until: Date().addingTimeInterval(1.0))
    try? FileManager.default.removeItem(atPath: outPath)
    movie.startRecording(to: URL(fileURLWithPath: outPath), recordingDelegate: recorder)
    log("RECORDING", seconds, "s")
    RunLoop.main.run(until: Date().addingTimeInterval(seconds))
    movie.stopRecording()
    RunLoop.main.run(until: Date().addingTimeInterval(10))
    log("STOP_TIMEOUT"); exit(8)
default:
    let out = AVCaptureVideoDataOutput()
    out.setSampleBufferDelegate(grab, queue: DispatchQueue(label: "grab"))
    session.addOutput(out)
    session.startRunning()
    RunLoop.main.run(until: Date().addingTimeInterval(8))
    log("NO_FRAME"); exit(4)
}
