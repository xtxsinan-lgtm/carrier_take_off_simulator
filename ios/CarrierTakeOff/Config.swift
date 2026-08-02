import Foundation

/// iOS 运行时配置（与 miniprogram/config.js 对应）
enum AppConfig {
    /**
     仿真 API 根地址，末尾不要斜杠。
     - 模拟器：http://127.0.0.1:8765
     - 真机：改为 Mac 局域网 IP，如 http://192.168.1.90:8765
       （API 需 python3 apps/miniprogram_api.py --host 0.0.0.0）
     */
    static var apiBaseUrl: String = "http://127.0.0.1:8765"

    /// 请求超时（秒），与小程序 120s 对齐
    static let simulateTimeout: TimeInterval = 120
}
