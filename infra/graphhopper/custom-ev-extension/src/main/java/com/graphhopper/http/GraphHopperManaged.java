package com.graphhopper.http;

import com.graphhopper.GraphHopper;
import com.graphhopper.GraphHopperConfig;
import com.graphhopper.gtfs.GraphHopperGtfs;
import com.ieumgil.graphhopper.routing.ev.IeumgilImportRegistry;
import io.dropwizard.lifecycle.Managed;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class GraphHopperManaged implements Managed {
    private static final Logger LOGGER = LoggerFactory.getLogger(GraphHopperManaged.class);

    private final GraphHopper graphHopper;

    public GraphHopperManaged(GraphHopperConfig config) {
        graphHopper = config.has("gtfs.file") ? new GraphHopperGtfs(config) : new GraphHopper();
        graphHopper.setImportRegistry(new IeumgilImportRegistry()).init(config);
    }

    @Override
    public void start() {
        graphHopper.importOrLoad();
        LOGGER.info(
                "loaded graph at:{}, data_reader_file:{}, encoded values:{}, {} bytes for edge flags, {}",
                graphHopper.getGraphHopperLocation(),
                graphHopper.getOSMFile(),
                graphHopper.getEncodingManager().toEncodedValuesAsString(),
                graphHopper.getEncodingManager().getBytesForFlags(),
                graphHopper.getBaseGraph().toDetailsString()
        );
    }

    public GraphHopper getGraphHopper() {
        return graphHopper;
    }

    @Override
    public void stop() {
        graphHopper.close();
    }
}
