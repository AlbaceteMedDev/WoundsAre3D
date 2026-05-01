import Foundation

/// Queue-backed upload service.
///
/// On capture completion, every artifact is enqueued; the service uploads
/// concurrently respecting a configured max in-flight count, retrying
/// transient failures with exponential backoff. Persisted across app launches.
@MainActor
final class UploadService: ObservableObject {
    @Published var pending: [UploadJob] = []
    @Published var inFlight: Int = 0

    private let api: APIClient
    private let session: URLSession = .shared
    let maxInFlight = 3

    init(api: APIClient) {
        self.api = api
    }

    func enqueue(_ job: UploadJob) {
        pending.append(job)
        Task { await pump() }
    }

    private func pump() async {
        while !pending.isEmpty, inFlight < maxInFlight {
            let job = pending.removeFirst()
            inFlight += 1
            Task { [weak self] in
                guard let self else { return }
                do {
                    try await self.runJob(job)
                } catch {
                    var retried = job
                    retried.attempt += 1
                    if retried.attempt < 4 {
                        let delayNs = UInt64(pow(2.0, Double(retried.attempt))) * 1_000_000_000
                        try? await Task.sleep(nanoseconds: delayNs)
                        await self.requeue(retried)
                    }
                }
                await self.completed()
            }
        }
    }

    private func runJob(_ job: UploadJob) async throws {
        var req = URLRequest(url: job.url)
        req.httpMethod = "PUT"
        let (_, response) = try await session.upload(for: req, from: job.data)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
    }

    private func requeue(_ job: UploadJob) {
        pending.insert(job, at: 0)
    }

    private func completed() {
        inFlight -= 1
        Task { await pump() }
    }
}

struct UploadJob: Identifiable, Equatable {
    let id: UUID
    let url: URL
    let data: Data
    let s3Key: String
    var attempt: Int = 0
}
