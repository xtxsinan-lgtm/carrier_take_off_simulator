import SwiftUI

/// 起飞轨迹侧视剖面（对齐 trajectory-chart）
struct TrajectoryChart: View {
    let result: SimulationResult?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("侧视剖面：甲板折线与飞机质心轨迹（水平 x、高度 y，单位 m）")
                .font(.system(size: 12))
                .foregroundStyle(AppTheme.muted)
            if let meta = metaText {
                Text(meta)
                    .font(.system(size: 12))
                    .foregroundStyle(AppTheme.muted)
            }
            Canvas { context, size in
                paint(context: context, size: size)
            }
            .frame(height: 220)
            .background(AppTheme.surface)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            HStack(spacing: 12) {
                legend(color: Color(hex: 0x64748B), title: "甲板")
                legend(color: AppTheme.accent, title: "飞机轨迹")
                legend(color: AppTheme.danger.opacity(0.7), title: "离舰点")
            }
            .font(.system(size: 11))
            .foregroundStyle(AppTheme.muted)
        }
    }

    private var metaText: String? {
        guard let result, let deck = result.deck_profile, let traj = result.trajectory, !traj.isEmpty else {
            return nil
        }
        let dist = result.distance_m ?? deck.takeoff_distance_m
        let n = traj.count
        if let dist {
            return "滑跑/离舰距离 \(Physics.fmtNum(dist, digits: 1)) m · 轨迹点 \(n)"
        }
        return "轨迹点 \(n)"
    }

    private func legend(color: Color, title: String) -> some View {
        HStack(spacing: 4) {
            RoundedRectangle(cornerRadius: 2)
                .fill(color)
                .frame(width: 12, height: 4)
            Text(title)
        }
    }

    private func paint(context: GraphicsContext, size: CGSize) {
        guard let result,
              let deck = result.deck_profile,
              let traj = result.trajectory,
              !deck.points.isEmpty,
              !traj.isEmpty
        else { return }

        let deckPts = deck.points.compactMap { p -> CGPoint? in
            guard p.count >= 2 else { return nil }
            return CGPoint(x: p[0], y: p[1])
        }
        guard !deckPts.isEmpty else { return }

        let takeoffX = resolveTakeoffX(result: result, deckPts: deckPts, traj: traj)
        var xs = deckPts.map(\.x) + traj.map { CGFloat($0.x) } + [CGFloat(takeoffX)]
        if let carrierDeck = deck.total_deck_length_m {
            xs.append(CGFloat(carrierDeck))
        }
        let ys = deckPts.map(\.y) + traj.map { CGFloat($0.y) }
        let minX: CGFloat = 0
        let maxX = max(xs.max() ?? 1, 1) * 1.08
        let minY = min(0, ys.min() ?? 0) - 2
        let maxY = max(ys.max() ?? 1, CGFloat(deck.lip_height_m ?? 0), 1) + 8

        let padL: CGFloat = 36
        let padR: CGFloat = 12
        let padT: CGFloat = 24
        let padB: CGFloat = 36
        let plotW = size.width - padL - padR
        let plotH = size.height - padT - padB

        func toX(_ x: CGFloat) -> CGFloat { padL + ((x - minX) / (maxX - minX)) * plotW }
        func toY(_ y: CGFloat) -> CGFloat { padT + plotH - ((y - minY) / (maxY - minY)) * plotH }

        // 网格
        let xStep = xAxisStep(maxX)
        var grid = Path()
        var gx: CGFloat = 0
        while gx <= maxX {
            grid.move(to: CGPoint(x: toX(gx), y: padT))
            grid.addLine(to: CGPoint(x: toX(gx), y: padT + plotH))
            gx += xStep
        }
        var gy = ceil(minY / 5) * 5
        while gy <= maxY {
            grid.move(to: CGPoint(x: padL, y: toY(gy)))
            grid.addLine(to: CGPoint(x: padL + plotW, y: toY(gy)))
            gy += 5
        }
        context.stroke(grid, with: .color(AppTheme.muted.opacity(0.15)), lineWidth: 1)

        // 甲板
        var deckPath = Path()
        for (i, p) in deckPts.enumerated() {
            let pt = CGPoint(x: toX(p.x), y: toY(p.y))
            if i == 0 { deckPath.move(to: pt) } else { deckPath.addLine(to: pt) }
        }
        context.stroke(deckPath, with: .color(Color(hex: 0x64748B)), lineWidth: 2)

        // 轨迹
        var trajPath = Path()
        for (i, p) in traj.enumerated() {
            let pt = CGPoint(x: toX(CGFloat(p.x)), y: toY(CGFloat(p.y)))
            if i == 0 { trajPath.move(to: pt) } else { trajPath.addLine(to: pt) }
        }
        context.stroke(trajPath, with: .color(AppTheme.accent), lineWidth: 2)

        // 离舰竖线
        var limit = Path()
        limit.move(to: CGPoint(x: toX(CGFloat(takeoffX)), y: padT))
        limit.addLine(to: CGPoint(x: toX(CGFloat(takeoffX)), y: padT + plotH))
        context.stroke(limit, with: .color(AppTheme.danger.opacity(0.55)), style: StrokeStyle(lineWidth: 1, dash: [4, 3]))

        // 标记点
        if let first = traj.first {
            let c = CGPoint(x: toX(CGFloat(first.x)), y: toY(CGFloat(first.y)))
            context.fill(Path(ellipseIn: CGRect(x: c.x - 3, y: c.y - 3, width: 6, height: 6)), with: .color(AppTheme.success))
        }
        if let last = traj.last {
            let c = CGPoint(x: toX(CGFloat(last.x)), y: toY(CGFloat(last.y)))
            context.fill(Path(ellipseIn: CGRect(x: c.x - 3, y: c.y - 3, width: 6, height: 6)), with: .color(AppTheme.accent))
        }
    }

    private func xAxisStep(_ maxX: CGFloat) -> CGFloat {
        if maxX <= 80 { return 10 }
        if maxX <= 200 { return 20 }
        if maxX <= 400 { return 50 }
        return 100
    }

    private func resolveTakeoffX(result: SimulationResult, deckPts: [CGPoint], traj: [TrajectoryPoint]) -> Double {
        if let exit = traj.first(where: { $0.phase == "deck_exit" }) {
            return exit.x
        }
        if let d = result.deck_profile?.takeoff_distance_m { return d }
        if let d = result.distance_m { return d }
        return Double(deckPts.last?.x ?? 0)
    }
}
