// MeasurementCard.swift
// AlbaceteMedDev
//
// Reusable card displaying a single wound measurement.

import SwiftUI

struct MeasurementCard: View {

    let title: String
    let value: String
    let unit: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Icon + title row
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(color)

                Text(title)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .textCase(.uppercase)
                    .tracking(0.5)
            }

            // Value + unit
            HStack(alignment: .lastTextBaseline, spacing: 4) {
                Text(value)
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundStyle(.primary)

                Text(unit)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.06), radius: 4, x: 0, y: 2)
    }
}

// MARK: - Convenience factory for wound measurements

extension MeasurementCard {
    static func length(_ mm: Double) -> MeasurementCard {
        MeasurementCard(
            title: "Length",
            value: String(format: "%.1f", mm),
            unit: "mm",
            icon: "arrow.left.and.right",
            color: .blue
        )
    }

    static func width(_ mm: Double) -> MeasurementCard {
        MeasurementCard(
            title: "Width",
            value: String(format: "%.1f", mm),
            unit: "mm",
            icon: "arrow.up.and.down",
            color: .teal
        )
    }

    static func bedArea(_ cm2: Double) -> MeasurementCard {
        MeasurementCard(
            title: "Bed Area",
            value: String(format: "%.2f", cm2),
            unit: "cm²",
            icon: "square.dashed",
            color: .orange
        )
    }

    static func depth(_ mm: Double) -> MeasurementCard {
        MeasurementCard(
            title: "Depth",
            value: String(format: "%.1f", mm),
            unit: "mm",
            icon: "arrow.down.to.line",
            color: .red
        )
    }
}

// MARK: - Preview

#Preview {
    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
        MeasurementCard.length(42.3)
        MeasurementCard.width(28.7)
        MeasurementCard.bedArea(9.84)
        MeasurementCard.depth(6.2)
    }
    .padding()
    .background(Color(.systemGroupedBackground))
}
