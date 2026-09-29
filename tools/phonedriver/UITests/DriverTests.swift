import XCTest
import Network

/// A long-running "test" that turns this phone into a small HTTP-controlled device (port 8100),
/// in the spirit of Appium's WebDriverAgent. The Mac reaches it over the CoreDevice USB tunnel.
///
/// Coordinates are in POINTS of the portrait screen (iPhone 15: 393 x 852).
///
///   GET /status                         {"ok":true,"app":"<bundle>"}
///   GET /screenshot                     PNG of the whole screen (pixels, @3x)
///   GET /tap?x=&y=                      single tap
///   GET /doubletap?x=&y=
///   GET /press?x=&y=&d=0.8              long press for d seconds
///   GET /swipe?x1=&y1=&x2=&y2=&d=0.25   drag from 1 to 2 over ~d seconds
///   GET /taps?pts=x1,y1;x2,y2&gap=0.2   several taps in one call, gap seconds apart ({"taps": n, "ms": [per-tap start ms]})
///   GET /pinch?scale=2&v=1              pinch the front app at its centre (scale > 1 zooms in; v > 0 in, v < 0 out)
///   GET /drag?x1=&y1=&x2=&y2=&d=0.5&v=400&hold=0.3   press d s, drag at v pt/s, hold before lifting
///   GET /activate?bundle=com.x.y        bring an installed app to the front (launches if needed)
///   GET /launch?bundle=com.x.y          terminate + fresh launch
///   GET /terminate?bundle=com.x.y
///   GET /home                           home button
///   GET /source?bundle=com.x.y          accessibility tree (debugDescription) of an app
///   GET /stop                           end the runner
final class DriverTests: XCTestCase {
    func testServe() throws {
        continueAfterFailure = true
        let driver = Driver()
        try driver.start(port: 8100)
        while !driver.stopRequested {
            RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        }
    }
}

private struct Request {
    let path: String
    let query: [String: String]

    /// Parses one HTTP/1.1 request head; nil until the head is complete.
    init?(_ data: Data) {
        guard let text = String(data: data, encoding: .utf8), text.contains("\r\n\r\n"),
              let line = text.split(separator: "\r\n", maxSplits: 1).first else { return nil }
        let parts = line.split(separator: " ")
        guard parts.count >= 2 else { return nil }
        let comps = URLComponents(string: String(parts[1]))
        path = comps?.path ?? "/"
        var q: [String: String] = [:]
        for item in comps?.queryItems ?? [] { q[item.name] = item.value ?? "" }
        query = q
    }

    func number(_ key: String, _ fallback: Double? = nil) -> Double? {
        query[key].flatMap(Double.init) ?? fallback
    }
}

private final class Driver {
    var stopRequested = false
    private var listener: NWListener?
    private let queue = DispatchQueue(label: "phonedriver.net")
    private var currentBundle = "com.apple.springboard"
    /// Gestures are synthesised through SpringBoard's coordinate space: the touch lands on whatever is
    /// on screen, and XCTest does not wait for a constantly animating game to go idle first.
    private let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")

    func start(port: UInt16) throws {
        let params = NWParameters.tcp
        params.allowLocalEndpointReuse = true
        let l = try NWListener(using: params, on: NWEndpoint.Port(rawValue: port)!)
        l.newConnectionHandler = { [weak self] conn in self?.accept(conn) }
        l.start(queue: queue)
        listener = l
    }

    private func accept(_ conn: NWConnection) {
        conn.start(queue: queue)
        read(conn, buffer: Data())
    }

    private func read(_ conn: NWConnection, buffer: Data) {
        conn.receive(minimumIncompleteLength: 1, maximumLength: 64 * 1024) { [weak self] data, _, done, error in
            guard let self else { return }
            var buf = buffer
            if let data { buf.append(data) }
            if let req = Request(buf) {
                let response = DispatchQueue.main.sync { self.respond(to: req) }
                conn.send(content: response, completion: .contentProcessed { _ in conn.cancel() })
            } else if done || error != nil {
                conn.cancel()
            } else {
                self.read(conn, buffer: buf)
            }
        }
    }

    private func http(_ status: Int, _ body: Data, type: String) -> Data {
        var head = "HTTP/1.1 \(status) \(status == 200 ? "OK" : "Error")\r\n"
        head += "Content-Type: \(type)\r\nContent-Length: \(body.count)\r\nConnection: close\r\n\r\n"
        return Data(head.utf8) + body
    }

    private func json(_ object: [String: Any], status: Int = 200) -> Data {
        let body = (try? JSONSerialization.data(withJSONObject: object)) ?? Data("{}".utf8)
        return http(status, body, type: "application/json")
    }

    private func point(_ x: Double, _ y: Double) -> XCUICoordinate {
        springboard.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: x, dy: y))
    }

    private func respond(to r: Request) -> Data {
        switch r.path {
        case "/status":
            return json(["ok": true, "app": currentBundle])

        case "/screenshot":
            return http(200, XCUIScreen.main.screenshot().pngRepresentation, type: "image/png")

        case "/tap", "/doubletap", "/press":
            guard let x = r.number("x"), let y = r.number("y") else { return json(["error": "x,y required"], status: 400) }
            let c = point(x, y)
            switch r.path {
            case "/tap": c.tap()
            case "/doubletap": c.doubleTap()
            default: c.press(forDuration: r.number("d", 0.8)!)
            }
            return json(["ok": true])

        case "/swipe":
            guard let x1 = r.number("x1"), let y1 = r.number("y1"),
                  let x2 = r.number("x2"), let y2 = r.number("y2") else { return json(["error": "x1,y1,x2,y2 required"], status: 400) }
            let d = max(r.number("d", 0.25)!, 0.05)
            let distance = hypot(x2 - x1, y2 - y1)
            point(x1, y1).press(forDuration: 0.05,
                                thenDragTo: point(x2, y2),
                                withVelocity: XCUIGestureVelocity(rawValue: CGFloat(max(distance / d, 50))),
                                thenHoldForDuration: 0.05)
            return json(["ok": true])

        case "/taps":
            guard let pts = r.query["pts"], !pts.isEmpty else { return json(["error": "pts required"], status: 400) }
            let gap = max(r.number("gap", 0.2)!, 0)
            let t0 = Date()
            var starts: [Int] = []
            for pair in pts.split(separator: ";") {
                let xy = pair.split(separator: ",").compactMap { Double($0.trimmingCharacters(in: .whitespaces)) }
                guard xy.count == 2 else { continue }
                starts.append(Int(Date().timeIntervalSince(t0) * 1000))
                point(xy[0], xy[1]).tap()
                if gap > 0 { Thread.sleep(forTimeInterval: gap) }
            }
            return json(["ok": true, "taps": starts.count, "ms": starts])

        case "/pinch":
            let scale = r.number("scale", 2)!
            guard scale > 0 else { return json(["error": "scale must be > 0"], status: 400) }
            let v = r.number("v", scale >= 1 ? 1 : -1)!
            XCUIApplication(bundleIdentifier: currentBundle).pinch(withScale: CGFloat(scale), velocity: CGFloat(v))
            return json(["ok": true])

        case "/drag":
            guard let x1 = r.number("x1"), let y1 = r.number("y1"),
                  let x2 = r.number("x2"), let y2 = r.number("y2") else { return json(["error": "x1,y1,x2,y2 required"], status: 400) }
            point(x1, y1).press(forDuration: max(r.number("d", 0.5)!, 0.05),
                                thenDragTo: point(x2, y2),
                                withVelocity: XCUIGestureVelocity(rawValue: CGFloat(max(r.number("v", 400)!, 10))),
                                thenHoldForDuration: max(r.number("hold", 0.3)!, 0))
            return json(["ok": true])

        case "/activate", "/launch", "/terminate", "/source":
            guard let bundle = r.query["bundle"], !bundle.isEmpty else { return json(["error": "bundle required"], status: 400) }
            let app = XCUIApplication(bundleIdentifier: bundle)
            switch r.path {
            case "/activate": app.activate(); currentBundle = bundle
            case "/launch": app.terminate(); app.launch(); currentBundle = bundle
            case "/terminate": app.terminate()
            default: return http(200, Data(app.debugDescription.utf8), type: "text/plain; charset=utf-8")
            }
            return json(["ok": true, "state": app.state.rawValue])

        case "/home":
            XCUIDevice.shared.press(.home)
            currentBundle = "com.apple.springboard"
            return json(["ok": true])

        case "/stop":
            stopRequested = true
            return json(["ok": true])

        default:
            return json(["error": "unknown path \(r.path)"], status: 404)
        }
    }
}
