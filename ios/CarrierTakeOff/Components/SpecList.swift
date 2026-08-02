import SwiftUI

/// 参数键值列表（对齐 spec-list）
struct SpecListView: View {
    let items: [SpecItem]
    var emptyText: String = "暂无数据"

    var body: some View {
        if items.isEmpty {
            Text(emptyText)
                .font(.system(size: 13))
                .foregroundStyle(AppTheme.muted)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.top, 8)
        } else {
            VStack(spacing: 0) {
                ForEach(items) { item in
                    HStack(alignment: .top) {
                        Text(item.label)
                            .font(.system(size: 13))
                            .foregroundStyle(AppTheme.muted)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        Text(item.value)
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(AppTheme.text)
                            .multilineTextAlignment(.trailing)
                    }
                    .padding(.vertical, 8)
                    Divider().overlay(AppTheme.border.opacity(0.6))
                }
            }
            .padding(.top, 4)
        }
    }
}

/// 卡片容器
struct CardView<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(AppTheme.accent)
                .tracking(0.3)
            content
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.radius)
                .fill(AppTheme.surface)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.radius)
                        .stroke(AppTheme.border, lineWidth: 1)
                )
        )
    }
}

/// 状态条
struct StatusBar: View {
    let text: String
    let kind: StatusKind

    var body: some View {
        if !text.isEmpty {
            Text(text)
                .font(.system(size: 13))
                .foregroundStyle(fg)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(AppTheme.surface2)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(border, lineWidth: 1)
                        )
                )
        }
    }

    private var fg: Color {
        switch kind {
        case .ok: return AppTheme.success
        case .error: return AppTheme.danger
        case .loading: return AppTheme.accent
        case .idle: return AppTheme.muted
        }
    }

    private var border: Color {
        switch kind {
        case .ok: return AppTheme.success.opacity(0.35)
        case .error: return AppTheme.danger.opacity(0.35)
        case .loading: return AppTheme.accent.opacity(0.35)
        case .idle: return .clear
        }
    }
}

/// 深色表单输入
struct FieldInput: View {
    let label: String
    @Binding var text: String
    var readonly: Bool = false
    var onEdit: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label)
                .font(.system(size: 12))
                .foregroundStyle(AppTheme.muted)
            TextField("", text: $text)
                .keyboardType(.decimalPad)
                .disabled(readonly)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .foregroundStyle(readonly ? AppTheme.muted : AppTheme.text)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(AppTheme.surface2)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(AppTheme.border, lineWidth: 1)
                        )
                )
                .onChange(of: text) { _, _ in
                    if !readonly { onEdit?() }
                }
        }
    }
}
