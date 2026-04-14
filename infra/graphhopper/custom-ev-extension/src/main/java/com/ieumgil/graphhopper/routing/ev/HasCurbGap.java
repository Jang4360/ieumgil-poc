package com.ieumgil.graphhopper.routing.ev;

import com.graphhopper.routing.ev.EncodedValue;
import com.graphhopper.routing.ev.SimpleBooleanEncodedValue;

public final class HasCurbGap {
    public static final String KEY = "has_curb_gap";

    private HasCurbGap() {
    }

    public static EncodedValue create() {
        return new SimpleBooleanEncodedValue(KEY);
    }
}
