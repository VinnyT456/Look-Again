import Foundation

/// Serves canned responses to a URLSession so network code can be tested
/// without the network. Only used from the `.serialized` network suite.
final class StubURLProtocol: URLProtocol {
    enum Reply {
        case response(status: Int, body: Data, headers: [String: String] = [:])
        case failure(URLError.Code)
    }

    /// Reply for each request; set by the test before making requests.
    nonisolated(unsafe) static var reply: @Sendable (URLRequest) -> Reply = { _ in .failure(.notConnectedToInternet) }
    /// Every URL requested, in order.
    nonisolated(unsafe) static var requestedURLs: [URL] = []

    static func session() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        return URLSession(configuration: configuration)
    }

    static func reset() {
        reply = { _ in .failure(.notConnectedToInternet) }
        requestedURLs = []
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        if let url = request.url { Self.requestedURLs.append(url) }
        switch Self.reply(request) {
        case let .response(status, body, headers):
            let response = HTTPURLResponse(url: request.url ?? URL(fileURLWithPath: "/"), statusCode: status, httpVersion: nil, headerFields: headers)
            if let response {
                client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            }
            client?.urlProtocol(self, didLoad: body)
            client?.urlProtocolDidFinishLoading(self)
        case let .failure(code):
            client?.urlProtocol(self, didFailWithError: URLError(code))
        }
    }

    override func stopLoading() {}
}
