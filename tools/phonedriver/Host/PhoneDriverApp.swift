import SwiftUI

/// Host app for the UI-test runner that lets the Mac drive this phone (see UITests/DriverTests.swift).
@main
struct PhoneDriverApp: App {
    var body: some Scene {
        WindowGroup {
            VStack(spacing: 8) {
                Text("Phone Driver").font(.title2.bold())
                Text("Remote-control runner used from the Mac. Safe to delete.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
