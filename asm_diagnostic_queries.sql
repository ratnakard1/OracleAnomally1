-- Oracle ASM Disk Write Error Diagnostic Queries
-- Use these queries to diagnose ORA-15032 and ORA-15096 errors
-- Connect as SYSDBA or ASM instance user

-- ============================================================================
-- 1. Check Disk Group Status
-- ============================================================================
-- Shows overall health of all disk groups
SELECT 
    name,
    state,
    type,
    total_mb,
    free_mb,
    usable_file_mb,
    offline_disks,
    compatibility,
    database_compatibility
FROM v$asm_diskgroup
ORDER BY name;

-- ============================================================================
-- 2. Check Individual Disk Status
-- ============================================================================
-- Detailed status of all disks in all disk groups
SELECT 
    dg.name AS diskgroup_name,
    d.path,
    d.name AS disk_name,
    d.state,
    d.mode_status,
    d.header_status,
    d.mount_status,
    d.total_mb,
    d.free_mb,
    d.failgroup,
    d.create_date,
    d.repair_timer
FROM v$asm_disk d
JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
ORDER BY dg.name, d.name;

-- ============================================================================
-- 3. Check Offline or Failed Disks
-- ============================================================================
-- Identifies disks that are not in NORMAL state
SELECT 
    dg.name AS diskgroup_name,
    d.path,
    d.name AS disk_name,
    d.state,
    d.header_status,
    d.mode_status,
    d.repair_timer,
    d.failgroup
FROM v$asm_disk d
JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
WHERE d.state != 'NORMAL'
ORDER BY dg.name, d.name;

-- ============================================================================
-- 4. Check Ongoing ASM Operations
-- ============================================================================
-- Shows any rebalance or other operations in progress
SELECT 
    operation,
    state,
    power,
    actual,
    sofar,
    est_work,
    est_rate,
    est_minutes
FROM v$asm_operation
ORDER BY operation;

-- ============================================================================
-- 5. Check ASM Alert Log for Recent Errors
-- ============================================================================
-- Recent alert log entries related to disk write errors
SELECT 
    message_text,
    message_level,
    message_type,
    message_timestamp
FROM v$asm_alert_history
WHERE message_timestamp >= SYSDATE - 1
AND (message_text LIKE '%ORA-15032%' 
     OR message_text LIKE '%ORA-15096%'
     OR message_text LIKE '%disk write%'
     OR message_text LIKE '%lost write%')
ORDER BY message_timestamp DESC;

-- ============================================================================
-- 6. Check Disk I/O Statistics
-- ============================================================================
-- Identifies disks with I/O errors
SELECT 
    dg.name AS diskgroup_name,
    d.name AS disk_name,
    d.reads,
    d.writes,
    d.read_errs,
    d.write_errs,
    d.read_time,
    d.write_time
FROM v$asm_disk_stat d
JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
WHERE d.read_errs > 0 OR d.write_errs > 0
ORDER BY dg.name, (d.read_errs + d.write_errs) DESC;

-- ============================================================================
-- 7. Check Disk Group Redundancy
-- ============================================================================
-- Verify redundancy levels and ensure adequate protection
SELECT 
    name,
    type,
    total_mb,
    free_mb,
    required_mirror_free_mb,
    usable_file_mb,
    offline_disks,
    voting_files
FROM v$asm_diskgroup
ORDER BY name;

-- ============================================================================
-- 8. Check Failgroup Distribution
-- ============================================================================
-- Ensure proper failgroup distribution for redundancy
SELECT 
    dg.name AS diskgroup_name,
    d.failgroup,
    COUNT(*) AS disk_count,
    SUM(d.total_mb) AS total_mb,
    SUM(d.free_mb) AS free_mb
FROM v$asm_disk d
JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
GROUP BY dg.name, d.failgroup
ORDER BY dg.name, d.failgroup;

-- ============================================================================
-- 9. Check Disk Repair Timers
-- ============================================================================
-- Disks with active repair timers (may indicate recent failures)
SELECT 
    dg.name AS diskgroup_name,
    d.name AS disk_name,
    d.path,
    d.state,
    d.repair_timer,
    d.header_status,
    d.mode_status
FROM v$asm_disk d
JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
WHERE d.repair_timer > 0
ORDER BY dg.name, d.repair_timer DESC;

-- ============================================================================
-- 10. Check ASM Instance Status
-- ============================================================================
-- Verify ASM instance is running properly
SELECT 
    instance_name,
    status,
    database_status,
    instance_role
FROM v$instance;
