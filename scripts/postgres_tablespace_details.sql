\pset pager off
\x off

\echo
\echo =============================================================
\echo PostgreSQL tablespace summary
\echo =============================================================

select
  t.spcname as tablespace_name,
  pg_catalog.pg_get_userbyid(t.spcowner) as owner_name,
  coalesce(nullif(pg_catalog.pg_tablespace_location(t.oid), ''), '[default-location]') as location,
  pg_catalog.pg_size_pretty(pg_catalog.pg_tablespace_size(t.oid)) as tablespace_size,
  pg_catalog.pg_tablespace_size(t.oid) as tablespace_size_bytes
from pg_catalog.pg_tablespace t
order by pg_catalog.pg_tablespace_size(t.oid) desc, t.spcname;

\echo
\echo =============================================================
\echo Current database usage by tablespace
\echo =============================================================

with db_default as (
  select dattablespace
  from pg_catalog.pg_database
  where datname = current_database()
)
select
  coalesce(ts_rel.spcname, ts_db.spcname, 'pg_default') as tablespace_name,
  pg_catalog.pg_size_pretty(sum(pg_catalog.pg_total_relation_size(c.oid))) as used_size,
  sum(pg_catalog.pg_total_relation_size(c.oid)) as used_size_bytes,
  count(*) as relation_count
from pg_catalog.pg_class c
join pg_catalog.pg_namespace n
  on n.oid = c.relnamespace
cross join db_default d
left join pg_catalog.pg_tablespace ts_rel
  on ts_rel.oid = c.reltablespace
 and c.reltablespace <> 0
left join pg_catalog.pg_tablespace ts_db
  on ts_db.oid = d.dattablespace
 and c.reltablespace = 0
where c.relkind in ('r', 'm')
group by coalesce(ts_rel.spcname, ts_db.spcname, 'pg_default')
order by sum(pg_catalog.pg_total_relation_size(c.oid)) desc;
