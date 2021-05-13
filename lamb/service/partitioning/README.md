1. Partitioning with native Postgresql commands
    1. create partitions (run script)
    2. set settings for maintenance partitions
    3. tune maintenance celery task

## Partitioning with native Postgresql commands

1. create partitions (run script) <br>
   Define partitioning params: table names, partitioning attribute, number available months, required action (delete,
   detach, NULL) <br>
   Run migration script with params string:

   ```shell
   psql -U postgres your_db < /<path to lamb>/lamb/service/partitioning/migrations/DB_LAMB_create_partitions.sql -v params="'lamb_event_track,time_created,3,delete,lamb_event_record,time_created,3,delete,lamb_execution_time_metric,start_time,3,delete'"
   ```
2. set settings for maintenance partitions <br>
   Edit LAMB_PARTITIONING_SETTINGS - specify table name, number available months, required action (
   delete\detach\None) <br>
   e.g.:
   ```python
   LAMB_PARTITIONING_SETTINGS = [
    ('lamb_event_track',  3, 'delete'),
    ('lamb_event_record', 3, 'delete'),
    ('lamb_execution_time_metric', 3, 'delete'),
   ]
   ```
3. tune maintenance celery task <br>
 def maintenance_of_partitioned_tables at lamb.service.partitioning.maintenance