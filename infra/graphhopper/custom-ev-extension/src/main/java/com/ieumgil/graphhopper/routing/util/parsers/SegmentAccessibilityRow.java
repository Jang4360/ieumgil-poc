package com.ieumgil.graphhopper.routing.util.parsers;

final class SegmentAccessibilityRow {
    private final boolean hasCurbGap;
    private final boolean hasAudioSignal;
    private final Double widthMeter;

    SegmentAccessibilityRow(boolean hasCurbGap, boolean hasAudioSignal, Double widthMeter) {
        this.hasCurbGap = hasCurbGap;
        this.hasAudioSignal = hasAudioSignal;
        this.widthMeter = widthMeter;
    }

    boolean hasCurbGap() {
        return hasCurbGap;
    }

    boolean hasAudioSignal() {
        return hasAudioSignal;
    }

    Double widthMeter() {
        return widthMeter;
    }
}
