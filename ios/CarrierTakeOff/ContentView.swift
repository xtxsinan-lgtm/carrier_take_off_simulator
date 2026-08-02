import SwiftUI

/// 主界面：与微信小程序 index 页相同的 6 段卡片布局
struct ContentView: View {
    @StateObject private var vm = SimulatorViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                header
                StatusBar(text: vm.statusText, kind: vm.statusKind)

                CardView(title: "1. 起飞模式") {
                    ModeSelector(items: vm.modeList, current: $vm.currentMode) { mode in
                        vm.applyMode(mode)
                    }
                    Text("滑跃 / 短距滑跃需滑跃甲板；短距 / 倾转短距需平直甲板。倾转短距仅策略 A/B；轨迹图仅滑跃与短距滑跃成功后显示。")
                        .font(.system(size: 12))
                        .foregroundStyle(AppTheme.muted)
                        .padding(.top, 4)
                    if vm.showStrategy {
                        Text(vm.strategyTitle)
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(AppTheme.accent)
                            .padding(.top, 8)
                        ModeSelector(items: vm.strategyList, current: $vm.currentStrategy)
                    }
                }

                CardView(title: "2. 航母") {
                    Text("选择航母")
                        .font(.system(size: 12))
                        .foregroundStyle(AppTheme.muted)
                    Picker("航母", selection: Binding(
                        get: { vm.selectedCarrierId ?? "" },
                        set: { vm.onCarrierPicked($0) }
                    )) {
                        ForEach(vm.carriers) { c in
                            Text(c.displayName).tag(c.id)
                        }
                    }
                    .pickerStyle(.menu)
                    .tint(AppTheme.text)
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(AppTheme.surface2)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(AppTheme.border, lineWidth: 1))
                    )
                    SpecListView(items: vm.carrierSpecs, emptyText: "请选择航母")

                    if vm.showSkiJump {
                        Text("滑跃参数（修改角度或弧长后，唇口高度自动重算）：")
                            .font(.system(size: 12))
                            .foregroundStyle(AppTheme.muted)
                            .padding(.top, 8)
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            FieldInput(label: "滑跃角 (°)", text: $vm.skiAngle) {
                                vm.updateSkiJumpFromInputs()
                            }
                            FieldInput(label: "滑跃弧长 (m)", text: $vm.skiArcLength) {
                                vm.updateSkiJumpFromInputs()
                            }
                            FieldInput(label: "唇口高度 (m)", text: $vm.skiHeight, readonly: true)
                        }
                        Text("滑跃水平投影：\(vm.skiHorizontal) m")
                            .font(.system(size: 12))
                            .foregroundStyle(AppTheme.muted)
                    }
                }

                CardView(title: "3. 战斗机") {
                    Text("选择战斗机")
                        .font(.system(size: 12))
                        .foregroundStyle(AppTheme.muted)
                    Picker("战斗机", selection: Binding(
                        get: { vm.selectedAircraftId ?? "" },
                        set: { vm.onAircraftPicked($0) }
                    )) {
                        ForEach(vm.aircraft) { a in
                            Text(a.name).tag(a.id)
                        }
                    }
                    .pickerStyle(.menu)
                    .tint(AppTheme.text)
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(AppTheme.surface2)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(AppTheme.border, lineWidth: 1))
                    )
                    SpecListView(items: vm.aircraftSpecs, emptyText: "请选择战斗机")
                }

                CardView(title: "4. 仿真条件") {
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                        FieldInput(label: "甲板风 (kt)", text: $vm.windKt) { vm.markWindEdited() }
                        FieldInput(label: "环境温度 (°C)", text: $vm.tempC)
                        FieldInput(label: "起飞重量 (kg)", text: $vm.massKg) { vm.markMassEdited() }
                    }
                    Button {
                        Task { await vm.runSimulation() }
                    } label: {
                        HStack {
                            if vm.running { ProgressView().tint(Color(hex: 0x0F172A)) }
                            Text(vm.running ? "计算中…" : "开始仿真")
                                .font(.system(size: 16, weight: .semibold))
                        }
                        .foregroundStyle(Color(hex: 0x0F172A))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(
                            LinearGradient(
                                colors: [AppTheme.accent, AppTheme.accentDim],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .opacity(vm.running ? 0.55 : 1)
                    }
                    .disabled(vm.running || !vm.engineReady)
                    .padding(.top, 4)

                    if !vm.engineReady {
                        Text("本地 Python 仿真引擎加载中（与 Web 版同一套物理模型，无需后端）。")
                            .font(.system(size: 12))
                            .foregroundStyle(AppTheme.muted)
                    }
                }

                CardView(title: "5. 仿真输出") {
                    ScrollView {
                        Text(vm.outputText)
                            .font(.system(size: 12, design: .monospaced))
                            .foregroundStyle(vm.outputEmpty ? AppTheme.muted : AppTheme.text)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .textSelection(.enabled)
                    }
                    .frame(maxHeight: 240)
                }

                if vm.showTrajectory {
                    CardView(title: "6. 起飞轨迹") {
                        TrajectoryChart(result: vm.chartResult)
                    }
                }

                Text("仿真在设备本地通过 Pyodide 运行 Python 物理模型 · 数据来自 aircraft_database.csv / carriers_database.csv")
                    .font(.system(size: 11))
                    .foregroundStyle(AppTheme.muted)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
            }
            .padding(.horizontal, 16)
            .padding(.top, 8)
            .padding(.bottom, 24)
        }
        .background(AppTheme.bg.ignoresSafeArea())
        .preferredColorScheme(.dark)
        .task { await vm.bootstrap() }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("航母舰载机起飞仿真")
                .font(.system(size: 22, weight: .semibold))
                .foregroundStyle(AppTheme.text)
            Text("支持滑跃、短距、短距滑跃、倾转短距 · 本机本地计算")
                .font(.system(size: 13))
                .foregroundStyle(AppTheme.muted)
        }
        .padding(.horizontal, 4)
        .padding(.bottom, 4)
    }
}

#Preview {
    ContentView()
}
