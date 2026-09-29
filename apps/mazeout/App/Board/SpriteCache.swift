import UIKit
import ImageIO

// B1 (SPEC-architecture §5.9 step 3, D16). Board sprites (the art pipeline's @3x PNGs in the bundle's UI/ folder, drawn at
// the 32 pt design pitch) decoded with ImageIO at the pixel size they need at max zoom, off the main thread, into an LRU
// capped at `spriteCache.capMB` (48 MB). The main thread only reads decoded CGImages (never decodes on the tap path).

final class SpriteCache: @unchecked Sendable {        // all mutable state behind `lock`
    private let lock = NSLock()
    private var images: [String: CGImage] = [:]
    private var order: [String] = []                   // least recently used first
    private var bytes = 0
    private let capBytes: Int
    private let bundle: Bundle
    private let queue = DispatchQueue(label: "board.sprites", qos: .userInitiated, attributes: .concurrent)
    private var missing: Set<String> = []

    init(capMB: Double, bundle: Bundle) {
        capBytes = Int(capMB * 1_048_576)
        self.bundle = bundle
    }

    var footprintMB: Double { lock.lock(); defer { lock.unlock() }; return Double(bytes) / 1_048_576 }

    /// The decoded sprite, decoding synchronously if it was not preloaded (logged: a preload was missed).
    func image(_ id: String, maxPixel: Int? = nil) -> CGImage? {
        lock.lock()
        if let img = images[id] {
            if let i = order.firstIndex(of: id) { order.remove(at: i) }
            order.append(id)
            lock.unlock()
            return img
        }
        let known = missing.contains(id)
        lock.unlock()
        if known { return nil }
        let img = decode(id, maxPixel: maxPixel)
        if img != nil { Log.debug("board", "sprite \(id) decoded on demand (not preloaded)") }
        return img
    }

    /// Decodes these sprites in the background (idempotent).
    func preload(_ ids: [String], maxPixel: Int? = nil) {
        for id in Set(ids) {
            lock.lock()
            let have = images[id] != nil || missing.contains(id)
            lock.unlock()
            if have { continue }
            queue.async { [weak self] in _ = self?.decode(id, maxPixel: maxPixel) }
        }
    }

    /// Waits (without blocking the caller's thread) for every decode queued so far (warm-up).
    func drain() async {
        await withCheckedContinuation { (c: CheckedContinuation<Void, Never>) in
            queue.async(flags: .barrier) { c.resume() }
        }
    }

    private func url(_ id: String) -> URL? {
        bundle.url(forResource: id + "@3x", withExtension: "png", subdirectory: "UI")
            ?? bundle.url(forResource: id, withExtension: "png", subdirectory: "UI")
    }

    @discardableResult
    private func decode(_ id: String, maxPixel: Int?) -> CGImage? {
        guard let u = url(id), let src = CGImageSourceCreateWithURL(u as CFURL, nil) else {
            lock.lock(); let first = missing.insert(id).inserted; lock.unlock()
            if first { Log.error("board", "sprite UI/\(id)@3x.png missing from the bundle") }
            return nil
        }
        var opts: [CFString: Any] = [kCGImageSourceShouldCacheImmediately: true,
                                     kCGImageSourceCreateThumbnailFromImageAlways: true,
                                     kCGImageSourceCreateThumbnailWithTransform: true]
        if let m = maxPixel { opts[kCGImageSourceThumbnailMaxPixelSize] = m } else {
            let props = CGImageSourceCopyPropertiesAtIndex(src, 0, nil) as? [CFString: Any]
            let w = props?[kCGImagePropertyPixelWidth] as? Int ?? 1024
            let h = props?[kCGImagePropertyPixelHeight] as? Int ?? 1024
            opts[kCGImageSourceThumbnailMaxPixelSize] = max(w, h)
        }
        guard let img = CGImageSourceCreateThumbnailAtIndex(src, 0, opts as CFDictionary) else { return nil }
        let size = img.bytesPerRow * img.height
        lock.lock()
        if images[id] == nil {
            images[id] = img
            order.append(id)
            bytes += size
            while bytes > capBytes, order.count > 1 {
                let old = order.removeFirst()
                if let o = images.removeValue(forKey: old) { bytes -= o.bytesPerRow * o.height }
            }
        }
        lock.unlock()
        return img
    }
}
