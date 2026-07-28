
            SELECT
              catalog_name as project_id,
              schema_name as dataset_id,
              replica_name,
              location as region,
              replica_primary_assigned,
              replica_primary_assignment_complete,
              creation_complete,
              UNIX_MILLIS(creation_time) as creation_time_millis,
              UNIX_MILLIS(replication_time) as replication_time_millis
            FROM `cloudhub-470100`.`region-us-central1`.INFORMATION_SCHEMA.SCHEMATA_REPLICAS
            WHERE catalog_name = 'cloudhub-470100'
              AND schema_name = 'project_2025_09_22_01_39_04_20d10ea0_9a37_40be_b322_29c86c0b9012'
          