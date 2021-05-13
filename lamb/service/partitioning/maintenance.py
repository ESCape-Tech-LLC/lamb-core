from datetime import date

from celery.utils.log import get_task_logger
from dateutil import relativedelta
from django.conf import settings

from lamb.db.context import lamb_db_context

__all__ = ['maintenance_of_partitioned_tables']

logger = get_task_logger(__name__)


def _get_table_names_within_months_count(table_name, months_count: int):
    table_name_pattern = '{}_y{}m{}'.format
    result_table_names = []
    current_date = date.today()
    for i in range(-1, months_count):
        working_date = current_date - relativedelta.relativedelta(months=i)
        result_table_names.append(table_name_pattern(table_name,
                                                     working_date.strftime('%Y'),
                                                     working_date.strftime('%m')))
    return result_table_names


def maintenance_of_partitioned_tables():
    lamb_partitioning_settings = settings.LAMB_PARTITIONING_SETTINGS
    table_name_pattern = '{}_y{}m{}'.format
    current_date = date.today()
    logger.info('Start maintenance_of_partitioned_tables')
    with lamb_db_context() as db_session:
        for table_name, partitioning_depth, required_action in lamb_partitioning_settings:
            all_partitions = db_session.execute(
                f"SELECT relname, relispartition FROM pg_class WHERE relname SIMILAR TO '{table_name}_y____m__';"
            )
            all_partitions = list(all_partitions)
            all_attached_partitions = [el[0] for el in all_partitions if el[1]]
            if partitioning_depth is not None and required_action is not None:
                table_names_within_months_count = _get_table_names_within_months_count(table_name,
                                                                                       partitioning_depth)
                all_detached_partitions = [el[0] for el in all_partitions if not el[1]]
                # detach or delete unnecessary partitions
                for attached_partition in all_attached_partitions:
                    if attached_partition not in table_names_within_months_count:
                        if required_action == 'detach':
                            logger.info(f'Detach partition {attached_partition} for table {table_name}')
                            print(f'Detach partition {attached_partition} for table {table_name}')
                            db_session.execute(
                                f"ALTER TABLE {table_name} DETACH PARTITION {attached_partition}"
                            )
                        else:
                            # required_action == 'delete'
                            db_session.execute(
                                f"DROP TABLE {attached_partition} CASCADE"
                            )
                        db_session.commit()
                # attach necessary partitions
                if required_action == 'detach':
                    for i in range(-1, partitioning_depth):
                        working_date = current_date - relativedelta.relativedelta(months=i)
                        partition_name = table_name_pattern(table_name,
                                                            working_date.strftime('%Y'),
                                                            working_date.strftime('%m'))
                        if partition_name not in all_attached_partitions:
                            if partition_name in all_detached_partitions:
                                date_from_year = working_date.strftime('%Y')
                                date_from_month = working_date.strftime('%m')
                                date_to = working_date + relativedelta.relativedelta(months=1)
                                date_to_year = date_to.strftime('%Y')
                                date_to_month = date_to.strftime('%m')
                                logger.info(f'Attach partition {partition_name} for table {table_name}')
                                db_session.execute(
                                    f"ALTER TABLE {table_name} ATTACH PARTITION {partition_name} "
                                    f"FOR VALUES FROM ('{date_from_year}-{date_from_month}-01') "
                                    f"TO ('{date_to_year}-{date_to_month}-01');"
                                )
                                db_session.commit()
            # check and create partition for the next month
            next_month_date = current_date + relativedelta.relativedelta(months=1)
            next_month_partition_name = table_name_pattern(table_name,
                                                           next_month_date.strftime('%Y'),
                                                           next_month_date.strftime('%m'))
            if next_month_partition_name not in all_attached_partitions:
                date_from_year = next_month_date.strftime('%Y')
                date_from_month = next_month_date.strftime('%m')
                date_to = next_month_date + relativedelta.relativedelta(months=1)
                date_to_year = date_to.strftime('%Y')
                date_to_month = date_to.strftime('%m')
                logger.info(f'Create partition {next_month_partition_name} for {table_name}')
                db_session.execute(
                    f"CREATE TABLE IF NOT EXISTS {next_month_partition_name} PARTITION OF {table_name} "
                    f"FOR VALUES FROM ('{date_from_year}-{date_from_month}-01') "
                    f"TO ('{date_to_year}-{date_to_month}-01');"
                )
                db_session.commit()
