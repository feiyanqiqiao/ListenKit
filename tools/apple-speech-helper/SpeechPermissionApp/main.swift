import AppKit
import AVFoundation
import CoreMedia
import Foundation
import Speech

struct SegmentPayload: Codable {
    let start: Double
    let end: Double
    let text: String
}

struct ErrorPayload: Codable {
    let type: String
    let message: String
}

struct TranscriptionPayload: Codable {
    let error: ErrorPayload?
    let engine: String
    let locale: String
    let fullText: String
    let segments: [SegmentPayload]
    let timingComplete: Bool

    enum CodingKeys: String, CodingKey {
        case error
        case engine
        case locale
        case fullText = "full_text"
        case segments
        case timingComplete = "timing_complete"
    }
}

struct HelperArguments {
    let audioPath: String
    let localeIdentifier: String
    let outputPath: String?

    static func parse(_ arguments: ArraySlice<String>) throws -> HelperArguments {
        var audioPath: String?
        var localeIdentifier = "ja-JP"
        var outputPath: String?

        var iterator = arguments.makeIterator()
        while let argument = iterator.next() {
            switch argument {
            case "--audio-path":
                guard let value = iterator.next(), !value.isEmpty else {
                    throw HelperError.invalidArguments("Missing value for --audio-path.")
                }
                audioPath = value
            case "--locale":
                guard let value = iterator.next(), !value.isEmpty else {
                    throw HelperError.invalidArguments("Missing value for --locale.")
                }
                localeIdentifier = value
            case "--json":
                continue
            case "--output-path":
                guard let value = iterator.next(), !value.isEmpty else {
                    throw HelperError.invalidArguments("Missing value for --output-path.")
                }
                outputPath = value
            default:
                throw HelperError.invalidArguments("Unknown argument: \(argument)")
            }
        }

        guard let audioPath else {
            throw HelperError.invalidArguments("Missing required --audio-path argument.")
        }

        return HelperArguments(
            audioPath: audioPath,
            localeIdentifier: localeIdentifier,
            outputPath: outputPath
        )
    }
}

enum HelperError: LocalizedError {
    case unsupportedOS
    case invalidArguments(String)
    case authorizationDenied
    case authorizationRestricted
    case authorizationUnknown
    case speechUnavailable
    case localeNotSupported(String)
    case fileNotFound(String)
    case fileOpenFailed(String)
    case assetInstallationFailed(String)
    case assetReservationFailed(String)
    case analysisFailed(String)

    var errorType: String {
        switch self {
        case .unsupportedOS:
            return "unsupported_os"
        case .invalidArguments:
            return "invalid_arguments"
        case .authorizationDenied:
            return "authorization_denied"
        case .authorizationRestricted:
            return "authorization_restricted"
        case .authorizationUnknown:
            return "authorization_unknown"
        case .speechUnavailable:
            return "speech_unavailable"
        case .localeNotSupported:
            return "locale_not_supported"
        case .fileNotFound:
            return "file_not_found"
        case .fileOpenFailed:
            return "file_open_failed"
        case .assetInstallationFailed:
            return "asset_installation_failed"
        case .assetReservationFailed:
            return "asset_reservation_failed"
        case .analysisFailed:
            return "analysis_failed"
        }
    }

    var errorDescription: String? {
        switch self {
        case .unsupportedOS:
            return "SpeechAnalyzer requires macOS 26 or newer."
        case let .invalidArguments(message),
             let .localeNotSupported(message),
             let .fileNotFound(message),
             let .fileOpenFailed(message),
             let .assetInstallationFailed(message),
             let .assetReservationFailed(message),
             let .analysisFailed(message):
            return message
        case .authorizationDenied:
            return "Speech recognition authorization was denied."
        case .authorizationRestricted:
            return "Speech recognition authorization is restricted on this Mac."
        case .authorizationUnknown:
            return "Speech recognition authorization returned an unknown status."
        case .speechUnavailable:
            return "SpeechTranscriber is not currently available on this Mac."
        }
    }
}

@available(macOS 26.0, *)
final class SpeechFileTranscriber {
    private let timeTolerance: Double = 0.02

    func transcribe(audioPath: String, localeIdentifier: String) async throws -> TranscriptionPayload {
        let authorizationStatus = await requestSpeechAuthorization()
        switch authorizationStatus {
        case .authorized:
            break
        case .denied:
            throw HelperError.authorizationDenied
        case .restricted:
            throw HelperError.authorizationRestricted
        case .notDetermined:
            throw HelperError.authorizationUnknown
        @unknown default:
            throw HelperError.authorizationUnknown
        }

        guard SpeechTranscriber.isAvailable else {
            throw HelperError.speechUnavailable
        }

        let audioURL = URL(fileURLWithPath: audioPath)
        guard FileManager.default.fileExists(atPath: audioURL.path) else {
            throw HelperError.fileNotFound("Audio file not found: \(audioURL.path)")
        }

        let requestedLocale = Locale(identifier: localeIdentifier)
        let supportedLocale = await SpeechTranscriber.supportedLocale(equivalentTo: requestedLocale)
        guard let resolvedLocale = supportedLocale else {
            throw HelperError.localeNotSupported("SpeechTranscriber does not support locale \(localeIdentifier).")
        }

        let transcriber = SpeechTranscriber(
            locale: resolvedLocale,
            transcriptionOptions: [],
            reportingOptions: [],
            attributeOptions: [.audioTimeRange]
        )

        try await ensureAssets(for: transcriber, locale: resolvedLocale)
        defer {
            Task {
                _ = await AssetInventory.release(reservedLocale: resolvedLocale)
            }
        }

        let audioFile: AVAudioFile
        do {
            audioFile = try AVAudioFile(forReading: audioURL)
        } catch {
            throw HelperError.fileOpenFailed("Unable to open audio file: \(error.localizedDescription)")
        }

        let analyzer = SpeechAnalyzer(modules: [transcriber])
        let collectorTask = Task { try await self.collectResults(from: transcriber) }

        do {
            try await analyzer.prepareToAnalyze(in: audioFile.processingFormat)
            try await analyzer.start(inputAudioFile: audioFile, finishAfterFile: true)
            let collected = try await collectorTask.value
            return TranscriptionPayload(
                error: nil,
                engine: "apple",
                locale: Self.bcp47Identifier(for: resolvedLocale),
                fullText: collected.fullText,
                segments: collected.segments,
                timingComplete: collected.timingComplete
            )
        } catch {
            collectorTask.cancel()
            throw HelperError.analysisFailed("Speech analysis failed: \(error.localizedDescription)")
        }
    }

    private func requestSpeechAuthorization() async -> SFSpeechRecognizerAuthorizationStatus {
        let currentStatus = SFSpeechRecognizer.authorizationStatus()
        guard currentStatus == .notDetermined else { return currentStatus }
        await MainActor.run {
            NSApp.setActivationPolicy(.regular)
            NSApp.activate(ignoringOtherApps: true)
        }
        return await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }
    }

    private func ensureAssets(for transcriber: SpeechTranscriber, locale: Locale) async throws {
        let status = await AssetInventory.status(forModules: [transcriber])
        if status == .unsupported {
            throw HelperError.localeNotSupported("Speech assets are unsupported for locale \(Self.bcp47Identifier(for: locale)).")
        }

        if status < .installed {
            do {
                if let request = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
                    try await request.downloadAndInstall()
                }
            } catch {
                throw HelperError.assetInstallationFailed("Failed to install speech assets: \(error.localizedDescription)")
            }
        }

        do {
            _ = try await AssetInventory.reserve(locale: locale)
        } catch {
            throw HelperError.assetReservationFailed("Failed to reserve locale assets: \(error.localizedDescription)")
        }
    }

    private func collectResults(from transcriber: SpeechTranscriber) async throws -> (fullText: String, segments: [SegmentPayload], timingComplete: Bool) {
        var transcriptParts: [String] = []
        var segments: [SegmentPayload] = []
        var timingComplete = true
        var lastSegmentEnd: Double = 0

        for try await result in transcriber.results {
            guard result.isFinal else { continue }

            let resultText = String(result.text.characters).trimmingCharacters(in: .whitespacesAndNewlines)
            if !resultText.isEmpty {
                transcriptParts.append(resultText)
            }

            let extracted = extractSegments(from: result.text, lastSegmentEnd: &lastSegmentEnd)
            if extracted.missingTiming {
                timingComplete = false
            }
            if extracted.segments.isEmpty, !resultText.isEmpty {
                let fallbackSegment = fallbackSegment(from: result.range, text: resultText)
                if let fallbackSegment {
                    segments.append(fallbackSegment)
                    lastSegmentEnd = fallbackSegment.end
                } else {
                    timingComplete = false
                }
            } else {
                segments.append(contentsOf: extracted.segments)
            }
        }

        return (transcriptParts.joined(separator: "\n"), segments, timingComplete)
    }

    private func extractSegments(from text: AttributedString, lastSegmentEnd: inout Double) -> (segments: [SegmentPayload], missingTiming: Bool) {
        var segments: [SegmentPayload] = []
        var missingTiming = false
        for run in text.runs {
            let runText = String(text[run.range].characters).trimmingCharacters(in: .whitespacesAndNewlines)
            guard !runText.isEmpty else { continue }
            guard let timeRange = run.attributes[keyPath: \.audioTimeRange] else {
                missingTiming = true
                continue
            }

            let start = timeRange.start.seconds
            let end = timeRange.end.seconds
            guard end > start else {
                missingTiming = true
                continue
            }
            if end <= lastSegmentEnd + timeTolerance {
                continue
            }

            segments.append(SegmentPayload(start: start, end: end, text: runText))
            lastSegmentEnd = end
        }
        return (segments, missingTiming)
    }

    private func fallbackSegment(from range: CMTimeRange, text: String) -> SegmentPayload? {
        let start = range.start.seconds
        let end = range.end.seconds
        guard end > start else { return nil }
        return SegmentPayload(start: start, end: end, text: text)
    }

    private static func bcp47Identifier(for locale: Locale) -> String {
        locale.identifier.replacingOccurrences(of: "_", with: "-")
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        Task {
            let exitCode = await run()
            fflush(stdout)
            fflush(stderr)
            exit(exitCode)
        }
    }

    private func run() async -> Int32 {
        let outputPath = (try? HelperArguments.parse(CommandLine.arguments.dropFirst()))?.outputPath
        do {
            let arguments = try HelperArguments.parse(CommandLine.arguments.dropFirst())
            let payload: TranscriptionPayload

            if #available(macOS 26.0, *) {
                let transcriber = SpeechFileTranscriber()
                payload = try await transcriber.transcribe(
                    audioPath: arguments.audioPath,
                    localeIdentifier: arguments.localeIdentifier
                )
            } else {
                throw HelperError.unsupportedOS
            }

            try writeJSON(payload, outputPath: arguments.outputPath)
            return 0
        } catch let helperError as HelperError {
            let payload = TranscriptionPayload(
                error: ErrorPayload(type: helperError.errorType, message: helperError.localizedDescription),
                engine: "apple",
                locale: "unknown",
                fullText: "",
                segments: [],
                timingComplete: false
            )
            try? writeJSON(payload, outputPath: outputPath)
            return 1
        } catch {
            let payload = TranscriptionPayload(
                error: ErrorPayload(type: "unknown", message: error.localizedDescription),
                engine: "apple",
                locale: "unknown",
                fullText: "",
                segments: [],
                timingComplete: false
            )
            try? writeJSON(payload, outputPath: outputPath)
            return 1
        }
    }

    private func writeJSON(_ payload: TranscriptionPayload, outputPath: String?) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted]
        let data = try encoder.encode(payload)
        if let outputPath {
            try data.write(to: URL(fileURLWithPath: outputPath), options: .atomic)
            return
        }
        if let json = String(data: data, encoding: .utf8) {
            print(json)
        } else {
            throw HelperError.analysisFailed("Failed to encode JSON output.")
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
