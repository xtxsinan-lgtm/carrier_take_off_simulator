import Foundation
import SwiftUI

/// 饱和打击参数与结果状态
@MainActor
final class SaturationViewModel: ObservableObject {
    @Published var statusText = "加载预设…"
    @Published var statusTag = "STANDBY"
    @Published var running = false

    @Published var nm = "24"
    @Published var vm = "2.6"
    @Published var rcs = "0.5"
    @Published var traj = "high"
    @Published var awacsArea = "8"
    @Published var awacsType = "aesa"
    @Published var standoff = "150"
    @Published var shipArea = "12"
    @Published var shipType = "aesa"
    @Published var samRange = "40"
    @Published var discoveryKm = "120"
    @Published var ni = "16"
    @Published var vi = "3.8"
    @Published var interceptorDia = "0.35"
    @Published var seekerType = "active_aesa"
    @Published var pk = "0.7"
    @Published var tlock = "6"
    @Published var minr = "3"

    @Published var asmPresets: [SaturationPresetItem] = []
    @Published var aewPresets: [SaturationPresetItem] = []
    @Published var shipPresets: [SaturationPresetItem] = []
    @Published var samPresets: [SaturationPresetItem] = []
    @Published var selectedAsmId = ""
    @Published var selectedAewId = ""
    @Published var selectedShipId = ""
    @Published var selectedSamId = ""

    @Published var distNote = ""
    @Published var pkNote = ""
    @Published var hasResult = false
    @Published var result: SaturationResult?

    let trajOptions = [("high", "高空"), ("sea", "掠海")]
    let radarOptions = [
        ("mechanical", "机械扫描"), ("pesa", "PESA"),
        ("aesa", "AESA"), ("gan_aesa", "GaN AESA"),
    ]
    let seekerOptions = [
        ("active_aesa", "主动 AESA"),
        ("active_mech", "主动机械"),
        ("semi_active", "半主动"),
    ]

    init() {
        loadPresets()
    }

    /// 从 Bundle catalog 读取预设
    func loadPresets() {
        do {
            let catalog = try CatalogStore.loadBundledCatalog()
            let p = catalog.saturation_presets
            asmPresets = p?.asm ?? []
            aewPresets = p?.aew ?? []
            shipPresets = p?.ship ?? []
            samPresets = p?.sam ?? []
            statusText = "预设已加载（本地 Pyodide）"
            statusTag = "READY"
        } catch {
            statusText = error.localizedDescription
            statusTag = "ERROR"
        }
    }

    func applyAsmPreset() {
        guard let p = asmPresets.first(where: { $0.id == selectedAsmId }) else { return }
        if let v = p.vm { vm = String(v) }
        if let v = p.rcs { rcs = String(v) }
        if let v = p.traj { traj = v }
    }

    func applyAewPreset() {
        guard let p = aewPresets.first(where: { $0.id == selectedAewId }) else { return }
        if let v = p.area { awacsArea = String(v) }
        if let v = p.type { awacsType = v }
        if let v = p.standoff { standoff = String(v) }
    }

    func applyShipPreset() {
        guard let p = shipPresets.first(where: { $0.id == selectedShipId }) else { return }
        if let v = p.area { shipArea = String(v) }
        if let v = p.type { shipType = v }
    }

    func applySamPreset() {
        guard let p = samPresets.first(where: { $0.id == selectedSamId }) else { return }
        if let v = p.vi { vi = String(v) }
        if let v = p.dia { interceptorDia = String(v) }
        if let v = p.guidance { seekerType = v }
        if let v = p.range { samRange = String(v) }
    }

    private func estimateParams() -> [String: Any] {
        [
            "rcs": Double(rcs) ?? 0.5,
            "traj": traj,
            "awacs_area": Double(awacsArea) ?? 8,
            "awacs_type": awacsType,
            "standoff": Double(standoff) ?? 150,
            "ship_area": Double(shipArea) ?? 12,
            "ship_type": shipType,
            "sam_range": Double(samRange) ?? 40,
            "vm": Double(vm) ?? 2.6,
            "vi": Double(vi) ?? 3.8,
            "interceptor_dia": Double(interceptorDia) ?? 0.35,
            "seeker_type": seekerType,
        ]
    }

    /// 一次估算交战距离与单发拦截成功概率，填入按钮下方两字段。
    func estimateDistanceAndPk() async {
        statusTag = "COMPUTING"
        do {
            let params = estimateParams()
            let distR = try await LocalSimulatorEngine.shared.runSaturation(payload: [
                "action": "estimate_distance",
                "params": params,
            ])
            guard distR.success, let dist = distR.engage_dist else {
                throw NSError(domain: "Saturation", code: 1, userInfo: [
                    NSLocalizedDescriptionKey: distR.error ?? "交战距离估算失败",
                ])
            }
            let pkR = try await LocalSimulatorEngine.shared.runSaturation(payload: [
                "action": "estimate_pk",
                "params": params,
            ])
            guard pkR.success, let value = pkR.pk else {
                throw NSError(domain: "Saturation", code: 1, userInfo: [
                    NSLocalizedDescriptionKey: pkR.error ?? "拦截率估算失败",
                ])
            }
            discoveryKm = String(format: "%.1f", dist)
            distNote = "交战距离 \(String(format: "%.1f", dist)) km（\(distR.binding ?? "")）"
            pk = String(format: "%.2f", value)
            pkNote = "估算拦截率（单发）= \(String(format: "%.2f", value))"
            statusTag = "READY"
        } catch {
            distNote = error.localizedDescription
            pkNote = ""
            statusTag = "ERROR"
        }
    }

    func run() async {
        running = true
        statusTag = "COMPUTING"
        statusText = "计算中…"
        defer { running = false }
        do {
            let params: [String: Any] = [
                "nm": Int(Double(nm) ?? 24),
                "vm": Double(vm) ?? 2.6,
                "D": Double(discoveryKm) ?? 120,
                "ni": Int(Double(ni) ?? 16),
                "vi": Double(vi) ?? 3.8,
                "pk": Double(pk) ?? 0.7,
                "tlock": Double(tlock) ?? 6,
                "minr": Double(minr) ?? 3,
            ]
            let r = try await LocalSimulatorEngine.shared.runSaturation(payload: [
                "action": "simulate",
                "params": params,
            ])
            guard r.success else {
                throw NSError(domain: "Saturation", code: 1, userInfo: [
                    NSLocalizedDescriptionKey: r.error ?? "仿真失败",
                ])
            }
            result = r
            hasResult = true
            statusTag = "DONE"
            statusText = "MC N=\(r.final_trials ?? 0)"
        } catch {
            statusTag = "ERROR"
            statusText = error.localizedDescription
            hasResult = false
        }
    }
}
