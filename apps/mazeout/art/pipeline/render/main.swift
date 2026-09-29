// mfrender — offscreen RealityKit (RealityRenderer, macOS 15+) preview renderer for item USDZs.
//
//   mfrender job.json          render every scene in the job
//   mfrender --inspect a.usdz  print hierarchy, materials and triangle counts as RealityKit sees them
//
// job.json = {"renders": [scene, ...]}; scene keys (all optional except out/items):
//   out, width, height, background [r,g,b,a] sRGB, toneMapping, msaa
//   camera {type: "persp"|"ortho", position, target, up, fov, scale}
//   ibl {image: equirect png, exponent}
//   lights [{type:"directional"|"point"|"spot", direction|position, target, intensity, color, shadow, shadowScale, attenuation, innerAngle, outerAngle}]
//   floor {y, size, color [r,g,b] sRGB, texture png, roughness, unlit}
//   items [{usdz, matrix (16 floats, row-major, column vectors), position, euler [deg xyz], scale, groundingShadow,
//          holdout (OcclusionMaterial), unlit [r,g,b] (flat colour: mattes / ID passes)}]
import AppKit
import CoreGraphics
import Foundation
import ImageIO
import Metal
import RealityKit
import SceneKit
import UniformTypeIdentifiers

struct Job: Decodable { var renders: [Scene] }

struct Scene: Decodable {
    var out: String
    var width: Int?
    var height: Int?
    var background: [Double]?
    var toneMapping: Bool?
    var msaa: Bool?
    var camera: Cam?
    var ibl: IBL?
    var lights: [Light]?
    var floor: Floor?
    var items: [Item]
    var frames: Int?
}

struct Cam: Decodable {
    var type: String?
    var position: [Float]?
    var target: [Float]?
    var up: [Float]?
    var fov: Float?
    var scale: Float?
    var near: Float?
    var far: Float?
}

struct IBL: Decodable { var image: String; var exponent: Float? }

struct Light: Decodable {
    var type: String
    var direction: [Float]?
    var position: [Float]?
    var target: [Float]?
    var intensity: Float?
    var color: [Double]?
    var shadow: Bool?
    var shadowScale: Float?
    var shadowFixed: Float?   // ortho shadow volume half-size (board-sized = crisp shadows)
    var shadowBias: Float?
    var attenuation: Float?
    var innerAngle: Float?
    var outerAngle: Float?
}

struct Floor: Decodable {
    var iblExponent: Float?
    var y: Float?
    var size: Float?
    var color: [Double]?
    var texture: String?
    var roughness: Float?
    var unlit: Bool?
}

struct Item: Decodable {
    var usdz: String
    var matrix: [Float]?
    var position: [Float]?
    var euler: [Float]?
    var scale: Float?
    var groundingShadow: Bool?
    var holdout: Bool?      // every material -> OcclusionMaterial (draws nothing; NOTE: in RealityRenderer it does not
                            // hide other opaque items -- ui3d builds mattes with `unlit` instead)
    var unlit: [Double]?    // every material -> UnlitMaterial(rgb 0-1): flat ID / matte renders (rig layer holdouts)
}

func v3(_ a: [Float]?, _ d: SIMD3<Float>) -> SIMD3<Float> {
    guard let a, a.count == 3 else { return d }
    return SIMD3(a[0], a[1], a[2])
}

func cg(_ c: [Double]?, _ d: [Double]) -> CGColor {
    let c = c ?? d
    let cs = CGColorSpace(name: CGColorSpace.sRGB)!
    return CGColor(colorSpace: cs, components: [CGFloat(c[0]), CGFloat(c[1]), CGFloat(c[2]), CGFloat(c.count > 3 ? c[3] : 1)])!
}

func ns(_ c: CGColor) -> NSColor { NSColor(cgColor: c) ?? .white }

func loadCGImage(_ path: String) -> CGImage? {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil) else { return nil }
    return CGImageSourceCreateImageAtIndex(src, 0, nil)
}

func writePNG(texture: MTLTexture, to path: String) throws {
    // RealityKit renders in Display P3 (sRGB transfer curve). Tag the bytes as P3, then
    // convert to sRGB so every tool (and the contact sheets) read the colours correctly.
    let w = texture.width, h = texture.height
    var bytes = [UInt8](repeating: 0, count: w * h * 4)
    texture.getBytes(&bytes, bytesPerRow: w * 4, from: MTLRegionMake2D(0, 0, w, h), mipmapLevel: 0)
    for i in stride(from: 0, to: bytes.count, by: 4) { bytes.swapAt(i, i + 2) }  // BGRA -> RGBA
    let src = CGColorSpace(name: outputSpaceName)!
    let provider = CGDataProvider(data: Data(bytes) as CFData)!
    let p3img = CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: w * 4, space: src,
                        bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedLast.rawValue),
                        provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
    let srgb = CGColorSpace(name: CGColorSpace.sRGB)!
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: srgb,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.draw(p3img, in: CGRect(x: 0, y: 0, width: w, height: h))
    let img = ctx.makeImage()!
    let url = URL(fileURLWithPath: path)
    try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    guard let dst = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else {
        throw NSError(domain: "mfrender", code: 2, userInfo: [NSLocalizedDescriptionKey: "cannot write \(path)"])
    }
    CGImageDestinationAddImage(dst, img, nil)
    CGImageDestinationFinalize(dst)
}

func trace(_ m: String) { if ProcessInfo.processInfo.environment["MFRENDER_TRACE"] != nil { FileHandle.standardError.write("[t] \(m)\n".data(using: .utf8)!) } }

// MFRENDER_OUTPUT_SPACE=srgb to tag the raw output as sRGB instead (debug)
let outputSpaceName: CFString = ProcessInfo.processInfo.environment["MFRENDER_OUTPUT_SPACE"] == "srgb"
    ? CGColorSpace.sRGB : CGColorSpace.displayP3

final class DoneFlag: @unchecked Sendable {
    private let lock = NSLock()
    private var v = false
    func set() { lock.lock(); v = true; lock.unlock() }
    var isSet: Bool { lock.lock(); defer { lock.unlock() }; return v }
}

@MainActor
final class Renderer {
    let device = MTLCreateSystemDefaultDevice()!
    var cache: [String: Entity] = [:]
    var envCache: [String: EnvironmentResource] = [:]

    func entity(_ path: String) async throws -> Entity {
        if let e = cache[path] { return e.clone(recursive: true) }
        let e = try await Entity(contentsOf: URL(fileURLWithPath: path))
        cache[path] = e
        return e.clone(recursive: true)
    }

    func render(_ s: Scene) async throws {
        trace("scene \(s.out)")
        let r = try RealityRenderer()
        let W = s.width ?? 800, H = s.height ?? 800
        r.cameraSettings.colorBackground = .color(cg(s.background, [0.2, 0.25, 0.3, 1]))
        r.cameraSettings.isToneMappingEnabled = s.toneMapping ?? true
        r.cameraSettings.antialiasing = (s.msaa ?? true) ? .multisample4X : .none

        // IBL
        if let ibl = s.ibl {
            var env = envCache[ibl.image]
            if env == nil, let img = loadCGImage(ibl.image) {
                env = try await EnvironmentResource(equirectangular: img, withName: nil)
                envCache[ibl.image] = env
            }
            if let env { r.lighting.resource = env; r.lighting.intensityExponent = ibl.exponent ?? 0 }
        }

        trace("ibl done")
        let root = Entity()
        r.entities.append(root)

        // camera
        let c = s.camera ?? Cam()
        let camEntity: Entity
        if (c.type ?? "persp") == "ortho" {
            let e = Entity()
            var oc = OrthographicCameraComponent()
            oc.scale = c.scale ?? 4
            oc.near = c.near ?? 0.05
            oc.far = c.far ?? 100
            oc.scaleDirection = .vertical
            e.components.set(oc)
            camEntity = e
        } else {
            let pc = PerspectiveCamera()
            pc.camera.fieldOfViewInDegrees = c.fov ?? 30
            pc.camera.near = c.near ?? 0.05
            pc.camera.far = c.far ?? 100
            pc.camera.fieldOfViewOrientation = .vertical
            camEntity = pc
        }
        camEntity.look(at: v3(c.target, .zero), from: v3(c.position, [0, 10, 0.01]), upVector: v3(c.up, [0, 0, -1]), relativeTo: nil)
        root.addChild(camEntity)
        r.activeCamera = camEntity

        // lights
        for l in s.lights ?? [] {
            switch l.type {
            case "directional":
                let e = DirectionalLight()
                e.light.intensity = l.intensity ?? 3000
                e.light.color = ns(cg(l.color, [1, 1, 1]))
                let d = simd_normalize(v3(l.direction, [0.3, -1, 0.3]))
                if l.shadow ?? true {
                    var sh = DirectionalLightComponent.Shadow()
                    if let fs = l.shadowFixed {
                        sh.shadowProjection = .fixed(zNear: 0.1, zFar: 40, orthographicScale: fs)
                    } else {
                        sh.shadowProjection = .automatic(maximumDistance: l.shadowScale ?? 12)
                    }
                    sh.depthBias = l.shadowBias ?? 1.0
                    e.shadow = sh
                }
                // the fixed shadow camera sits at the light's position: put it 15 units up-light
                e.look(at: .zero, from: -d * 15, relativeTo: nil)
                root.addChild(e)
            case "point":
                let e = PointLight()
                e.light.intensity = l.intensity ?? 20000
                e.light.color = ns(cg(l.color, [1, 1, 1]))
                e.light.attenuationRadius = l.attenuation ?? 30
                e.position = v3(l.position, [0, 5, 0])
                root.addChild(e)
            case "spot":
                let e = SpotLight()
                e.light.intensity = l.intensity ?? 20000
                e.light.color = ns(cg(l.color, [1, 1, 1]))
                e.light.attenuationRadius = l.attenuation ?? 30
                e.light.innerAngleInDegrees = l.innerAngle ?? 30
                e.light.outerAngleInDegrees = l.outerAngle ?? 60
                if l.shadow ?? false { e.shadow = SpotLightComponent.Shadow() }
                e.look(at: v3(l.target, .zero), from: v3(l.position, [0, 8, 0]), relativeTo: nil)
                root.addChild(e)
            default: break
            }
        }

        // floor
        if let f = s.floor {
            let size = f.size ?? 30
            let mesh = MeshResource.generatePlane(width: size, depth: size)
            var mat: RealityKit.Material
            if f.unlit ?? false {
                var m = UnlitMaterial(color: ns(cg(f.color, [0.4, 0.47, 0.57])))
                if let t = f.texture, let img = loadCGImage(t) {
                    let tex = try await TextureResource(image: img, options: .init(semantic: .color))
                    m.color = .init(tint: .white, texture: .init(tex))
                }
                mat = m
            } else {
                var m = PhysicallyBasedMaterial()
                m.baseColor = .init(tint: ns(cg(f.color, [0.4, 0.47, 0.57])))
                if let t = f.texture, let img = loadCGImage(t) {
                    let tex = try await TextureResource(image: img, options: .init(semantic: .color))
                    m.baseColor = .init(tint: .white, texture: .init(tex))
                }
                m.roughness = .init(floatLiteral: f.roughness ?? 1)
                m.metallic = .init(floatLiteral: 0)
                m.specular = 0.2
                mat = m
            }
            let floor = ModelEntity(mesh: mesh, materials: [mat])
            floor.position.y = f.y ?? 0
            root.addChild(floor)
            // optional separate (brighter) ambient for the floor, so floor shadows can be lighter
            // than the items' self-shading (the capture does this)
            if let fe = f.iblExponent, let ibl = s.ibl, let env = envCache[ibl.image] {
                let le = Entity()
                le.components.set(ImageBasedLightComponent(source: .single(env), intensityExponent: fe))
                root.addChild(le)
                floor.components.set(ImageBasedLightReceiverComponent(imageBasedLight: le))
            }
        }

        trace("floor done")
        // items
        for it in s.items {
            let e = try await entity(it.usdz)
            if let m = it.matrix, m.count == 16 {
                // row-major input -> simd (column-major)
                let M = simd_float4x4(rows: [SIMD4(m[0], m[1], m[2], m[3]), SIMD4(m[4], m[5], m[6], m[7]),
                                             SIMD4(m[8], m[9], m[10], m[11]), SIMD4(m[12], m[13], m[14], m[15])])
                e.transform = Transform(matrix: M)
            } else {
                var t = Transform()
                if let eu = it.euler, eu.count == 3 {
                    let rx = simd_quatf(angle: eu[0] * .pi / 180, axis: [1, 0, 0])
                    let ry = simd_quatf(angle: eu[1] * .pi / 180, axis: [0, 1, 0])
                    let rz = simd_quatf(angle: eu[2] * .pi / 180, axis: [0, 0, 1])
                    t.rotation = ry * rx * rz
                }
                t.translation = v3(it.position, .zero)
                t.scale = SIMD3(repeating: it.scale ?? 1)
                e.transform = t
            }
            if it.groundingShadow ?? false {
                e.components.set(GroundingShadowComponent(castsShadow: true))
            }
            if it.holdout ?? false {   // a matte: hides what is behind it, renders transparent (rig layers, art/ui/tools/rig.py)
                func occlude(_ en: Entity) {
                    if var mc = en.components[ModelComponent.self] {
                        mc.materials = mc.materials.map { _ in OcclusionMaterial() }
                        en.components.set(mc)
                    }
                    for c in en.children { occlude(c) }
                }
                occlude(e)
            }
            if let u = it.unlit, u.count >= 3 {
                let col = NSColor(srgbRed: u[0], green: u[1], blue: u[2], alpha: 1)
                func flat(_ en: Entity) {
                    if var mc = en.components[ModelComponent.self] {
                        mc.materials = mc.materials.map { _ in UnlitMaterial(color: col) }
                        en.components.set(mc)
                    }
                    for c in en.children { flat(c) }
                }
                flat(e)
            }
            root.addChild(e)
        }

        trace("items done")
        // output
        let desc = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .bgra8Unorm_srgb, width: W, height: H, mipmapped: false)
        desc.usage = [.renderTarget, .shaderRead, .shaderWrite]
        desc.storageMode = .shared
        let tex = device.makeTexture(descriptor: desc)!
        let out = try RealityRenderer.CameraOutput(.singleProjection(colorTexture: tex))
        let frames = s.frames ?? 3
        for fi in 0..<frames {
            let done = DoneFlag()
            try r.updateAndRender(deltaTime: 1.0 / 60, cameraOutput: out, onComplete: { _ in done.set() })
            let t0 = Date()
            while !done.isSet {
                if Date().timeIntervalSince(t0) > 8 {
                    FileHandle.standardError.write("frame \(fi) of \(s.out) did not complete in 8 s\n".data(using: .utf8)!)
                    break
                }
                try await Task.sleep(nanoseconds: 2_000_000)
            }
        }
        trace("frames done")
        try writePNG(texture: tex, to: s.out)
        print("wrote \(s.out)")
    }
}

@MainActor
func inspect(_ path: String) async throws {
    let e = try await Entity(contentsOf: URL(fileURLWithPath: path))
    var tris = 0
    func walk(_ e: Entity, _ depth: Int) {
        let pad = String(repeating: "  ", count: depth)
        var line = "\(pad)\(e.name.isEmpty ? "<entity>" : e.name) [\(type(of: e))]"
        if let m = e.components[ModelComponent.self] {
            var t = 0
            for model in m.mesh.contents.models { for part in model.parts { t += (part.triangleIndices?.count ?? 0) / 3 } }
            tris += t
            line += " mesh tris=\(t)"
            for mat in m.materials {
                if let p = mat as? PhysicallyBasedMaterial {
                    let c = p.baseColor.tint.cgColor.components ?? []
                    line += String(format: "\n\(pad)   PBR spec=%.3f sheen=%@ base=(%.3f,%.3f,%.3f) tex=%@ rough=%.2f metal=%.2f clearcoat=%.2f ccRough=%.2f",
                                   p.specular.scale, p.sheen == nil ? "nil" : "set",
                                   c.count > 0 ? c[0] : -1, c.count > 1 ? c[1] : -1, c.count > 2 ? c[2] : -1,
                                   p.baseColor.texture == nil ? "no" : "yes", p.roughness.scale, p.metallic.scale,
                                   p.clearcoat.scale, p.clearcoatRoughness.scale)
                } else {
                    line += "\n\(pad)   material \(type(of: mat))"
                }
            }
        }
        print(line)
        for c in e.children { walk(c, depth + 1) }
    }
    walk(e, 0)
    let b = e.visualBounds(relativeTo: nil)
    print(String(format: "total tris=%d  bounds min=(%.3f,%.3f,%.3f) max=(%.3f,%.3f,%.3f)", tris,
                 b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z))
}

func inspectSceneKit(_ path: String) throws {
    let scene = try SCNScene(url: URL(fileURLWithPath: path), options: nil)
    var tris = 0, meshes = 0, textured = 0
    scene.rootNode.enumerateHierarchy { node, _ in
        guard let g = node.geometry else { return }
        meshes += 1
        for el in g.elements where el.primitiveType == .triangles { tris += el.primitiveCount }
        for m in g.materials where m.diffuse.contents != nil && !(m.diffuse.contents is NSColor) {
            textured += 1
        }
        let m = g.firstMaterial
        print("  \(node.name ?? "?"): tris=\(g.elements.map { $0.primitiveCount }.reduce(0, +)) lighting=\(m?.lightingModel.rawValue ?? "-") diffuse=\(type(of: m?.diffuse.contents as Any))")
    }
    print("SceneKit: \(meshes) meshes, \(tris) triangles, \(textured) textured materials")
}

let args = CommandLine.arguments
if args.count >= 3 && args[1] == "--inspect-scn" {
    for p in args[2...] {
        print("== \(p)")
        try inspectSceneKit(p)
    }
    exit(0)
}
if args.count >= 3 && args[1] == "--inspect" {
    for p in args[2...] {
        print("== \(p)")
        try await inspect(p)
    }
    exit(0)
}
guard args.count >= 2 else {
    print("usage: mfrender job.json | --inspect file.usdz ...")
    exit(1)
}
let data = try Data(contentsOf: URL(fileURLWithPath: args[1]))
let job = try JSONDecoder().decode(Job.self, from: data)
let renderer = Renderer()
// watchdog: RealityKit occasionally stalls (asset/IBL load); exit so the caller can retry
final class Progress: @unchecked Sendable { var t = Date(); let lock = NSLock()
    func touch() { lock.lock(); t = Date(); lock.unlock() }
    func age() -> TimeInterval { lock.lock(); defer { lock.unlock() }; return Date().timeIntervalSince(t) } }
let progress = Progress()
Thread.detachNewThread {
    while true {
        Thread.sleep(forTimeInterval: 1)
        if progress.age() > 25 {
            FileHandle.standardError.write("watchdog: no progress for 25 s, exiting\n".data(using: .utf8)!)
            exit(3)
        }
    }
}
for s in job.renders {
    progress.touch()
    do { try await renderer.render(s) } catch {
        FileHandle.standardError.write("failed \(s.out): \(error)\n".data(using: .utf8)!)
    }
}

exit(0)
