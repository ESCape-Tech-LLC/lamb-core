BEGIN TRANSACTION;

set ext.params to :params;

DROP TYPE IF EXISTS lamb_p_params_type CASCADE;
CREATE TYPE lamb_p_params_type AS
(
    p_table_name           text,
    partitioning_feature   text,
    table_life_month_count int,
    action_with_partitions text
);

DROP TYPE IF EXISTS lamb_p_fk_data_type CASCADE;
CREATE TYPE lamb_p_fk_data_type AS
(
    f_table_name      text,
    fk_columns        text[],
    pk_columns        text[],
    f_constraint_name text
);

DROP TYPE IF EXISTS lamb_p_pk_name_and_type_type CASCADE;
CREATE TYPE lamb_p_pk_name_and_type_type AS
(
    pk_name text,
    pk_type text
);

DROP FUNCTION IF EXISTS lamb_p_get_db_owner;
CREATE OR REPLACE FUNCTION lamb_p_get_db_owner() returns text as
$$
declare
    result text;
begin
    SELECT u.usename
    into result
    FROM pg_database d
             JOIN pg_user u ON (d.datdba = u.usesysid)
    WHERE d.datname = (SELECT current_database());

    RETURN result;
end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_parse_params;
CREATE OR REPLACE FUNCTION lamb_p_parse_params(params_string text) returns lamb_p_params_type[] as
$$
declare
    elem   lamb_p_params_type;
    result lamb_p_params_type[];
    idx    int := 1;
    data   text[];
begin
    data := string_to_array(params_string, ',');
    while idx < array_length(data, 1)
        loop
            elem.p_table_name := data[idx];
            elem.partitioning_feature := data[idx + 1];
            elem.table_life_month_count := data[idx + 2]::int;
            elem.action_with_partitions := data[idx + 3];
            result := array_append(result, elem);
            idx := idx + 4;
        end loop;
    RETURN result;
end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_get_primary_keys_columns_names;
CREATE OR REPLACE FUNCTION lamb_p_get_primary_keys_columns_names(table_name text) returns text[] as
$$
declare
    result text[];
begin
    SELECT array_agg(a.attname)
    into result
    FROM pg_index i
             JOIN pg_attribute a ON a.attrelid = i.indrelid
        AND a.attnum = ANY (i.indkey)
    WHERE i.indrelid = table_name::regclass
      AND i.indisprimary;
    RETURN result;
end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_get_f_keys_columns_names;
CREATE OR REPLACE FUNCTION lamb_p_get_f_keys_columns_names(table_name text) returns text[] as
$$
declare
    result text[];
begin
    SELECT array_agg(a.attname)
    into result
    FROM pg_index i
             JOIN pg_attribute a ON a.attrelid = i.indrelid
        AND a.attnum = ANY (i.indkey)
    WHERE i.indrelid = table_name::regclass
      AND i.indisprimary;
    if result is NULL then
        result := ARRAY []::text[];
    end if;
    RETURN result;
end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_get_table_pk;
CREATE OR REPLACE FUNCTION lamb_p_get_table_pk(table_name text) returns lamb_p_pk_name_and_type_type[] as
$$
declare
    result lamb_p_pk_name_and_type_type[];
begin
    SELECT array_agg((pg_attribute.attname, format_type(atttypid, atttypmod))::lamb_p_pk_name_and_type_type)
    into result
    FROM pg_index,
         pg_class,
         pg_attribute,
         pg_namespace
    WHERE pg_class.oid = table_name::regclass
      AND indrelid = pg_class.oid
      AND nspname = 'public'
      AND pg_class.relnamespace = pg_namespace.oid
      AND pg_attribute.attrelid = pg_class.oid
      AND pg_attribute.attnum = any (pg_index.indkey)
      AND indisprimary;

    if result is NULL then
        result := ARRAY []::lamb_p_pk_name_and_type_type[];
    end if;
    RETURN result;
end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_get_table_new_pk;
CREATE OR REPLACE FUNCTION lamb_p_get_table_new_pk(table_name text, partitioning_feature text) returns text as
$$
declare
    result      lamb_p_pk_name_and_type_type[];
    pk_names    text[];
    table_pk    lamb_p_pk_name_and_type_type;
    result_text text;
    user_notice text;
begin
    result := lamb_p_get_table_pk(table_name);
    foreach table_pk in array result
        loop
            pk_names := array_append(pk_names, table_pk.pk_name);
        end loop;
    if partitioning_feature != ALL (pk_names) then
        pk_names := array_append(pk_names, partitioning_feature);
        result_text := array_to_string(pk_names, ', ');
        user_notice := 'new pk for table ' || table_name || '->(' || result_text || ')';
        raise notice '%', user_notice;
    else
        result_text := array_to_string(pk_names, ', ');
    end if;
    RETURN result_text;
end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_get_table_source;
CREATE OR REPLACE FUNCTION lamb_p_get_table_source(table_name text, partitioning_feature text) returns text as
$$
declare
    result text;
begin
    select string_agg(quote_ident(attname) || ' ' ||
                      format_type(atttypid, atttypmod) ||
                      case when attnotnull then ' NOT NULL ' else '' end ||
                      case
                          when atthasdef then ' DEFAULT ' ||
                                              (select pg_get_expr(adbin, attrelid)
                                               from pg_attrdef
                                               where adrelid = attrelid
                                                 and adnum = attnum)::text
                          else ''
                          end ||
                      case
                          when nullif(confrelid, 0) is not null
                              then ' references ' || confrelid::regclass::text || '( ' ||
                                   array_to_string(ARRAY(select quote_ident(fa.attname)
                                                         from pg_attribute as fa
                                                         where fa.attnum = ANY (confkey)
                                                           and fa.attrelid = confrelid
                                                         order by fa.attnum
                                                       ), ','
                                       ) || ' )'
                                       || case
                                              when pg_constraint.confupdtype = 'a' THEN ' on update no action'
                                              when pg_constraint.confupdtype = 'r' THEN ' on update restrict'
                                              when pg_constraint.confupdtype = 'c' THEN ' on update cascade'
                                              when pg_constraint.confupdtype = 'n' THEN ' on update set null'
                                              when pg_constraint.confupdtype = 'd' THEN ' on update set default'
                                       end || case
                                                  when pg_constraint.confdeltype = 'a' THEN ' on delete no action'
                                                  when pg_constraint.confdeltype = 'r' THEN ' on delete restrict'
                                                  when pg_constraint.confdeltype = 'c' THEN ' on delete cascade'
                                                  when pg_constraint.confdeltype = 'n' THEN ' on delete set null'
                                                  when pg_constraint.confdeltype = 'd' THEN ' on delete set default'
                                       end
                          else '' end, ', ')
    into result
    from pg_attribute
             left outer join pg_constraint on conrelid = attrelid
        and attnum = conkey[1]
        and array_upper(conkey, 1) = 1,
         pg_class,
         pg_namespace
    where pg_class.oid = attrelid
      and pg_namespace.oid = relnamespace
      and pg_class.oid = btrim(table_name)::regclass::oid
      and attnum > 0
      and not attisdropped;

    -- add primary key note
    result := result || ', primary key (' || lamb_p_get_table_new_pk(table_name, partitioning_feature) || ')';
    RETURN result;
end
$$ LANGUAGE plpgsql;



DROP FUNCTION IF EXISTS lamb_p_create_partitioning_table;
CREATE OR REPLACE FUNCTION lamb_p_create_partitioning_table(p_table_name text, db_owner text, partitioning_feature text) returns void as
$$
begin
    execute 'CREATE TABLE ' || p_table_name || '
                (' || lamb_p_get_table_source(p_table_name || '_old', partitioning_feature) ||
            ') partition by range (' || partitioning_feature || ')';

    execute 'alter table ' || p_table_name ||
            ' owner to ' || db_owner;

end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_get_value_from;
CREATE OR REPLACE FUNCTION lamb_p_get_value_from(year int, month int) returns text AS
$$
begin
    RETURN year || '-' || lpad(cast(month as text), 2, '0') || '-01';
end;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_get_value_to;
CREATE OR REPLACE FUNCTION lamb_p_get_value_to(year int, month int) returns text AS
$$
begin
    month := month + 1;
    if month = 13 then
        month := 1;
        year := year + 1;
    end if;
    RETURN year || '-' || lpad(cast(month as text), 2, '0') || '-01';
end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_create_table_partitions;
CREATE OR REPLACE FUNCTION lamb_p_create_table_partitions(p_table_name text, min_date date, db_owner text) returns void AS
$$
declare
    year         int;
    month        int;
    finish_year  int;
    finish_month int;
    table_name   text;
    value_from   text;
    value_to     text;
begin
    finish_year := EXTRACT(year from current_date) :: int;
    finish_month := EXTRACT(month from current_date) + 2 :: int;
    if finish_month > 12 then
        finish_year := finish_year + 1;
        finish_month := mod(finish_month, 12);
    end if;
    year := EXTRACT(year from min_date) :: int;
    month := EXTRACT(month from min_date) :: int;
    while year < finish_year or month < finish_month
        loop
            table_name := p_table_name || '_y' || year || 'm' || lpad(cast(month as text), 2, '0');
            value_from := lamb_p_get_value_from(year, month);
            value_to := lamb_p_get_value_to(year, month);
            execute format('
                CREATE TABLE if not exists ' || table_name || ' PARTITION OF ' || p_table_name ||
                           ' FOR VALUES FROM (%L) TO (%L)', value_from, value_to);
            execute 'alter table ' || table_name ||
                    ' owner to ' || db_owner;
            month := month + 1;
            if month > 12 then
                month := 1;
                year := year + 1;
            end if;
        end loop;
end
$$ LANGUAGE plpgsql;



DROP FUNCTION IF EXISTS lamb_p_get_pk_diff;
CREATE OR REPLACE FUNCTION lamb_p_get_pk_diff(p_table_name text) returns lamb_p_pk_name_and_type_type[] AS
$$
declare
    result                    lamb_p_pk_name_and_type_type[];
    table_pk                  lamb_p_pk_name_and_type_type;
    p_table_name_old_pk_names text[];
begin
    foreach table_pk in array lamb_p_get_table_pk(p_table_name || '_old')
        loop
            p_table_name_old_pk_names := array_append(p_table_name_old_pk_names, table_pk.pk_name);
        end loop;


    foreach table_pk in array lamb_p_get_table_pk(p_table_name)
        loop
            if table_pk.pk_name != ALL (p_table_name_old_pk_names) then
                result := array_append(result, table_pk);
            end if;
        end loop;
    RETURN result;
end
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS lamb_p_get_table_fk_data;
CREATE OR REPLACE FUNCTION lamb_p_get_table_fk_data(p_table_name_old text) returns lamb_p_fk_data_type[] AS
$$
declare
    result lamb_p_fk_data_type[];
begin
    select array_agg((f_table_name, fk_columns, pk_columns, f_constraint_name)::lamb_p_fk_data_type)
    into result
    from (
             select kcu.table_name                 as f_table_name,
                    array_agg(kcu.column_name)     as fk_columns,
                    array_agg(rel_kcu.column_name) as pk_columns,
                    kcu.constraint_name            as f_constraint_name
             from information_schema.table_constraints tco
                      join information_schema.key_column_usage kcu
                           on tco.constraint_schema = kcu.constraint_schema
                               and tco.constraint_name = kcu.constraint_name
                      join information_schema.referential_constraints rco
                           on tco.constraint_schema = rco.constraint_schema
                               and tco.constraint_name = rco.constraint_name
                      join information_schema.key_column_usage rel_kcu
                           on rco.unique_constraint_schema = rel_kcu.constraint_schema
                               and rco.unique_constraint_name = rel_kcu.constraint_name
                               and kcu.ordinal_position = rel_kcu.ordinal_position
             where tco.constraint_type = 'FOREIGN KEY'
               and rel_kcu.table_name = p_table_name_old
             group by f_table_name, kcu.constraint_name) t;
    if result is NULL then
        result := ARRAY []::lamb_p_fk_data_type[];
    end if;
    RETURN result;
end
$$ LANGUAGE plpgsql;


DROP FUNCTION IF EXISTS lamb_p_fill_new_column_by_values;
CREATE OR REPLACE FUNCTION lamb_p_fill_new_column_by_values(fk_data_elem lamb_p_fk_data_type,
                                                            new_column_name text,
                                                            pk_difference_elem lamb_p_pk_name_and_type_type,
                                                            new_table_name text) returns void AS
$$
declare
    column_text text := '';
    on_text     text := '';
    where_text  text := '';
    elem        text;
    idx         int;
    exc text;
begin
    idx := 1;
    foreach elem in array fk_data_elem.pk_columns
        loop
            column_text := column_text || 't.' || fk_data_elem.fk_columns[idx] || ', ';
            if idx > 1 then
                where_text := where_text || ' AND ';
            end if;
            where_text := where_text || 'subquery.' || fk_data_elem.fk_columns[idx] || ' = ' ||
                          fk_data_elem.f_table_name || '.' || fk_data_elem.fk_columns[idx];
        end loop;
    column_text := column_text || new_table_name || '.' || pk_difference_elem.pk_name;

    idx := 1;
    foreach elem in array fk_data_elem.pk_columns
        loop
            if idx > 1 then
                on_text := on_text || ' AND ';
            end if;
            on_text := on_text || new_table_name || '.' || elem || ' = t.' || fk_data_elem.fk_columns[idx];
            idx := idx + 1;
        end loop;
    raise notice 'fill_new_column_by_values: %', 'UPDATE ' || fk_data_elem.f_table_name ||
                                                 ' SET ' || new_column_name || ' = subquery.' || pk_difference_elem.pk_name ||
                                                 ' FROM (SELECT ' || column_text ||
                                                 ' FROM ' || fk_data_elem.f_table_name || ' t ' ||
                                                 'LEFT JOIN ' || new_table_name || ' ON ' || on_text || ') AS subquery ' ||
                                                 'WHERE ' || where_text;
    EXECUTE 'UPDATE ' || fk_data_elem.f_table_name ||
            ' SET ' || new_column_name || ' = subquery.' || pk_difference_elem.pk_name ||
            ' FROM (SELECT ' || column_text ||
            ' FROM ' || fk_data_elem.f_table_name || ' t ' ||
            'LEFT JOIN ' || new_table_name || ' ON ' || on_text || ') AS subquery ' ||
            'WHERE ' || where_text;
end
$$ LANGUAGE plpgsql;



DROP FUNCTION IF EXISTS lamb_p_get_table_const_actions;
CREATE OR REPLACE FUNCTION lamb_p_get_table_const_actions(p_table_name text, con_name text) returns text AS
$$
declare
    result text;
begin
    SELECT case
               when confupdtype = 'a' THEN ' on update no action'
               when confupdtype = 'r' THEN ' on update restrict'
               when confupdtype = 'c' THEN ' on update cascade'
               when confupdtype = 'n' THEN ' on update set null'
               when confupdtype = 'd' THEN ' on update set default'
               end || case
                          when confdeltype = 'a' THEN ' on delete no action'
                          when confdeltype = 'r' THEN ' on delete restrict'
                          when confdeltype = 'c' THEN ' on delete cascade'
                          when confdeltype = 'n' THEN ' on delete set null'
                          when confdeltype = 'd' THEN ' on delete set default'
               end as tt
    into result
    FROM pg_catalog.pg_constraint con
             INNER JOIN pg_catalog.pg_class rel
                        ON rel.oid = con.conrelid
             INNER JOIN pg_catalog.pg_namespace nsp
                        ON nsp.oid = connamespace
    WHERE rel.relname = p_table_name
      and conname = con_name;

    return result;
end
$$ LANGUAGE plpgsql;


DROP FUNCTION IF EXISTS lamb_p_switch_old_table_fk;
CREATE OR REPLACE FUNCTION lamb_p_switch_old_table_fk(p_table_name text,
                                                      fk_data_elem lamb_p_fk_data_type,
                                                      pk_difference lamb_p_pk_name_and_type_type[]) returns void AS
$$
declare
    elem            lamb_p_pk_name_and_type_type;
    constraint_name text := '';
    const_actions   text := '';
    pk_names        text := '';
    fk_names        text := '';
begin
    const_actions := lamb_p_get_table_const_actions(fk_data_elem.f_table_name, fk_data_elem.f_constraint_name);

    raise notice 'const_actions, %', 'alter table ' || fk_data_elem.f_table_name ||
                                     ' drop constraint ' || fk_data_elem.f_constraint_name;
    EXECUTE 'alter table ' || fk_data_elem.f_table_name ||
            ' drop constraint ' || fk_data_elem.f_constraint_name;

    constraint_name := fk_data_elem.f_table_name || '_' || array_to_string(fk_data_elem.pk_columns, '_');
    pk_names := array_to_string(fk_data_elem.pk_columns, ', ');
    fk_names := array_to_string(fk_data_elem.fk_columns, ', ');
    foreach elem in array pk_difference
        loop
            constraint_name := constraint_name || '_' || elem.pk_name;
            fk_names := fk_names || ', ' || p_table_name || '_' || elem.pk_name;
            pk_names := pk_names || ', ' || elem.pk_name;
        end loop;
    constraint_name := constraint_name || '_fkey';
    raise notice 'const_actions, %', 'alter table ' || fk_data_elem.f_table_name ||
                                     ' add constraint ' || constraint_name ||
                                     ' foreign key (' || fk_names || ') references ' || p_table_name || ' (' || pk_names || ') ' ||
                                     const_actions;
    EXECUTE 'alter table ' || fk_data_elem.f_table_name ||
            ' add constraint ' || constraint_name ||
            ' foreign key (' || fk_names || ') references ' || p_table_name || ' (' || pk_names || ') ' ||
            const_actions;


end
$$ LANGUAGE plpgsql;


DROP TYPE IF EXISTS lamb_p_seq_data_type CASCADE;
CREATE TYPE lamb_p_seq_data_type AS
(
    seq_column_name text,
    seq_name        text
);

DROP FUNCTION IF EXISTS lamb_p_switch_sequences;
CREATE OR REPLACE FUNCTION lamb_p_switch_sequences(p_table_name text, p_table_name_old text, db_owner text) returns void AS
$$
declare
    related_seqs lamb_p_seq_data_type[];
    related_seq  lamb_p_seq_data_type;
begin
    SELECT array_agg((a.attname, s.relname)::lamb_p_seq_data_type)
    into related_seqs
    FROM pg_class s
             JOIN pg_depend d ON d.objid = s.oid
             JOIN pg_class t ON d.objid = s.oid AND d.refobjid = t.oid
             JOIN pg_attribute a ON (d.refobjid, d.refobjsubid) = (a.attrelid, a.attnum)
             JOIN pg_namespace n ON n.oid = s.relnamespace
    WHERE s.relkind = 'S'
      AND n.nspname = 'public'
      AND t.relname = p_table_name_old;


    if related_seqs is not NULL then
        foreach related_seq in array related_seqs
            loop
                raise notice 'sequence: %', 'alter sequence ' || related_seq.seq_name || ' owner to ' || db_owner;
                raise notice 'sequence: %', 'ALTER SEQUENCE ' || related_seq.seq_name ||
                                            ' OWNED BY ' || p_table_name || '.' || related_seq.seq_column_name;
                execute 'alter sequence ' || related_seq.seq_name || ' owner to ' || db_owner;
                raise notice 'switch % seq', related_seq.seq_name;
                execute 'ALTER SEQUENCE ' || related_seq.seq_name ||
                        ' OWNED BY ' || p_table_name || '.' || related_seq.seq_column_name;
            end loop;
    end if;

end
$$ LANGUAGE plpgsql;

do
$do$
    declare
        params_string        text := current_setting('ext.params');
        db_owner             text;
        partitioning_feature text;
        parsed_params        lamb_p_params_type[];
        parsed_params_elem   lamb_p_params_type;
        p_table_name         text;
        new_table_name       text;
        storage_depth        int;
        partition_action     text;
        min_date             date;
        table_min_date       date;
        pk_difference        lamb_p_pk_name_and_type_type[];
        pk_difference_elem   lamb_p_pk_name_and_type_type;
        fk_data_elem         lamb_p_fk_data_type;
        new_column_name      text;
    begin
        -- parse params
        parsed_params := lamb_p_parse_params(params_string);
        raise notice 'parsed_params ok';
        -- get DB owner
        db_owner := lamb_p_get_db_owner();
        -- main loop
        FOREACH parsed_params_elem IN ARRAY parsed_params
            LOOP
                p_table_name := parsed_params_elem.p_table_name;
                raise notice 'handle %', p_table_name;
                -- rename table to table_old
                new_table_name := p_table_name || '_old';
                raise notice 'rename % to %', p_table_name, new_table_name;
                EXECUTE '
                ALTER TABLE ' || p_table_name ||
                        ' RENAME TO ' || new_table_name;

                partitioning_feature := parsed_params_elem.partitioning_feature;
                -- create partitioned table
                raise notice 'create partitioned table %', p_table_name;
                PERFORM lamb_p_create_partitioning_table(p_table_name,
                                                         db_owner,
                                                         partitioning_feature);

                -- create table partitions
                raise notice 'create table partitions';
                storage_depth := parsed_params_elem.table_life_month_count;
                partition_action := parsed_params_elem.action_with_partitions;
                execute 'select min(' || partitioning_feature || ') from ' || p_table_name || '_old' into table_min_date;
                if partition_action = 'delete' then
                    if storage_depth < 0 then
                        raise exception 'storage_depth with delete action cant be less then 0';
                    end if;
                    min_date := LEAST(table_min_date, current_date - make_interval(months := storage_depth));
                else
                    min_date := LEAST(table_min_date, current_date);
                end if;
                PERFORM lamb_p_create_table_partitions(p_table_name, min_date, db_owner);

                -- move table data from _old to partitioned table
                raise notice 'move table data from _old to partitioned table';
                execute 'insert into ' || p_table_name ||
                        ' select * from ' || new_table_name ||
                        ' where ' || partitioning_feature || ' >= ''' || min_date::timestamp || '''';

                raise notice 'update master tables';
                pk_difference := lamb_p_get_pk_diff(p_table_name);
                FOREACH fk_data_elem in array lamb_p_get_table_fk_data(new_table_name)
                    loop
                        FOREACH pk_difference_elem in array pk_difference
                            loop
                                new_column_name := p_table_name || '_' || pk_difference_elem.pk_name;
                                -- create additional column
                                raise notice 'create additional column %', new_column_name;
                                raise notice 'for table %', fk_data_elem.f_table_name;
                                EXECUTE
                                                    'ALTER TABLE ' || fk_data_elem.f_table_name ||
                                                    ' add column ' || new_column_name || ' ' ||
                                                    pk_difference_elem.pk_type;
                                -- fill column by values
                                PERFORM lamb_p_fill_new_column_by_values(fk_data_elem,
                                                                         new_column_name,
                                                                         pk_difference_elem,
                                                                         new_table_name);
                            end loop;
                        -- switch fks
                        PERFORM lamb_p_switch_old_table_fk(p_table_name, fk_data_elem, pk_difference);
                    end loop;
                -- switch sequences owner if required
                raise notice 'switch sequences owner if required';
                PERFORM lamb_p_switch_sequences(p_table_name, new_table_name, db_owner);
                -- delete _old table
                raise notice 'drop table %', new_table_name;
                execute 'DROP TABLE ' || new_table_name;
            END LOOP;
    end;
$do$;

END TRANSACTION;
