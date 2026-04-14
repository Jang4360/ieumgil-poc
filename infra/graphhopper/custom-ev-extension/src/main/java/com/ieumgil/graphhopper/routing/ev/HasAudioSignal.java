package com.ieumgil.graphhopper.routing.ev;

import com.graphhopper.routing.ev.EncodedValue;
import com.graphhopper.routing.ev.SimpleBooleanEncodedValue;

public final class HasAudioSignal {
    public static final String KEY = "has_audio_signal";

    private HasAudioSignal() {
    }

    public static EncodedValue create() {
        return new SimpleBooleanEncodedValue(KEY);
    }
}
