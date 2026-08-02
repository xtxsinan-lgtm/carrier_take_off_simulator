import Foundation

/// 与小程序 utils/api.js 对等的 HTTP 客户端
enum APIClient {
    enum APIError: LocalizedError {
        case missingBaseURL
        case invalidResponse
        case server(String)
        case httpStatus(Int)

        var errorDescription: String? {
            switch self {
            case .missingBaseURL:
                return "未配置 apiBaseUrl。请在 Config.swift 填写后端地址，并启动 python3 apps/simulator_api.py"
            case .invalidResponse:
                return "服务器返回无效数据"
            case .server(let msg):
                return msg
            case .httpStatus(let code):
                return "仿真请求失败 (\(code))"
            }
        }
    }

    /// 读取 Bundle 内置 data.json
    static func loadBundledCatalog() throws -> CatalogPayload {
        guard let url = Bundle.main.url(forResource: "data", withExtension: "json") else {
            throw NSError(
                domain: "CarrierTakeOff",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "缺少 data.json，请在仓库根目录运行 python3 scripts/build_all.py"]
            )
        }
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(CatalogPayload.self, from: data)
    }

    /**
     加载仿真数据：优先本地 Bundle；若配置了 apiBaseUrl 则尝试远端覆盖（失败保留本地）。
     */
    static func loadSimulatorData() async -> CatalogPayload {
        let local = (try? loadBundledCatalog()) ?? CatalogPayload(
            version: nil,
            modes: [:],
            stovl_strategies: nil,
            tiltrotor_strategies: nil,
            carriers: [],
            aircraft: []
        )
        let base = AppConfig.apiBaseUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !base.isEmpty, let url = URL(string: base + "/api/data") else {
            return local
        }
        do {
            var req = URLRequest(url: url)
            req.timeoutInterval = 15
            let (data, response) = try await URLSession.shared.data(for: req)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                return local
            }
            let remote = try JSONDecoder().decode(CatalogPayload.self, from: data)
            if remote.carriers.isEmpty || remote.aircraft.isEmpty {
                return local
            }
            return remote
        } catch {
            return local
        }
    }

    /// 调用后端 Python 仿真 API
    static func runSimulation(payload: [String: Any]) async throws -> SimulationResult {
        let base = AppConfig.apiBaseUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !base.isEmpty, let url = URL(string: base + "/api/simulate") else {
            throw APIError.missingBaseURL
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = AppConfig.simulateTimeout
        req.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        if !(200..<300).contains(http.statusCode) {
            if let obj = try? JSONDecoder().decode(SimulationResult.self, from: data),
               let err = obj.error, !err.isEmpty {
                throw APIError.server(err)
            }
            throw APIError.httpStatus(http.statusCode)
        }
        return try JSONDecoder().decode(SimulationResult.self, from: data)
    }
}

extension Encodable {
    /// 将 Codable 转为 JSON 字典，供仿真 payload 拼装
    func asJSONDictionary() throws -> [String: Any] {
        let data = try JSONEncoder().encode(self)
        let obj = try JSONSerialization.jsonObject(with: data)
        guard let dict = obj as? [String: Any] else {
            throw APIClient.APIError.invalidResponse
        }
        return dict
    }
}
