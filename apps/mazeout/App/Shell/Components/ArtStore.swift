import SwiftUI
import UIKit
import ImageIO

// SHELL S1 (SPEC-architecture §6.11 "UIArt", §5.9, R16). Loads the bundle's rasters (`UIArt` cases, rig layers, the loading
// characters) with ImageIO, decoded NOW (kCGImageSourceShouldCacheImmediately) and optionally downsampled to the pixel size a
// screen needs, then cached. Boot and screen warm-ups call `preload` behind the Loading screen so no first frame pays a decode.
// A missing file is remembered (never retried per frame). `ArtImage` shows the image, or — in DEBUG builds only — the hatched
// `DebugPlaceholder` of the same frame; a Release build draws nothing for a missing file (never ship stand-in content;
// UIArtBundleTests, V1, require 0 missing).

enum ArtStore {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var cache: [String: UIImage] = [:]
    nonisolated(unsafe) private static var missingPaths: Set<String> = []

    /// `path` inside the bundle ("UI/iconCoin@3x.png", "Art/char_sci_home_rig/torso@3x.png"); `maxPixel` downsamples the
    /// longest side (nil = full size). Scale 3 (the @3x files).
    static func image(path: String, maxPixel: Int? = nil, bundle: Bundle = .main) -> UIImage? {
        let key = "\(path)|\(maxPixel ?? 0)"
        lock.lock()
        if let hit = cache[key] { lock.unlock(); return hit }
        if missingPaths.contains(path) { lock.unlock(); return nil }
        lock.unlock()
        guard let root = bundle.resourceURL else { return nil }
        let url = root.appendingPathComponent(path)
        guard let src = CGImageSourceCreateWithURL(url as CFURL, [kCGImageSourceShouldCache: false] as CFDictionary) else {
            lock.lock(); missingPaths.insert(path); lock.unlock()
            return nil
        }
        let cg: CGImage?
        if let maxPixel {
            cg = CGImageSourceCreateThumbnailAtIndex(src, 0, [
                kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceThumbnailMaxPixelSize: maxPixel,
                kCGImageSourceCreateThumbnailWithTransform: true,
                kCGImageSourceShouldCacheImmediately: true,
            ] as CFDictionary)
        } else {
            cg = CGImageSourceCreateImageAtIndex(src, 0, [kCGImageSourceShouldCacheImmediately: true] as CFDictionary)
        }
        guard let cg else {
            lock.lock(); missingPaths.insert(path); lock.unlock()
            return nil
        }
        // Keep the point size of the @3x original when downsampled.
        let fullWidth = (CGImageSourceCopyPropertiesAtIndex(src, 0, nil) as? [CFString: Any])?[kCGImagePropertyPixelWidth] as? Int ?? cg.width
        let scale = 3 * CGFloat(cg.width) / CGFloat(max(fullWidth, 1))
        let img = UIImage(cgImage: cg, scale: scale, orientation: .up)
        lock.lock(); cache[key] = img; lock.unlock()
        return img
    }

    static func image(_ art: UIArt, maxPixel: Int? = nil) -> UIImage? { image(path: art.path, maxPixel: maxPixel) }

    static func exists(_ art: UIArt, bundle: Bundle = .main) -> Bool {
        guard let root = bundle.resourceURL else { return false }
        return FileManager.default.fileExists(atPath: root.appendingPathComponent(art.path).path)
    }

    /// Decodes the given ids now; returns how many exist.
    @discardableResult
    static func preload(_ arts: [UIArt], maxPixel: Int? = nil) -> Int { arts.filter { image($0, maxPixel: maxPixel) != nil }.count }

    /// Every shipped id missing from the bundle (UIArtBundleTests, the ShellLab summary).
    static func missing(_ arts: [UIArt] = UIArt.allCases, bundle: Bundle = .main) -> [UIArt] { arts.filter { !exists($0, bundle: bundle) } }

    /// Drops decoded bitmaps (memory warning; event art on leaving its screen, R16).
    static func purge(prefix: String? = nil) {
        lock.lock(); defer { lock.unlock() }
        if let prefix { cache = cache.filter { !$0.key.hasPrefix(prefix) } } else { cache.removeAll() }
    }

    /// FIX-2 A (V3-09): drops the decoded bitmaps of these exact bundle paths (every downsampled size); returns their bytes.
    /// Only for art no mounted view shows any more (a view keeps its own reference: purging art on screen frees nothing and a
    /// later read would decode it twice).
    @discardableResult
    static func purge(paths: [String]) -> Int {
        let set = Set(paths)
        lock.lock(); defer { lock.unlock() }
        var bytes = 0
        for (k, img) in cache {
            guard let bar = k.lastIndex(of: "|"), set.contains(String(k[..<bar])) else { continue }
            if let cg = img.cgImage { bytes += cg.bytesPerRow * cg.height }
            cache.removeValue(forKey: k)
        }
        return bytes
    }

    /// Whether a path is decoded and cached (any size; tests).
    static func isCached(path: String) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return cache.keys.contains { $0.hasPrefix(path + "|") }
    }

    /// The biggest decoded entries (path|maxPixel, bytes), largest first (the memory log).
    static func largest(_ n: Int) -> [(String, Int)] {
        lock.lock(); defer { lock.unlock() }
        return cache.map { ($0.key, $0.value.cgImage.map { $0.bytesPerRow * $0.height } ?? 0) }
            .sorted { $0.1 > $1.1 }.prefix(n).map { $0 }
    }

    /// The decoded bytes held (tests, the memory log).
    static var bytes: Int {
        lock.lock(); defer { lock.unlock() }
        return cache.values.reduce(0) { $0 + ($1.cgImage.map { $0.bytesPerRow * $0.height } ?? 0) }
    }
}

/// A raster at its frame (aspect fit), with the DEBUG-only placeholder when the file is missing.
struct ArtImage: View {
    let art: UIArt
    var maxPixel: Int? = nil
    var contentMode: ContentMode = .fit

    var body: some View {
        if let img = ArtStore.image(art, maxPixel: maxPixel) {
            Image(uiImage: img).resizable().interpolation(.high).aspectRatio(contentMode: contentMode)
                .accessibilityHidden(true)
        } else {
            #if DEBUG
            DebugPlaceholder(name: art.rawValue)
            #else
            Color.clear.accessibilityHidden(true)
            #endif
        }
    }
}

/// A raster by bundle path (rig layers, loading characters).
struct PathImage: View {
    let path: String
    var maxPixel: Int? = nil

    var body: some View {
        if let img = ArtStore.image(path: path, maxPixel: maxPixel) {
            Image(uiImage: img).resizable().interpolation(.high).accessibilityHidden(true)
        } else {
            #if DEBUG
            DebugPlaceholder(name: (path as NSString).lastPathComponent)
            #else
            Color.clear.accessibilityHidden(true)
            #endif
        }
    }
}
