FROM cassandra:3.11.2

WORKDIR /home/cassandra

COPY entrypoint-wrap.sh .

COPY schema.cql .

ENTRYPOINT ["/home/cassandra/entrypoint-wrap.sh"]

CMD ["cassandra", "-f"]