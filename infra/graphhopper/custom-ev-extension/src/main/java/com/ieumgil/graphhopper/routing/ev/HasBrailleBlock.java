package com.ieumgil.graphhopper.routing.ev;

import com.graphhopper.routing.ev.EncodedValue;
import com.graphhopper.routing.ev.SimpleBooleanEncodedValue;

public final class HasBrailleBlock {
    public static final String KEY = "has_braille_block";

    private HasBrailleBlock() {
    }

    public static EncodedValue create() {
        return new SimpleBooleanEncodedValue(KEY);
    }
}
