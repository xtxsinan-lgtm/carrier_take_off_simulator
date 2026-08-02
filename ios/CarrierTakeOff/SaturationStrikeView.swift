import SwiftUI

/// 饱和打击仿真界面（战术终端风格）
struct SaturationStrikeView: View {
    @StateObject private var vm = SaturationViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                header
                Text(vm.statusText)
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(SaturationTheme.green)

                panel(title: "参数输入") {
                    sectionLabel("▸ 打击方", color: SaturationTheme.red)
                    presetPicker("反舰导弹预设", selection: $vm.selectedAsmId, items: vm.asmPresets) {
                        vm.applyAsmPreset()
                    }
                    field("来袭数量 (枚)", text: $vm.nm)
                    field("速度 (Ma)", text: $vm.vm)
                    field("RCS (m²)", text: $vm.rcs)
                    pickerRow("弹道", selection: $vm.traj, options: vm.trajOptions)
                    field("抗干扰 1–5", text: $vm.ecm)

                    sectionLabel("▸ 预警机", color: SaturationTheme.cyan)
                    presetPicker("预警机预设", selection: $vm.selectedAewId, items: vm.aewPresets) {
                        vm.applyAewPreset()
                    }
                    field("天线面积 (m²)", text: $vm.awacsArea)
                    pickerRow("雷达体制", selection: $vm.awacsType, options: vm.radarOptions)
                    field("前出距离 (km)", text: $vm.standoff)

                    sectionLabel("▸ 舰载雷达 & 拦截弹", color: SaturationTheme.green)
                    presetPicker("驱逐舰雷达", selection: $vm.selectedShipId, items: vm.shipPresets) {
                        vm.applyShipPreset()
                    }
                    presetPicker("防空导弹", selection: $vm.selectedSamId, items: vm.samPresets) {
                        vm.applySamPreset()
                    }
                    field("舰载天线 (m²)", text: $vm.shipArea)
                    pickerRow("舰载体制", selection: $vm.shipType, options: vm.radarOptions)
                    field("拦截弹射程 (km)", text: $vm.samRange)
                    field("拦截弹数量", text: $vm.ni)
                    field("拦截弹速度 (Ma)", text: $vm.vi)
                    field("拦截弹直径 (m)", text: $vm.interceptorDia)
                    pickerRow("制导头", selection: $vm.seekerType, options: vm.seekerOptions)
                    field("火控锁定时间 (s)", text: $vm.tlock)
                    field("最小交战距离 (km)", text: $vm.minr)

                    Button("◈ 估算交战距离与拦截率") {
                        Task { await vm.estimateDistanceAndPk() }
                    }
                    .buttonStyle(SatSecondaryButton())
                    if !vm.distNote.isEmpty {
                        Text(vm.distNote).font(.system(size: 10, design: .monospaced)).foregroundStyle(SaturationTheme.textDim)
                    }
                    if !vm.pkNote.isEmpty {
                        Text(vm.pkNote).font(.system(size: 10, design: .monospaced)).foregroundStyle(SaturationTheme.textDim)
                    }

                    field("雷达发现距离 (km)", text: $vm.discoveryKm)
                    field("单发拦截成功概率", text: $vm.pk)

                    Button(vm.running ? "计算中…" : "▶ 运行仿真") {
                        Task { await vm.run() }
                    }
                    .buttonStyle(SatPrimaryButton())
                    .disabled(vm.running)
                }

                if vm.hasResult, let r = vm.result {
                    resultsPanel(r)
                }
            }
            .padding(14)
        }
        .background(SaturationTheme.bg.ignoresSafeArea())
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("▲ 饱和打击 / 反导拦截仿真终端")
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundStyle(SaturationTheme.amber)
            Text("SATURATION ATTACK · LOCAL PYODIDE")
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(SaturationTheme.textDim)
            Text(vm.statusTag)
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(SaturationTheme.amber)
        }
    }

    private func resultsPanel(_ r: SaturationResult) -> some View {
        panel(title: "仿真结果 · \(vm.statusTag)") {
            HStack(spacing: 10) {
                stat("窗口数", "\(r.n_rounds ?? 0)", nil)
                stat("期望突防", String(format: "%.2f", r.expected_leak ?? 0), SaturationTheme.red)
                stat("拦截率", String(format: "%.1f%%", (r.intercept_rate ?? 0) * 100), SaturationTheme.green)
            }
            sectionLabel("▸ 拦截窗口", color: SaturationTheme.textDim)
            ForEach(r.windows ?? []) { w in
                Text("#\(w.round)  \(String(format: "%.1f", w.dist_start_km))→\(String(format: "%.1f", w.dist_end_km)) km  t=\(String(format: "%.1f", w.total_t_s))s")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(SaturationTheme.text)
            }
            if let best = r.best {
                sectionLabel("▸ 最优方案 \(best.name)", color: SaturationTheme.textDim)
                Text("[\(best.plan.map(String.init).joined(separator: ", "))]")
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(SaturationTheme.green)
            }
            sectionLabel("▸ 策略对比", color: SaturationTheme.textDim)
            ForEach(r.all_candidates ?? []) { c in
                Text("\(c.name)  [\(c.plan.map(String.init).joined(separator: ", "))]  突防 \(String(format: "%.2f", c.expected_leak))")
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(SaturationTheme.textDim)
            }
            if let note = r.note {
                Text(note)
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(SaturationTheme.textDim)
                    .padding(.top, 8)
            }
        }
    }

    private func panel<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(SaturationTheme.textDim)
            content()
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(SaturationTheme.panel)
        .overlay(Rectangle().stroke(SaturationTheme.line, lineWidth: 1))
    }

    private func sectionLabel(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 10, design: .monospaced))
            .foregroundStyle(color)
            .padding(.top, 6)
    }

    private func field(_ label: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(SaturationTheme.textDim)
            TextField("", text: text)
                .textFieldStyle(.plain)
                .padding(8)
                .background(SaturationTheme.panel2)
                .overlay(Rectangle().stroke(SaturationTheme.line, lineWidth: 1))
                .foregroundStyle(SaturationTheme.text)
                .font(.system(size: 13, design: .monospaced))
        }
    }

    private func pickerRow(_ label: String, selection: Binding<String>, options: [(String, String)]) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(SaturationTheme.textDim)
            Picker(label, selection: selection) {
                ForEach(options, id: \.0) { opt in
                    Text(opt.1).tag(opt.0)
                }
            }
            .pickerStyle(.menu)
            .tint(SaturationTheme.cyan)
        }
    }

    private func presetPicker(
        _ label: String,
        selection: Binding<String>,
        items: [SaturationPresetItem],
        onChange: @escaping () -> Void
    ) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(SaturationTheme.textDim)
            Picker(label, selection: selection) {
                Text("— 自定义 —").tag("")
                ForEach(items) { item in
                    Text(item.name).tag(item.id)
                }
            }
            .pickerStyle(.menu)
            .tint(SaturationTheme.amber)
            .onChange(of: selection.wrappedValue) { _, _ in onChange() }
        }
    }

    private func stat(_ k: String, _ v: String, _ color: Color?) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(k)
                .font(.system(size: 9, design: .monospaced))
                .foregroundStyle(SaturationTheme.textDim)
            Text(v)
                .font(.system(size: 20, design: .monospaced))
                .foregroundStyle(color ?? SaturationTheme.amber)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(SaturationTheme.panel2)
        .overlay(Rectangle().stroke(SaturationTheme.line, lineWidth: 1))
    }
}

private struct SatPrimaryButton: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .bold, design: .monospaced))
            .frame(maxWidth: .infinity)
            .padding(12)
            .background(SaturationTheme.amber)
            .foregroundStyle(Color(hex: 0x1A1300))
            .opacity(configuration.isPressed ? 0.85 : 1)
    }
}

private struct SatSecondaryButton: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12, weight: .bold, design: .monospaced))
            .frame(maxWidth: .infinity)
            .padding(10)
            .background(SaturationTheme.cyan)
            .foregroundStyle(Color(hex: 0x04262B))
            .opacity(configuration.isPressed ? 0.85 : 1)
    }
}
