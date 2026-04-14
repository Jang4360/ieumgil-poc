package com.ieumgil.graphhopper.routing.util.parsers;

import com.graphhopper.reader.ReaderWay;
import com.graphhopper.routing.ev.BooleanEncodedValue;
import com.graphhopper.routing.ev.EdgeIntAccess;
import com.graphhopper.routing.ev.EncodedValueLookup;
import com.graphhopper.routing.util.parsers.TagParser;
import com.graphhopper.storage.IntsRef;
import com.ieumgil.graphhopper.routing.ev.HasBrailleBlock;
import com.ieumgil.graphhopper.routing.ev.HasElevator;

public final class AccessibilityOsmTagParser implements TagParser {
    private final BooleanEncodedValue hasElevatorEnc;
    private final BooleanEncodedValue hasBrailleBlockEnc;

    public AccessibilityOsmTagParser(EncodedValueLookup lookup) {
        hasElevatorEnc = lookup.getBooleanEncodedValue(HasElevator.KEY);
        hasBrailleBlockEnc = lookup.getBooleanEncodedValue(HasBrailleBlock.KEY);
    }

    @Override
    public void handleWayTags(int edgeId, EdgeIntAccess edgeIntAccess, ReaderWay way, IntsRef relationFlags) {
        boolean hasElevator = way.hasTag("elevator", "yes") || way.hasTag("highway", "elevator");
        String tactilePaving = way.getTag("tactile_paving");
        boolean hasBrailleBlock = "yes".equals(tactilePaving) || "contrasted".equals(tactilePaving);

        hasElevatorEnc.setBool(false, edgeId, edgeIntAccess, hasElevator);
        hasBrailleBlockEnc.setBool(false, edgeId, edgeIntAccess, hasBrailleBlock);
    }
}
