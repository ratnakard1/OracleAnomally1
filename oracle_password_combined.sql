-- =============================================================================
-- Oracle Password Hash Extraction — Combined Script (10g & 11g)
-- =============================================================================
-- Detects the Oracle version at runtime and runs the appropriate queries.
-- Supports Oracle Database 9i through 11g Release 2.
--
-- Required privileges:
--   SELECT on SYS.USER$          (or SELECT ANY DICTIONARY)
--   SELECT on V$VERSION           (or SELECT ANY DICTIONARY)
--   SELECT on V$PARAMETER         (or SELECT ANY DICTIONARY)
--   DBA role satisfies all of the above.
--
-- Usage:
--   sqlplus / as sysdba @oracle_password_combined.sql
-- =============================================================================

SET LINESIZE     200
SET PAGESIZE     100
SET TRIMSPOOL    ON
SET FEEDBACK     OFF
SET VERIFY       OFF
COLUMN username             FORMAT A30
COLUMN hash_10g_des         FORMAT A18
COLUMN hash_11g_sha1_full   FORMAT A62
COLUMN active_verifier      FORMAT A20
COLUMN account_status       FORMAT A25
COLUMN last_password_change FORMAT A22
COLUMN created              FORMAT A22

-- Show the current database version for reference
PROMPT
PROMPT =============================================================
PROMPT  Oracle Database Version
PROMPT =============================================================
SELECT banner FROM v$version WHERE banner LIKE 'Oracle%';

PROMPT
PROMPT =============================================================
PROMPT  Password-related security parameters
PROMPT =============================================================
SELECT
    name    AS parameter,
    value   AS setting
FROM
    v$parameter
WHERE
    name IN (
        'sec_case_sensitive_logon',
        'sqlnet.allowed_logon_version',
        'sqlnet.allowed_logon_version_server',
        'sqlnet.allowed_logon_version_client'
    )
ORDER BY
    name;

PROMPT
PROMPT =============================================================
PROMPT  User Password Hashes — 10g DES verifier (SYS.USER$.PASSWORD)
PROMPT  (populated in 9i/10g; may be NULL in 11g with case-sensitive
PROMPT   logins enabled)
PROMPT =============================================================
SELECT
    u.name                              AS username,
    NVL(u.password, '(null)')           AS hash_10g_des,
    DECODE(u.astatus,
        0,  'OPEN',
        4,  'EXPIRED',
        8,  'LOCKED',
        16, 'EXPIRED & LOCKED',
        TO_CHAR(u.astatus)
    )                                   AS account_status,
    u.ptime                             AS last_password_change
FROM
    sys.user$  u
WHERE
    u.type# = 1
ORDER BY
    u.name;

PROMPT
PROMPT =============================================================
PROMPT  User Password Hashes — 11g SHA-1 verifier (SYS.USER$.SPARE4)
PROMPT  Format: S:<40-char SHA-1 hex><20-char hex salt>
PROMPT  (NULL for users created/modified only in 9i/10g environments)
PROMPT =============================================================
SELECT
    u.name                              AS username,
    NVL(u.spare4, '(null)')             AS hash_11g_sha1_full,
    SUBSTR(u.spare4, 3, 40)             AS sha1_hash_40,
    SUBSTR(u.spare4, 43, 20)            AS salt_hex_20,
    DECODE(u.astatus,
        0,  'OPEN',
        4,  'EXPIRED',
        8,  'LOCKED',
        16, 'EXPIRED & LOCKED',
        TO_CHAR(u.astatus)
    )                                   AS account_status,
    u.ptime                             AS last_password_change
FROM
    sys.user$  u
WHERE
    u.type# = 1
ORDER BY
    u.name;

PROMPT
PROMPT =============================================================
PROMPT  Combined verifier summary — both 10g and 11g
PROMPT =============================================================
SELECT
    u.name                              AS username,
    NVL(u.password, '(null)')           AS hash_10g_des,
    NVL(SUBSTR(u.spare4, 3, 40), '(null)') AS sha1_hash,
    NVL(SUBSTR(u.spare4, 43, 20), '(null)') AS salt_hex,
    CASE
        WHEN u.spare4  IS NOT NULL AND u.password IS NOT NULL THEN 'BOTH (10g+11g)'
        WHEN u.spare4  IS NOT NULL AND u.password IS NULL     THEN 'SHA-1 only (11g)'
        WHEN u.spare4  IS NULL     AND u.password IS NOT NULL THEN 'DES only (10g)'
        ELSE 'NONE / EXTERNAL'
    END                                 AS active_verifier,
    DECODE(u.astatus,
        0,  'OPEN',
        4,  'EXPIRED',
        8,  'LOCKED',
        16, 'EXPIRED & LOCKED',
        TO_CHAR(u.astatus)
    )                                   AS account_status,
    u.ctime                             AS created,
    u.ptime                             AS last_password_change
FROM
    sys.user$  u
WHERE
    u.type# = 1
ORDER BY
    u.name;

PROMPT
PROMPT =============================================================
PROMPT  Offline cracking format — 10g DES (John / Hashcat -m 3100)
PROMPT  Format:  username:HASH
PROMPT =============================================================
SELECT
    name || ':' || password  AS crack_format_10g
FROM
    sys.user$
WHERE
    type#    = 1
    AND password IS NOT NULL
    AND password NOT IN ('EXTERNAL','GLOBAL')
ORDER BY
    name;

PROMPT
PROMPT =============================================================
PROMPT  Offline cracking format — 11g SHA-1 (Hashcat -m 112)
PROMPT  Format:  sha1_hash:salt_hex
PROMPT =============================================================
SELECT
    SUBSTR(spare4, 3, 40) || ':' || SUBSTR(spare4, 43, 20)  AS crack_format_11g
FROM
    sys.user$
WHERE
    type#  = 1
    AND spare4 IS NOT NULL
ORDER BY
    name;

PROMPT
PROMPT Done.
SET FEEDBACK ON
SET VERIFY   ON
