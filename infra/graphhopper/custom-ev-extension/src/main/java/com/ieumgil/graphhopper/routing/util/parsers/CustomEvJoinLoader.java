package com.ieumgil.graphhopper.routing.util.parsers;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

final class CustomEvJoinLoader {
    private CustomEvJoinLoader() {
    }

    static Map<Long, Map<Integer, SegmentAccessibilityRow>> load(Path path) throws IOException {
        Map<Long, Map<Integer, SegmentAccessibilityRow>> rows = new HashMap<>();

        try (BufferedReader reader = Files.newBufferedReader(path)) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                return Collections.emptyMap();
            }
            String[] header = headerLine.split(",", -1);
            Map<String, Integer> index = new HashMap<>();
            for (int i = 0; i < header.length; i++) {
                index.put(header[i].trim(), i);
            }

            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                String[] values = line.split(",", -1);
                long wayId = Long.parseLong(value(values, index, "source_way_id"));
                int ordinal = Integer.parseInt(value(values, index, "segment_ordinal"));
                boolean hasCurbGap = parseBoolean(value(values, index, "has_curb_gap"));
                boolean hasAudioSignal = parseBoolean(value(values, index, "has_audio_signal"));
                Double widthMeter = parseNullableDouble(value(values, index, "width_meter"));

                rows.computeIfAbsent(wayId, ignored -> new HashMap<>())
                        .put(ordinal, new SegmentAccessibilityRow(hasCurbGap, hasAudioSignal, widthMeter));
            }
        }

        Map<Long, Map<Integer, SegmentAccessibilityRow>> immutable = new HashMap<>();
        for (Map.Entry<Long, Map<Integer, SegmentAccessibilityRow>> entry : rows.entrySet()) {
            immutable.put(entry.getKey(), Collections.unmodifiableMap(entry.getValue()));
        }
        return Collections.unmodifiableMap(immutable);
    }

    private static String value(String[] values, Map<String, Integer> index, String key) {
        Integer position = index.get(key);
        if (position == null || position >= values.length) {
            return "";
        }
        return values[position].trim();
    }

    private static boolean parseBoolean(String raw) {
        return "true".equalsIgnoreCase(raw) || "1".equals(raw) || "yes".equalsIgnoreCase(raw);
    }

    private static Double parseNullableDouble(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        return Double.parseDouble(raw);
    }
}
