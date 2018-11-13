DROP KEYSPACE IF EXISTS metromind;

CREATE KEYSPACE metromind WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '3'}  AND durable_writes = true;

CREATE TYPE metromind.coordinate (
    x double,
    y double,
    z double
);

CREATE TYPE metromind.aisle (
    id text,
    name text,
    level text,
    coordinate frozen<coordinate>
);

CREATE TYPE metromind.analyticsmodule (
    id text,
    description text,
    source text,
    version text
);

CREATE TYPE metromind.bbox (
    topleftx double,
    toplefty double,
    bottomrightx double,
    bottomrighty double
);

CREATE TYPE metromind.entrance (
    name text,
    lane text,
    level text,
    coordinate frozen<coordinate>
);

CREATE TYPE metromind.event (
    id text,
    type text,
    source text,
    email text
);

CREATE TYPE metromind.location (
    lat double,
    lon double,
    alt double
);

CREATE TYPE metromind.vehicle (
    type text,
    make text,
    model text,
    color text,
    confidence double,
    license text,
    licensestate text
);

CREATE TYPE metromind.object (
    id text,
    vehicle frozen<vehicle>,
    bbox frozen<bbox>,
    signature list<double>,
    speed double,
    direction double,
    orientation double,
    location frozen<location>,
    coordinate frozen<coordinate>
);

CREATE TYPE metromind.parkingspot (
    id text,
    type text,
    level text,
    coordinate frozen<coordinate>
);

CREATE TYPE metromind.place (
    id text,
    name text,
    type text,
    location frozen<location>,
    entrance frozen<entrance>,
    parkingspot frozen<parkingspot>,
    aisle frozen<aisle>
);

CREATE TYPE metromind.sensor (
    id text,
    type text,
    location frozen<location>,
    description text,
    coordinate frozen<coordinate>
);

CREATE TABLE metromind.aisle (
    messageid text,
    timestamp timestamp,
    analyticsmodule frozen<analyticsmodule>,
    event frozen<event>,
    mdsversion text,
    object frozen<object>,
    place frozen<place>,
    sensor frozen<sensor>,
    used int,
    videopath text,
    PRIMARY KEY (messageid, timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC)
    AND bloom_filter_fp_chance = 0.01
    AND caching = {'keys': 'ALL', 'rows_per_partition': 'NONE'}
    AND comment = ''
    AND compaction = {'class': 'org.apache.cassandra.db.compaction.SizeTieredCompactionStrategy', 'max_threshold': '32', 'min_threshold': '4'}
    AND compression = {'chunk_length_in_kb': '64', 'class': 'org.apache.cassandra.io.compress.LZ4Compressor'}
    AND crc_check_chance = 1.0
    AND dclocal_read_repair_chance = 0.1
    AND default_time_to_live = 0
    AND gc_grace_seconds = 864000
    AND max_index_interval = 2048
    AND memtable_flush_period_in_ms = 0
    AND min_index_interval = 128
    AND read_repair_chance = 0.0
    AND speculative_retry = '99PERCENTILE';

CREATE TABLE metromind.car_count (
    id text PRIMARY KEY,
    p1_available counter,
    p1_count counter,
    p2_available counter,
    p2_count counter,
    reserved_available counter,
    reserved_count counter,
    total_available counter,
    total_count counter
) WITH bloom_filter_fp_chance = 0.01
    AND caching = {'keys': 'ALL', 'rows_per_partition': 'NONE'}
    AND comment = ''
    AND compaction = {'class': 'org.apache.cassandra.db.compaction.SizeTieredCompactionStrategy', 'max_threshold': '32', 'min_threshold': '4'}
    AND compression = {'chunk_length_in_kb': '64', 'class': 'org.apache.cassandra.io.compress.LZ4Compressor'}
    AND crc_check_chance = 1.0
    AND dclocal_read_repair_chance = 0.1
    AND default_time_to_live = 0
    AND gc_grace_seconds = 864000
    AND max_index_interval = 2048
    AND memtable_flush_period_in_ms = 0
    AND min_index_interval = 128
    AND read_repair_chance = 0.0
    AND speculative_retry = '99PERCENTILE';

CREATE TABLE metromind.parkingspotplayback (
    garageid text,
    level text,
    sensortype text,
    spotid text,
    timestamp timestamp,
    analyticsmodule frozen<analyticsmodule>,
    event frozen<event>,
    mdsversion text,
    messageid text,
    object frozen<object>,
    place frozen<place>,
    sensor frozen<sensor>,
    used int,
    videopath text,
    PRIMARY KEY ((garageid, level, sensortype, spotid), timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC)
    AND bloom_filter_fp_chance = 0.01
    AND caching = {'keys': 'ALL', 'rows_per_partition': 'NONE'}
    AND comment = ''
    AND compaction = {'class': 'org.apache.cassandra.db.compaction.SizeTieredCompactionStrategy', 'max_threshold': '32', 'min_threshold': '4'}
    AND compression = {'chunk_length_in_kb': '64', 'class': 'org.apache.cassandra.io.compress.LZ4Compressor'}
    AND crc_check_chance = 1.0
    AND dclocal_read_repair_chance = 0.1
    AND default_time_to_live = 0
    AND gc_grace_seconds = 864000
    AND max_index_interval = 2048
    AND memtable_flush_period_in_ms = 0
    AND min_index_interval = 128
    AND read_repair_chance = 0.0
    AND speculative_retry = '99PERCENTILE';

CREATE TABLE metromind.parkingspot (
    messageid text,
    timestamp timestamp,
    analyticsmodule frozen<analyticsmodule>,
    event frozen<event>,
    mdsversion text,
    object frozen<object>,
    place frozen<place>,
    sensor frozen<sensor>,
    used int,
    videopath text,
    PRIMARY KEY (messageid, timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC)
    AND bloom_filter_fp_chance = 0.01
    AND caching = {'keys': 'ALL', 'rows_per_partition': 'NONE'}
    AND comment = ''
    AND compaction = {'class': 'org.apache.cassandra.db.compaction.SizeTieredCompactionStrategy', 'max_threshold': '32', 'min_threshold': '4'}
    AND compression = {'chunk_length_in_kb': '64', 'class': 'org.apache.cassandra.io.compress.LZ4Compressor'}
    AND crc_check_chance = 1.0
    AND dclocal_read_repair_chance = 0.1
    AND default_time_to_live = 0
    AND gc_grace_seconds = 864000
    AND max_index_interval = 2048
    AND memtable_flush_period_in_ms = 0
    AND min_index_interval = 128
    AND read_repair_chance = 0.0
    AND speculative_retry = '99PERCENTILE';

CREATE TABLE metromind.flowrate (
    id text,
    timestamp timestamp,
    entry int,
    exit int,
    PRIMARY KEY (id, timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC)
    AND bloom_filter_fp_chance = 0.01
    AND caching = {'keys': 'ALL', 'rows_per_partition': 'NONE'}
    AND comment = ''
    AND compaction = {'class': 'org.apache.cassandra.db.compaction.SizeTieredCompactionStrategy', 'max_threshold': '32', 'min_threshold': '4'}
    AND compression = {'chunk_length_in_kb': '64', 'class': 'org.apache.cassandra.io.compress.LZ4Compressor'}
    AND crc_check_chance = 1.0
    AND dclocal_read_repair_chance = 0.1
    AND default_time_to_live = 0
    AND gc_grace_seconds = 864000
    AND max_index_interval = 2048
    AND memtable_flush_period_in_ms = 0
    AND min_index_interval = 128
    AND read_repair_chance = 0.0
    AND speculative_retry = '99PERCENTILE';

CREATE TABLE metromind.parkingspotdelta (
    garageid text,
    level text,
    sensortype text,
    timestamp timestamp,
    analyticsmodule frozen<analyticsmodule>,
    event frozen<event>,
    mdsversion text,
    messageid text,
    object frozen<object>,
    place frozen<place>,
    sensor frozen<sensor>,
    spotid text,
    used int,
    videopath text,
    PRIMARY KEY ((garageid, level, sensortype), timestamp, spotid)
) WITH CLUSTERING ORDER BY (timestamp DESC, spotid ASC)
    AND bloom_filter_fp_chance = 0.01
    AND caching = {'keys': 'ALL', 'rows_per_partition': 'NONE'}
    AND comment = ''
    AND compaction = {'class': 'org.apache.cassandra.db.compaction.SizeTieredCompactionStrategy', 'max_threshold': '32', 'min_threshold': '4'}
    AND compression = {'chunk_length_in_kb': '64', 'class': 'org.apache.cassandra.io.compress.LZ4Compressor'}
    AND crc_check_chance = 1.0
    AND dclocal_read_repair_chance = 0.1
    AND default_time_to_live = 0
    AND gc_grace_seconds = 864000
    AND max_index_interval = 2048
    AND memtable_flush_period_in_ms = 0
    AND min_index_interval = 128
    AND read_repair_chance = 0.0
    AND speculative_retry = '99PERCENTILE';

CREATE TABLE metromind.parkingspotstate (
    garageid text,
    level text,
    spotid text,
    analyticsmodule frozen<analyticsmodule>,
    event frozen<event>,
    mdsversion text,
    messageid text,
    object frozen<object>,
    place frozen<place>,
    sensor frozen<sensor>,
    timestamp timestamp,
    used int,
    videopath text,
    PRIMARY KEY ((garageid, level), spotid)
) WITH CLUSTERING ORDER BY (spotid ASC)
    AND bloom_filter_fp_chance = 0.01
    AND caching = {'keys': 'ALL', 'rows_per_partition': 'NONE'}
    AND comment = ''
    AND compaction = {'class': 'org.apache.cassandra.db.compaction.SizeTieredCompactionStrategy', 'max_threshold': '32', 'min_threshold': '4'}
    AND compression = {'chunk_length_in_kb': '64', 'class': 'org.apache.cassandra.io.compress.LZ4Compressor'}
    AND crc_check_chance = 1.0
    AND dclocal_read_repair_chance = 0.1
    AND default_time_to_live = 0
    AND gc_grace_seconds = 864000
    AND max_index_interval = 2048
    AND memtable_flush_period_in_ms = 0
    AND min_index_interval = 128
    AND read_repair_chance = 0.0
    AND speculative_retry = '99PERCENTILE';
    
UPDATE metromind.car_count SET total_available = total_available + 0, total_count = total_count + 0  WHERE id = 'endeavor';

    