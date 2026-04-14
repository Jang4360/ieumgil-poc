package com.ieumgil.graphhopper.routing.ev;

import com.graphhopper.routing.ev.EncodedValue;
import com.graphhopper.routing.ev.SimpleBooleanEncodedValue;

public final class HasElevator {
    public static final String KEY = "has_elevator";

    private HasElevator() {
    }

    public static EncodedValue create() {
        return new SimpleBooleanEncodedValue(KEY);
    }
}
