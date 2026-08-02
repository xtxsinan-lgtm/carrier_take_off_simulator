import Foundation

/// iOS 运行时配置（本地 Pyodide，无后端地址）
enum AppConfig {
    /// 与 Web / engine.js 对齐的 Pyodide 版本说明（实际版本写在 engine.js）
    static let pyodideVersionNote = "0.26.4"
}
