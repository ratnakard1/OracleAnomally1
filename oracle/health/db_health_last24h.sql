-- Oracle Database health report (last N hours, default 24)
-- Output: text report spooled to current directory
--
-- Usage (SQL*Plus):
--   SQL> @db_health_last24h.sql 24 20
--        |hours_back|top_n|
--
-- Notes:
-- - Last-24h reporting is AWR based (DBA_HIST_*). Requires appropriate privileges and licensing.
-- - If AWR views are not accessible, AWR sections will show zeros / empty output.

set echo off
set feedback on
set verify off
set termout on
set pagesize 50000
set linesize 220
set trimspool on
set tab off
set long 200000
set longchunksize 200000
set serveroutput on size unlimited

whenever sqlerror continue

define hours_back = &1
define top_n      = &2

column report_ts new_value REPORT_TS noprint
select to_char(sysdate,'YYYYMMDD_HH24MISS') report_ts from dual;

column dbid new_value DBID noprint
column db_name new_value DB_NAME noprint
column db_unique_name new_value DB_UNIQUE_NAME noprint
select dbid, name db_name, db_unique_name
from v$database;

column inst_name new_value INST_NAME noprint
column host_name new_value HOST_NAME noprint
column version_full new_value VERSION_FULL noprint
select instance_name inst_name, host_name, version version_full
from v$instance;

column is_rac new_value IS_RAC noprint
select case when (select count(*) from gv$instance) > 1 then 'Y' else 'N' end is_rac
from dual;

column begin_time new_value BEGIN_TIME noprint
column end_time   new_value END_TIME noprint
select to_char(systimestamp - numtodsinterval(&&hours_back,'HOUR'),'YYYY-MM-DD HH24:MI:SS') begin_time,
       to_char(systimestamp,'YYYY-MM-DD HH24:MI:SS') end_time
from dual;

column elapsed_s new_value ELAPSED_S noprint
select greatest(1, round((to_timestamp('&&END_TIME','YYYY-MM-DD HH24:MI:SS') -
                          to_timestamp('&&BEGIN_TIME','YYYY-MM-DD HH24:MI:SS')) * 86400)) elapsed_s
from dual;

column report_file new_value REPORT_FILE noprint
select 'db_health_last24h_'||lower('&&DB_UNIQUE_NAME')||'_'||'&&REPORT_TS'||'.lst' report_file
from dual;

spool &&REPORT_FILE

prompt
prompt ====================================================================================================
prompt Oracle Database Health Report (last &&hours_back hours)
prompt ====================================================================================================
prompt Generated at : &&REPORT_TS
prompt DB           : &&DB_NAME (unique_name=&&DB_UNIQUE_NAME, dbid=&&DBID)
prompt Instance     : &&INST_NAME on &&HOST_NAME (version=&&VERSION_FULL, RAC=&&IS_RAC)
prompt Window       : &&BEGIN_TIME  ->  &&END_TIME  (elapsed_seconds=&&ELAPSED_S)
prompt Report file  : &&REPORT_FILE
prompt ====================================================================================================
prompt

prompt ## AWR SNAPSHOT WINDOW (computed)
define SNAP_BEGIN_ID = 0
define SNAP_END_ID   = 0

column snap_begin_id new_value SNAP_BEGIN_ID noprint
select nvl(min(snap_id),0) snap_begin_id
from dba_hist_snapshot
where dbid = &&DBID
  and end_interval_time >= to_timestamp('&&BEGIN_TIME','YYYY-MM-DD HH24:MI:SS');

column snap_end_id new_value SNAP_END_ID noprint
select nvl(max(snap_id),0) snap_end_id
from dba_hist_snapshot
where dbid = &&DBID
  and end_interval_time <= to_timestamp('&&END_TIME','YYYY-MM-DD HH24:MI:SS');

column awr_status format a140
select case
         when &&SNAP_END_ID = 0 or &&SNAP_BEGIN_ID = 0 then
           'AWR snapshot ids not found (or no access). AWR-based sections may be empty.'
         else
           'AWR snapshot range: ['||&&SNAP_BEGIN_ID||' .. '||&&SNAP_END_ID||']'
       end awr_status
from dual;

prompt

prompt ## DATABASE TIME / CPU (AWR time model deltas)
column db_time_s format 9999999990.99
column db_cpu_s  format 9999999990.99
column aas       format 9999990.999
column cpu_aas   format 9999990.999
with tm as (
  select stat_name,
         sum(delta_us) delta_us
  from (
    select snap_id,
           instance_number,
           stat_name,
           (value - lag(value) over (partition by instance_number, stat_name order by snap_id)) delta_us
    from dba_hist_sys_time_model
    where dbid = &&DBID
      and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
      and stat_name in ('DB time','DB CPU')
  )
  where snap_id > &&SNAP_BEGIN_ID
  group by stat_name
)
select round(nvl((select sum(delta_us) from tm where stat_name='DB time'),0)/1e6,2) db_time_s,
       round(nvl((select sum(delta_us) from tm where stat_name='DB CPU'),0)/1e6,2)  db_cpu_s,
       round((nvl((select sum(delta_us) from tm where stat_name='DB time'),0)/1e6) / &&ELAPSED_S,3) aas,
       round((nvl((select sum(delta_us) from tm where stat_name='DB CPU'),0)/1e6) / &&ELAPSED_S,3)  cpu_aas
from dual;

prompt
prompt ## HOST CPU UTILIZATION (AWR OSSTAT deltas)
column busy_cs format 9999999999990
column idle_cs format 9999999999990
column cpu_busy_pct format 990.99
with os as (
  select stat_name,
         sum(delta_val) delta_val
  from (
    select snap_id,
           instance_number,
           stat_name,
           (value - lag(value) over (partition by instance_number, stat_name order by snap_id)) delta_val
    from dba_hist_osstat
    where dbid = &&DBID
      and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
      and stat_name in ('BUSY_TIME','IDLE_TIME')
  )
  where snap_id > &&SNAP_BEGIN_ID
  group by stat_name
)
select nvl((select sum(delta_val) from os where stat_name='BUSY_TIME'),0) busy_cs,
       nvl((select sum(delta_val) from os where stat_name='IDLE_TIME'),0) idle_cs,
       case
         when nvl((select sum(delta_val) from os where stat_name='BUSY_TIME'),0) +
              nvl((select sum(delta_val) from os where stat_name='IDLE_TIME'),0) = 0 then null
         else round(
           ( nvl((select sum(delta_val) from os where stat_name='BUSY_TIME'),0) /
             ( nvl((select sum(delta_val) from os where stat_name='BUSY_TIME'),0) +
               nvl((select sum(delta_val) from os where stat_name='IDLE_TIME'),0) ) ) * 100
         , 2)
       end cpu_busy_pct
from dual;

prompt
prompt ## MEMORY (PGA/SGA) - AWR history + current parameter settings
column pga_avg_mb format 9999999990.9
column pga_max_mb format 9999999990.9
column pga_max_alloc_mb format 9999999990.9
with pga as (
  select snap_id,
         name,
         sum(value) val_bytes
  from dba_hist_pgastat
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
    and name in ('total PGA allocated','maximum PGA allocated')
  group by snap_id, name
)
select round(avg(case when name='total PGA allocated' then val_bytes end)/1024/1024,1) pga_avg_mb,
       round(max(case when name='total PGA allocated' then val_bytes end)/1024/1024,1) pga_max_mb,
       round(max(case when name='maximum PGA allocated' then val_bytes end)/1024/1024,1) pga_max_alloc_mb
from pga;

column sga_avg_mb format 9999999990.9
column sga_max_mb format 9999999990.9
with sga as (
  select snap_id,
         instance_number,
         sum(bytes) total_bytes
  from dba_hist_sgastat
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
  group by snap_id, instance_number
),
sgat as (
  select snap_id, sum(total_bytes) total_bytes
  from sga
  group by snap_id
)
select round(avg(total_bytes)/1024/1024,1) sga_avg_mb,
       round(max(total_bytes)/1024/1024,1) sga_max_mb
from sgat;

prompt
column name format a35
column value format a35
select name, value
from v$parameter
where name in (
  'memory_target','memory_max_target',
  'sga_target','sga_max_size',
  'pga_aggregate_target','pga_aggregate_limit',
  'db_cache_size','shared_pool_size','large_pool_size','java_pool_size','streams_pool_size','inmemory_size',
  'use_large_pages'
)
order by name;

prompt
prompt ## WORKLOAD SUMMARY (executions, transactions, parses)
column executes_total format 9999999999990
column commits_total  format 9999999999990
column rollbacks_total format 9999999999990
column tx_total       format 9999999999990
column tx_per_s       format 9999990.999
column parses_total   format 9999999999990
column hard_parses_total format 9999999999990
with st as (
  select stat_name,
         sum(delta_val) delta_val
  from (
    select snap_id,
           instance_number,
           stat_name,
           (value - lag(value) over (partition by instance_number, stat_name order by snap_id)) delta_val
    from dba_hist_sysstat
    where dbid = &&DBID
      and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
      and stat_name in (
        'execute count',
        'user commits','user rollbacks',
        'parse count (total)','parse count (hard)'
      )
  )
  where snap_id > &&SNAP_BEGIN_ID
  group by stat_name
)
select nvl((select sum(delta_val) from st where stat_name='execute count'),0) executes_total,
       nvl((select sum(delta_val) from st where stat_name='user commits'),0) commits_total,
       nvl((select sum(delta_val) from st where stat_name='user rollbacks'),0) rollbacks_total,
       nvl((select sum(delta_val) from st where stat_name='user commits'),0) +
       nvl((select sum(delta_val) from st where stat_name='user rollbacks'),0) tx_total,
       round( ( nvl((select sum(delta_val) from st where stat_name='user commits'),0) +
                nvl((select sum(delta_val) from st where stat_name='user rollbacks'),0) ) / &&ELAPSED_S, 3) tx_per_s,
       nvl((select sum(delta_val) from st where stat_name='parse count (total)'),0) parses_total,
       nvl((select sum(delta_val) from st where stat_name='parse count (hard)'),0) hard_parses_total
from dual;

prompt
prompt ## CACHE EFFICIENCY (buffer cache / logical & physical reads)
column logical_reads format 9999999999990
column physical_reads format 9999999999990
column buf_hit_pct format 990.99
column logical_reads_s format 9999999990.99
column physical_reads_s format 9999999990.99
with st as (
  select stat_name,
         sum(delta_val) delta_val
  from (
    select snap_id,
           instance_number,
           stat_name,
           (value - lag(value) over (partition by instance_number, stat_name order by snap_id)) delta_val
    from dba_hist_sysstat
    where dbid = &&DBID
      and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
      and stat_name in ('db block gets','consistent gets','physical reads')
  )
  where snap_id > &&SNAP_BEGIN_ID
  group by stat_name
),
calc as (
  select ( nvl((select sum(delta_val) from st where stat_name='db block gets'),0) +
           nvl((select sum(delta_val) from st where stat_name='consistent gets'),0) ) logical_reads,
         nvl((select sum(delta_val) from st where stat_name='physical reads'),0) physical_reads
  from dual
)
select logical_reads,
       physical_reads,
       case when logical_reads = 0 then null
            else round( (1 - (physical_reads / logical_reads)) * 100, 2) end buf_hit_pct,
       round(logical_reads / &&ELAPSED_S, 2) logical_reads_s,
       round(physical_reads / &&ELAPSED_S, 2) physical_reads_s
from calc;

prompt
prompt ## SHARED POOL (library cache + row cache summary)
column namespace format a25
column gets format 9999999999990
column gethits format 9999999999990
column pins format 9999999999990
column pinhits format 9999999999990
column get_hit_pct format 990.99
column pin_hit_pct format 990.99
select namespace,
       sum(gets) gets,
       sum(gethits) gethits,
       sum(pins) pins,
       sum(pinhits) pinhits,
       case when sum(gets)=0 then null else round(sum(gethits)/sum(gets)*100,2) end get_hit_pct,
       case when sum(pins)=0 then null else round(sum(pinhits)/sum(pins)*100,2) end pin_hit_pct
from dba_hist_librarycache
where dbid = &&DBID
  and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
group by namespace
order by namespace;

column parameter format a35
column gets format 9999999999990
column getmisses format 9999999999990
column scans format 9999999999990
column scanmisses format 9999999999990
column rowcache_hit_pct format 990.99
select parameter,
       sum(gets) gets,
       sum(getmisses) getmisses,
       sum(scans) scans,
       sum(scanmisses) scanmisses,
       case when sum(gets)=0 then null else round((sum(gets)-sum(getmisses))/sum(gets)*100,2) end rowcache_hit_pct
from dba_hist_rowcache_summary
where dbid = &&DBID
  and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
group by parameter
order by rowcache_hit_pct asc nulls last;

prompt
prompt ## TOP WAIT EVENTS (non-idle) by time waited
column wait_class format a15
column event_name format a45
column waits format 9999999999990
column time_waited_s format 9999999990.99
column avg_wait_ms format 9999990.999
with base as (
  select snap_id,
         instance_number,
         event_name,
         (total_waits - lag(total_waits) over (partition by instance_number, event_name order by snap_id)) total_waits_delta,
         (time_waited_micro - lag(time_waited_micro) over (partition by instance_number, event_name order by snap_id)) time_waited_micro_delta
  from dba_hist_system_event
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
),
agg as (
  select b.event_name,
         nvl(e.wait_class,'Unknown') wait_class,
         sum(nvl(b.total_waits_delta,0)) waits,
         sum(nvl(b.time_waited_micro_delta,0)) time_waited_micro
  from base b
  left join dba_hist_event_name e
    on e.dbid = &&DBID
   and e.event_name = b.event_name
  where b.snap_id > &&SNAP_BEGIN_ID
  group by b.event_name, nvl(e.wait_class,'Unknown')
)
select *
from (
  select wait_class,
         event_name,
         waits,
         round(time_waited_micro/1e6,2) time_waited_s,
         case when waits=0 then null else round((time_waited_micro/1e3)/waits,3) end avg_wait_ms
  from agg
  where wait_class <> 'Idle'
    and waits > 0
  order by time_waited_micro desc
)
where rownum <= &&top_n;

prompt
prompt ## I/O PERFORMANCE (AWR sysstat deltas)
column read_iops format 9999999990.99
column write_iops format 9999999990.99
column read_mb_s format 99999990.99
column write_mb_s format 99999990.99
column avg_read_kb format 9999990.99
column avg_write_kb format 9999990.99
with st as (
  select stat_name,
         sum(delta_val) delta_val
  from (
    select snap_id,
           instance_number,
           stat_name,
           (value - lag(value) over (partition by instance_number, stat_name order by snap_id)) delta_val
    from dba_hist_sysstat
    where dbid = &&DBID
      and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
      and stat_name in (
        'physical read total IO requests',
        'physical write total IO requests',
        'physical read total bytes',
        'physical write total bytes'
      )
  )
  where snap_id > &&SNAP_BEGIN_ID
  group by stat_name
),
calc as (
  select nvl((select sum(delta_val) from st where stat_name='physical read total IO requests'),0)  read_ios,
         nvl((select sum(delta_val) from st where stat_name='physical write total IO requests'),0) write_ios,
         nvl((select sum(delta_val) from st where stat_name='physical read total bytes'),0)        read_bytes,
         nvl((select sum(delta_val) from st where stat_name='physical write total bytes'),0)       write_bytes
  from dual
)
select round(read_ios/&&ELAPSED_S,2)  read_iops,
       round(write_ios/&&ELAPSED_S,2) write_iops,
       round((read_bytes/1024/1024)/&&ELAPSED_S,2)  read_mb_s,
       round((write_bytes/1024/1024)/&&ELAPSED_S,2) write_mb_s,
       case when read_ios=0 then null else round((read_bytes/read_ios)/1024,2) end avg_read_kb,
       case when write_ios=0 then null else round((write_bytes/write_ios)/1024,2) end avg_write_kb
from calc;

prompt
prompt ## COMMIT / REDO PERFORMANCE
column redo_mb format 9999999990.99
column redo_mb_s format 99999990.99
with st as (
  select stat_name,
         sum(delta_val) delta_val
  from (
    select snap_id,
           instance_number,
           stat_name,
           (value - lag(value) over (partition by instance_number, stat_name order by snap_id)) delta_val
    from dba_hist_sysstat
    where dbid = &&DBID
      and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
      and stat_name in ('redo size','user commits')
  )
  where snap_id > &&SNAP_BEGIN_ID
  group by stat_name
)
select round(nvl((select sum(delta_val) from st where stat_name='redo size'),0)/1024/1024,2) redo_mb,
       round((nvl((select sum(delta_val) from st where stat_name='redo size'),0)/1024/1024)/&&ELAPSED_S,2) redo_mb_s,
       nvl((select sum(delta_val) from st where stat_name='user commits'),0) commits
from dual;

prompt
prompt -- log file sync / log file parallel write (average wait ms)
column event_name format a30
with base as (
  select snap_id,
         instance_number,
         event_name,
         (total_waits - lag(total_waits) over (partition by instance_number, event_name order by snap_id)) total_waits_delta,
         (time_waited_micro - lag(time_waited_micro) over (partition by instance_number, event_name order by snap_id)) time_waited_micro_delta
  from dba_hist_system_event
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
    and event_name in ('log file sync','log file parallel write','log buffer space')
),
agg as (
  select event_name,
         sum(nvl(total_waits_delta,0)) waits,
         sum(nvl(time_waited_micro_delta,0)) time_waited_micro
  from base
  where snap_id > &&SNAP_BEGIN_ID
  group by event_name
)
select event_name,
       waits,
       round(time_waited_micro/1e6,2) time_waited_s,
       case when waits=0 then null else round((time_waited_micro/1e3)/waits,3) end avg_wait_ms
from agg
order by time_waited_micro desc;

prompt
prompt ## NETWORK LATENCY (wait class = Network)
with base as (
  select snap_id,
         instance_number,
         event_name,
         (total_waits - lag(total_waits) over (partition by instance_number, event_name order by snap_id)) total_waits_delta,
         (time_waited_micro - lag(time_waited_micro) over (partition by instance_number, event_name order by snap_id)) time_waited_micro_delta
  from dba_hist_system_event
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
),
agg as (
  select b.event_name,
         nvl(e.wait_class,'Unknown') wait_class,
         sum(nvl(b.total_waits_delta,0)) waits,
         sum(nvl(b.time_waited_micro_delta,0)) time_waited_micro
  from base b
  left join dba_hist_event_name e
    on e.dbid = &&DBID
   and e.event_name = b.event_name
  where b.snap_id > &&SNAP_BEGIN_ID
  group by b.event_name, nvl(e.wait_class,'Unknown')
)
select *
from (
  select event_name,
         waits,
         round(time_waited_micro/1e6,2) time_waited_s,
         case when waits=0 then null else round((time_waited_micro/1e3)/waits,3) end avg_wait_ms
  from agg
  where wait_class = 'Network'
    and waits > 0
  order by time_waited_micro desc
)
where rownum <= &&top_n;

prompt
prompt ## RAC / INTERCONNECT (cluster) - wait events
prompt (If RAC=N, this section is expected to be empty.)
with base as (
  select snap_id,
         instance_number,
         event_name,
         (total_waits - lag(total_waits) over (partition by instance_number, event_name order by snap_id)) total_waits_delta,
         (time_waited_micro - lag(time_waited_micro) over (partition by instance_number, event_name order by snap_id)) time_waited_micro_delta
  from dba_hist_system_event
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
),
agg as (
  select b.event_name,
         nvl(e.wait_class,'Unknown') wait_class,
         sum(nvl(b.total_waits_delta,0)) waits,
         sum(nvl(b.time_waited_micro_delta,0)) time_waited_micro
  from base b
  left join dba_hist_event_name e
    on e.dbid = &&DBID
   and e.event_name = b.event_name
  where b.snap_id > &&SNAP_BEGIN_ID
  group by b.event_name, nvl(e.wait_class,'Unknown')
)
select *
from (
  select wait_class,
         event_name,
         waits,
         round(time_waited_micro/1e6,2) time_waited_s,
         case when waits=0 then null else round((time_waited_micro/1e3)/waits,3) end avg_wait_ms
  from agg
  where (wait_class = 'Cluster' or event_name like 'gc%')
    and waits > 0
  order by time_waited_micro desc
)
where rownum <= &&top_n;

prompt
prompt ## REDO LOG / LOG BUFFER CONFIGURATION (current)
column name format a35
column value format a45
select name, value
from v$parameter
where name in (
  'log_buffer',
  'disk_asynch_io','filesystemio_options',
  'fast_start_mttr_target',
  'log_checkpoint_timeout','log_checkpoint_interval'
)
order by name;

prompt
column group# format 9990
column thread# format 9990
column mb format 9999990.9
column members format 990
column status format a12
column archived format a8
select l.group#, l.thread#, round(l.bytes/1024/1024,1) mb, l.members, l.status, l.archived
from v$log l
order by l.thread#, l.group#;

column member format a90
column type format a10
column is_recovery_dest_file format a5
select lf.group#, lf.type, lf.is_recovery_dest_file, lf.member
from v$logfile lf
order by lf.group#, lf.member;

prompt
prompt ## LOG SWITCHES (per hour) in report window
column hour format a16
column switches format 9999990
select to_char(first_time,'YYYY-MM-DD HH24') hour,
       count(*) switches
from v$log_history
where first_time >= to_timestamp('&&BEGIN_TIME','YYYY-MM-DD HH24:MI:SS')
  and first_time <= to_timestamp('&&END_TIME','YYYY-MM-DD HH24:MI:SS')
group by to_char(first_time,'YYYY-MM-DD HH24')
order by hour;

prompt
prompt ## TOP SQL BY ELAPSED TIME (AWR SQLSTAT)
column sql_id format a13
column plan_hash format 9999999999
column execs format 9999999990
column elapsed_s format 9999999990.99
column cpu_s format 9999999990.99
column ela_per_exec_s format 9999990.9999
column cpu_per_exec_s format 9999990.9999
column buffer_gets format 9999999999990
column disk_reads format 9999999999990
column sql_text format a120
with s as (
  select sql_id,
         plan_hash_value,
         sum(executions_delta) execs,
         sum(elapsed_time_delta)/1e6 elapsed_s,
         sum(cpu_time_delta)/1e6 cpu_s,
         sum(buffer_gets_delta) buffer_gets,
         sum(disk_reads_delta) disk_reads
  from dba_hist_sqlstat
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
    and snap_id > &&SNAP_BEGIN_ID
  group by sql_id, plan_hash_value
),
t as (
  select sql_id,
         replace(replace(dbms_lob.substr(sql_text, 120, 1), chr(10), ' '), chr(13), ' ') sql_text
  from dba_hist_sqltext
  where dbid = &&DBID
)
select *
from (
  select s.sql_id,
         s.plan_hash_value plan_hash,
         s.execs,
         round(s.elapsed_s,2) elapsed_s,
         round(s.cpu_s,2) cpu_s,
         case when s.execs=0 then null else round(s.elapsed_s/s.execs,4) end ela_per_exec_s,
         case when s.execs=0 then null else round(s.cpu_s/s.execs,4) end cpu_per_exec_s,
         s.buffer_gets,
         s.disk_reads,
         t.sql_text
  from s
  left join t on t.sql_id = s.sql_id
  order by s.elapsed_s desc
)
where rownum <= &&top_n;

prompt
prompt ## TOP SQL BY CPU (AWR SQLSTAT)
with s as (
  select sql_id,
         plan_hash_value,
         sum(executions_delta) execs,
         sum(elapsed_time_delta)/1e6 elapsed_s,
         sum(cpu_time_delta)/1e6 cpu_s,
         sum(buffer_gets_delta) buffer_gets,
         sum(disk_reads_delta) disk_reads
  from dba_hist_sqlstat
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
    and snap_id > &&SNAP_BEGIN_ID
  group by sql_id, plan_hash_value
),
t as (
  select sql_id,
         replace(replace(dbms_lob.substr(sql_text, 120, 1), chr(10), ' '), chr(13), ' ') sql_text
  from dba_hist_sqltext
  where dbid = &&DBID
)
select *
from (
  select s.sql_id,
         s.plan_hash_value plan_hash,
         s.execs,
         round(s.cpu_s,2) cpu_s,
         round(s.elapsed_s,2) elapsed_s,
         case when s.execs=0 then null else round(s.cpu_s/s.execs,4) end cpu_per_exec_s,
         s.buffer_gets,
         s.disk_reads,
         t.sql_text
  from s
  left join t on t.sql_id = s.sql_id
  order by s.cpu_s desc
)
where rownum <= &&top_n;

prompt
prompt ## SQL SUMMARY (Top by elapsed: includes wait breakdown)
column iowait_s format 9999999990.99
column clwait_s format 9999999990.99
column apwait_s format 9999999990.99
column ccwait_s format 9999999990.99
with s as (
  select sql_id,
         plan_hash_value,
         sum(executions_delta) execs,
         sum(elapsed_time_delta)/1e6 elapsed_s,
         sum(cpu_time_delta)/1e6 cpu_s,
         sum(iowait_delta)/1e6 iowait_s,
         sum(clwait_delta)/1e6 clwait_s,
         sum(apwait_delta)/1e6 apwait_s,
         sum(ccwait_delta)/1e6 ccwait_s,
         sum(buffer_gets_delta) buffer_gets,
         sum(disk_reads_delta) disk_reads,
         sum(rows_processed_delta) rows_proc
  from dba_hist_sqlstat
  where dbid = &&DBID
    and snap_id between &&SNAP_BEGIN_ID and &&SNAP_END_ID
    and snap_id > &&SNAP_BEGIN_ID
  group by sql_id, plan_hash_value
),
t as (
  select sql_id,
         replace(replace(dbms_lob.substr(sql_text, 120, 1), chr(10), ' '), chr(13), ' ') sql_text
  from dba_hist_sqltext
  where dbid = &&DBID
)
select *
from (
  select s.sql_id,
         s.plan_hash_value plan_hash,
         s.execs,
         round(s.elapsed_s,2) elapsed_s,
         round(s.cpu_s,2) cpu_s,
         round(s.iowait_s,2) iowait_s,
         round(s.clwait_s,2) clwait_s,
         round(s.apwait_s,2) apwait_s,
         round(s.ccwait_s,2) ccwait_s,
         s.buffer_gets,
         s.disk_reads,
         s.rows_proc,
         t.sql_text
  from s
  left join t on t.sql_id = s.sql_id
  order by s.elapsed_s desc
)
where rownum <= &&top_n;

prompt
prompt ====================================================================================================
prompt End of report.
prompt ====================================================================================================

spool off

undefine 1
undefine 2
undefine hours_back
undefine top_n
undefine REPORT_TS
undefine REPORT_FILE
undefine BEGIN_TIME
undefine END_TIME
undefine ELAPSED_S
undefine DBID
undefine DB_NAME
undefine DB_UNIQUE_NAME
undefine INST_NAME
undefine HOST_NAME
undefine VERSION_FULL
undefine IS_RAC
undefine SNAP_BEGIN_ID
undefine SNAP_END_ID
