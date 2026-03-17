-- Create Application User Script
-- Run as SYSDBA after database creation
-- Customize username, password, and default tablespace

-- Replace placeholders:
--   <APP_USER>     - Application username
--   <APP_PASSWORD> - Application password
--   <TABLESPACE>   - Default tablespace (e.g. USERS or app_data)

CREATE USER <APP_USER> IDENTIFIED BY <APP_PASSWORD>
  DEFAULT TABLESPACE <TABLESPACE>
  TEMPORARY TABLESPACE temp
  QUOTA UNLIMITED ON <TABLESPACE>;

GRANT CONNECT, RESOURCE TO <APP_USER>;
GRANT CREATE VIEW TO <APP_USER>;
GRANT CREATE SEQUENCE TO <APP_USER>;

-- For more privileges (uncomment as needed):
-- GRANT CREATE PROCEDURE TO <APP_USER>;
-- GRANT CREATE TRIGGER TO <APP_USER>;
-- GRANT CREATE TABLE TO <APP_USER>;
