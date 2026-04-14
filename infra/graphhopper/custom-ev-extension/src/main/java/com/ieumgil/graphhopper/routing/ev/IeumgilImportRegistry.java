package com.ieumgil.graphhopper.routing.ev;

import com.graphhopper.routing.ev.DefaultImportRegistry;
import com.graphhopper.routing.ev.ImportUnit;
import com.ieumgil.graphhopper.routing.util.parsers.AccessibilityJoinTagParser;
import com.ieumgil.graphhopper.routing.util.parsers.AccessibilityOsmTagParser;
import com.ieumgil.graphhopper.routing.util.parsers.NoOpTagParser;

public final class IeumgilImportRegistry extends DefaultImportRegistry {
    @Override
    public ImportUnit createImportUnit(String name) {
        return switch (name) {
            case HasElevator.KEY -> ImportUnit.create(
                    HasElevator.KEY,
                    ignored -> HasElevator.create(),
                    (lookup, ignored) -> new AccessibilityOsmTagParser(lookup),
                    HasBrailleBlock.KEY
            );
            case HasBrailleBlock.KEY -> ImportUnit.create(
                    HasBrailleBlock.KEY,
                    ignored -> HasBrailleBlock.create(),
                    (lookup, ignored) -> new NoOpTagParser()
            );
            case HasCurbGap.KEY -> ImportUnit.create(
                    HasCurbGap.KEY,
                    ignored -> HasCurbGap.create(),
                    (lookup, ignored) -> new AccessibilityJoinTagParser(lookup),
                    HasAudioSignal.KEY,
                    WidthMeter.KEY
            );
            case HasAudioSignal.KEY -> ImportUnit.create(
                    HasAudioSignal.KEY,
                    ignored -> HasAudioSignal.create(),
                    (lookup, ignored) -> new NoOpTagParser()
            );
            case WidthMeter.KEY -> ImportUnit.create(
                    WidthMeter.KEY,
                    ignored -> WidthMeter.create(),
                    (lookup, ignored) -> new NoOpTagParser()
            );
            default -> super.createImportUnit(name);
        };
    }
}
