-- Post-Database Creation Script
-- Run after 01_create_database.sql completes successfully
-- Creates data dictionary views and optional components

-- Run catalog scripts (required for data dictionary)
@?/rdbms/admin/catalog.sql
@?/rdbms/admin/catproc.sql

-- Run Java and other optional components (uncomment if needed)
-- @?/javavm/install/initjvm.sql
-- @?/rdbms/admin/catjava.sql

-- Run PL/SQL packages
@?/rdbms/admin/utlrp.sql

-- Create additional tablespaces (optional - customize as needed)
-- CREATE TABLESPACE app_data
--   DATAFILE '<ORACLE_BASE>/oradata/<SID>/app_data01.dbf' SIZE 100M
--   AUTOEXTEND ON NEXT 10M MAXSIZE UNLIMITED;

-- CREATE TABLESPACE app_idx
--   DATAFILE '<ORACLE_BASE>/oradata/<SID>/app_idx01.dbf' SIZE 50M
--   AUTOEXTEND ON NEXT 10M MAXSIZE UNLIMITED;
