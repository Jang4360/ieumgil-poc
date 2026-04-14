package com.ieumgil.graphhopper.routing.ev;

import com.graphhopper.routing.ev.DecimalEncodedValueImpl;
import com.graphhopper.routing.ev.EncodedValue;

public final class WidthMeter {
    public static final String KEY = "width_meter";
    public static final double MISSING_SENTINEL = 0.0;

    private WidthMeter() {
    }

    public static EncodedValue create() {
        return new DecimalEncodedValueImpl(KEY, 10, 0.05, false);
    }
}
