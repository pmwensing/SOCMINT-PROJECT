FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends tor \
    && rm -rf /var/lib/apt/lists/*

CMD ["sh", "-c", "mkdir -p /var/lib/tor/socmint && chown -R debian-tor:debian-tor /var/lib/tor && chmod 700 /var/lib/tor /var/lib/tor/socmint && exec runuser -u debian-tor -- tor -f /etc/tor/torrc"]
