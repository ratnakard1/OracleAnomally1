set pagesize 500
set linesize 220
set trimspool on
set verify off
set feedback on
set tab off

prompt
prompt =============================================================
prompt Oracle tablespace summary (permanent tablespaces)
prompt =============================================================

column tablespace_name format a30
column allocated_mb format 9999999990.00
column free_mb format 9999999990.00
column used_mb format 9999999990.00
column pct_used format 9990.00
column max_mb format 9999999990.00
column file_count format 99990
column autoext_files format 99990

with file_totals as (
  select
    tablespace_name,
    sum(bytes) / 1024 / 1024 as allocated_mb,
    sum(case when autoextensible = 'YES' then maxbytes else bytes end) / 1024 / 1024 as max_mb,
    count(*) as file_count,
    sum(case when autoextensible = 'YES' then 1 else 0 end) as autoext_files
  from dba_data_files
  group by tablespace_name
),
free_totals as (
  select
    tablespace_name,
    sum(bytes) / 1024 / 1024 as free_mb
  from dba_free_space
  group by tablespace_name
)
select
  f.tablespace_name,
  round(f.allocated_mb, 2) as allocated_mb,
  round(nvl(fr.free_mb, 0), 2) as free_mb,
  round(f.allocated_mb - nvl(fr.free_mb, 0), 2) as used_mb,
  round(
    case
      when f.allocated_mb = 0 then 0
      else ((f.allocated_mb - nvl(fr.free_mb, 0)) * 100) / f.allocated_mb
    end,
    2
  ) as pct_used,
  round(f.max_mb, 2) as max_mb,
  f.file_count,
  f.autoext_files
from file_totals f
left join free_totals fr
  on fr.tablespace_name = f.tablespace_name
order by pct_used desc, f.tablespace_name;

prompt
prompt =============================================================
prompt Oracle temp tablespace summary
prompt =============================================================

column allocated_mb format 9999999990.00
column used_mb format 9999999990.00
column free_mb format 9999999990.00
column pct_used format 9990.00

with temp_file_totals as (
  select
    tablespace_name,
    sum(bytes) / 1024 / 1024 as allocated_mb
  from dba_temp_files
  group by tablespace_name
),
temp_usage as (
  select
    tablespace_name,
    sum(bytes_used) / 1024 / 1024 as used_mb,
    sum(bytes_free) / 1024 / 1024 as free_mb
  from v$temp_space_header
  group by tablespace_name
)
select
  tf.tablespace_name,
  round(tf.allocated_mb, 2) as allocated_mb,
  round(nvl(tu.used_mb, 0), 2) as used_mb,
  round(nvl(tu.free_mb, tf.allocated_mb), 2) as free_mb,
  round(
    case
      when tf.allocated_mb = 0 then 0
      else (nvl(tu.used_mb, 0) * 100) / tf.allocated_mb
    end,
    2
  ) as pct_used
from temp_file_totals tf
left join temp_usage tu
  on tu.tablespace_name = tf.tablespace_name
order by pct_used desc, tf.tablespace_name;

prompt
prompt =============================================================
prompt Oracle datafile details
prompt =============================================================

column file_name format a90
column status format a12
column autoextensible format a5
column max_file_mb format 9999999990.00
column file_size_mb format 9999999990.00

select
  tablespace_name,
  file_id,
  file_name,
  round(bytes / 1024 / 1024, 2) as file_size_mb,
  round((case when autoextensible = 'YES' then maxbytes else bytes end) / 1024 / 1024, 2) as max_file_mb,
  autoextensible,
  status
from dba_data_files
order by tablespace_name, file_id;
