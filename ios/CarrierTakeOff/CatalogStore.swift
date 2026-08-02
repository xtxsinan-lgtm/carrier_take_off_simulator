import Foundation

/// 本地目录数据加载（仅 Bundle，无网络后端）
enum CatalogStore {
    /// 读取 Bundle 内置 data.json（含 py_sources，供本地 Pyodide）
    static func loadBundledCatalog() throws -> CatalogPayload {
        guard let url = Bundle.main.url(forResource: "data", withExtension: "json") else {
            throw NSError(
                domain: "CarrierTakeOff",
                code: 1,
                userInfo: [
                    NSLocalizedDescriptionKey:
                        "缺少 data.json，请在仓库根目录运行 python3 scripts/build_all.py",
                ]
            )
        }
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(CatalogPayload.self, from: data)
    }
}
