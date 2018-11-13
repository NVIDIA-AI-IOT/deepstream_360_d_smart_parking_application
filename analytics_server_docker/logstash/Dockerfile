# https://github.com/elastic/logstash-docker
FROM docker.elastic.co/logstash/logstash-oss:6.4.0

# Add your logstash plugins setup here
# Example: RUN logstash-plugin install logstash-filter-json
RUN logstash-plugin install logstash-filter-json logstash-output-kafka
RUN logstash-plugin install logstash-filter-json logstash-input-kafka
RUN logstash-plugin install logstash-filter-json logstash-filter-fingerprint