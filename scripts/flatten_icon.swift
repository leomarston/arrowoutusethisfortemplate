import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let inP = CommandLine.arguments[1], outP = CommandLine.arguments[2]
guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: inP) as CFURL, nil),
      let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { exit(1) }
let n = 1024
let cs = CGColorSpaceCreateDeviceRGB()
guard let ctx = CGContext(data: nil, width: n, height: n, bitsPerComponent: 8, bytesPerRow: 0,
                          space: cs, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { exit(1) }
ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: n, height: n))
ctx.interpolationQuality = .high
ctx.draw(img, in: CGRect(x: 0, y: 0, width: n, height: n))
guard let out = ctx.makeImage(),
      let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: outP) as CFURL, UTType.png.identifier as CFString, 1, nil) else { exit(1) }
CGImageDestinationAddImage(dest, out, nil)
CGImageDestinationFinalize(dest)
