import SwiftUI

/// 模式 / 策略按钮组（对齐 mode-selector）
struct ModeSelector: View {
    let items: [ModeItem]
    @Binding var current: String
    var onChange: ((String) -> Void)?

    var body: some View {
        FlowLayout(spacing: 8) {
            ForEach(items) { item in
                Button {
                    current = item.id
                    onChange?(item.id)
                } label: {
                    Text(item.label)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(current == item.id ? Color(hex: 0x0F172A) : AppTheme.text)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .fill(current == item.id ? AppTheme.accent : AppTheme.surface2)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(current == item.id ? AppTheme.accent : AppTheme.border, lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
            }
        }
    }
}

/// 简易换行布局（替代 LazyVGrid，按钮宽度随文案）
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowH: CGFloat = 0
        var totalH: CGFloat = 0
        var totalW: CGFloat = 0
        for sub in subviews {
            let size = sub.sizeThatFits(.unspecified)
            if x + size.width > maxWidth, x > 0 {
                y += rowH + spacing
                totalH = y
                x = 0
                rowH = 0
            }
            x += size.width + spacing
            rowH = max(rowH, size.height)
            totalW = max(totalW, x - spacing)
            totalH = y + rowH
        }
        return CGSize(width: totalW, height: totalH)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        var y = bounds.minY
        var rowH: CGFloat = 0
        for sub in subviews {
            let size = sub.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX, x > bounds.minX {
                y += rowH + spacing
                x = bounds.minX
                rowH = 0
            }
            sub.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowH = max(rowH, size.height)
        }
    }
}
