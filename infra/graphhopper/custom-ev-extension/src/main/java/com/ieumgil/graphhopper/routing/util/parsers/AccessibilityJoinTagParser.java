package com.ieumgil.graphhopper.routing.util.parsers;

import com.graphhopper.reader.ReaderWay;
import com.graphhopper.routing.ev.BooleanEncodedValue;
import com.graphhopper.routing.ev.DecimalEncodedValue;
import com.graphhopper.routing.ev.EdgeIntAccess;
import com.graphhopper.routing.ev.EncodedValueLookup;
import com.graphhopper.routing.util.parsers.TagParser;
import com.graphhopper.storage.IntsRef;
import com.ieumgil.graphhopper.routing.ev.HasAudioSignal;
import com.ieumgil.graphhopper.routing.ev.HasCurbGap;
import com.ieumgil.graphhopper.routing.ev.WidthMeter;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class AccessibilityJoinTagParser implements TagParser {
    public static final String JOIN_FILE_PROPERTY = "ieumgil.graphhopper.custom_ev_join_file";

    private static final Logger LOGGER = LoggerFactory.getLogger(AccessibilityJoinTagParser.class);
    private static Map<Long, Map<Integer, SegmentAccessibilityRow>> cachedRows;
    private static String cachedPath;

    private final BooleanEncodedValue hasCurbGapEnc;
    private final BooleanEncodedValue hasAudioSignalEnc;
    private final DecimalEncodedValue widthMeterEnc;
    private final Map<Long, Map<Integer, SegmentAccessibilityRow>> rowsByWayAndOrdinal;
    private final Map<Long, Integer> wayOrdinalCounter = new HashMap<>();

    public AccessibilityJoinTagParser(EncodedValueLookup lookup) {
        hasCurbGapEnc = lookup.getBooleanEncodedValue(HasCurbGap.KEY);
        hasAudioSignalEnc = lookup.getBooleanEncodedValue(HasAudioSignal.KEY);
        widthMeterEnc = lookup.getDecimalEncodedValue(WidthMeter.KEY);
        rowsByWayAndOrdinal = loadFromConfiguredFile();
    }

    @Override
    public void handleWayTags(int edgeId, EdgeIntAccess edgeIntAccess, ReaderWay way, IntsRef relationFlags) {
        int ordinal = wayOrdinalCounter.compute(way.getId(), (ignored, current) -> current == null ? 1 : current + 1);
        SegmentAccessibilityRow row = rowsByWayAndOrdinal.getOrDefault(way.getId(), Collections.emptyMap()).get(ordinal);
        if (row == null) {
            return;
        }

        hasCurbGapEnc.setBool(false, edgeId, edgeIntAccess, row.hasCurbGap());
        hasAudioSignalEnc.setBool(false, edgeId, edgeIntAccess, row.hasAudioSignal());
        widthMeterEnc.setDecimal(
                false,
                edgeId,
                edgeIntAccess,
                row.widthMeter() == null ? WidthMeter.MISSING_SENTINEL : row.widthMeter()
        );
    }

    private static synchronized Map<Long, Map<Integer, SegmentAccessibilityRow>> loadFromConfiguredFile() {
        String configuredPath = System.getProperty(JOIN_FILE_PROPERTY, "").trim();
        if (configuredPath.isBlank()) {
            LOGGER.warn("custom EV join file is not configured. property={}", JOIN_FILE_PROPERTY);
            return Collections.emptyMap();
        }
        if (configuredPath.equals(cachedPath) && cachedRows != null) {
            return cachedRows;
        }

        try {
            cachedRows = CustomEvJoinLoader.load(Path.of(configuredPath));
            cachedPath = configuredPath;
            LOGGER.info("loaded custom EV join rows from {} for {} OSM ways", configuredPath, cachedRows.size());
            return cachedRows;
        } catch (IOException e) {
            LOGGER.warn("failed to load custom EV join rows from {}: {}", configuredPath, e.getMessage());
            cachedRows = Collections.emptyMap();
            cachedPath = configuredPath;
            return cachedRows;
        }
    }
}
