ARG GRAPHHOPPER_VERSION=11.0

FROM eclipse-temurin:21-jre

ARG GRAPHHOPPER_VERSION

WORKDIR /opt/graphhopper

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o graphhopper-web.jar "https://repo1.maven.org/maven2/com/graphhopper/graphhopper-web/${GRAPHHOPPER_VERSION}/graphhopper-web-${GRAPHHOPPER_VERSION}.jar" \
    && curl -fsSL -o config.yml "https://raw.githubusercontent.com/graphhopper/graphhopper/${GRAPHHOPPER_VERSION%%.*}.x/config-example.yml"

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8989

ENTRYPOINT ["docker-entrypoint.sh"]
