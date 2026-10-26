// 3.2 Unique constraints on the three business IDs and a range index on TRANSFER.occurred_at
CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE;
CREATE CONSTRAINT account_id_unique  IF NOT EXISTS FOR (a:Account)  REQUIRE a.account_id  IS UNIQUE;
CREATE CONSTRAINT device_id_unique   IF NOT EXISTS FOR (d:Device)   REQUIRE d.device_id   IS UNIQUE;
CREATE RANGE INDEX transfer_occurred_at IF NOT EXISTS FOR ()-[t:TRANSFER]-() ON (t.occurred_at);

// Wait until every index is online (up to 15 minutes)
CALL db.awaitIndexes(900);

SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties, ownedIndex
RETURN name, type, entityType, labelsOrTypes, properties, ownedIndex;

SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties, state, populationPercent
RETURN name, type, entityType, labelsOrTypes, properties, state, populationPercent;
