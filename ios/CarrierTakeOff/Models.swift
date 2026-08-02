import Foundation

/// 目录数据总包（与 data.json /api/data 一致）
struct CatalogPayload: Codable {
    var version: Int?
    var modes: [String: String]
    var stovl_strategies: [String: String]?
    var tiltrotor_strategies: [String: String]?
    var carriers: [Carrier]
    var aircraft: [Aircraft]
}

/// 航母记录
struct Carrier: Codable, Identifiable, Hashable {
    var id: String
    var name: String
    var nation: String
    var max_speed_kt: Double?
    var total_deck_length_m: Double
    var ski_jump: Bool
    var ski_jump_angle_deg: Double?
    var ski_jump_height_m: Double?
    var f35b_capable: Bool
    var notes: String?
    var deck_length_source: String?

    var displayName: String { "\(name)（\(nation)）" }
}

/// 战斗机记录
struct Aircraft: Codable, Identifiable, Hashable {
    var id: String
    var name: String
    var type_label: String
    var mtow_kg: Double
    var empty_kg: Double
    var internal_fuel_kg: Double
    var max_payload_kg: Double
    var bvr_missile: String
    var missile_mass_kg: Double
    var wingspan_m: Double
    var wing_area_m2: Double
    var sweep_le_deg: Double
    var cd0: Double
    var t_max_sl_n: Double?
    var t_main_stovl_sl_n: Double?
    var t_liftfan_sl_n: Double?
    var t_rollposts_sl_n: Double?
    var shaft_power_sl_w: Double?
    var prop_diameter_m: Double?
    var nacelle_blockage_frac: Double?
    var notes: String?
    var wing_height_m: Double?
    var exhaust_d0_m: Double?
    var exhaust_height_m: Double?
    var exhaust_mdot_kg_s: Double?
}

/// 规格行
struct SpecItem: Identifiable, Hashable {
    var id: String { label }
    var label: String
    var value: String
}

/// 模式/策略按钮项
struct ModeItem: Identifiable, Hashable {
    var id: String
    var label: String
}

/// 仿真 API 返回（字段按需解码）
struct SimulationResult: Codable {
    var success: Bool
    var error: String?
    var output: String?
    var deck_launch_ok: Bool?
    var deck_margin_m: Double?
    var distance_m: Double?
    var trajectory: [TrajectoryPoint]?
    var deck_profile: DeckProfile?
}

struct TrajectoryPoint: Codable, Hashable {
    var x: Double
    var y: Double
    var phase: String?
}

struct DeckProfile: Codable, Hashable {
    var points: [[Double]]
    var total_deck_length_m: Double?
    var takeoff_distance_m: Double?
    var lip_height_m: Double?
}

/// 状态条样式
enum StatusKind {
    case idle
    case loading
    case ok
    case error
}
