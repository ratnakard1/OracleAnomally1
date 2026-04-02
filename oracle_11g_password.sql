-- =============================================================================
-- Oracle 11g Password Hash Extraction Script
-- =============================================================================
-- Oracle 11g introduced a stronger SHA-1 based verifier (S: verifier) stored
-- in SYS.USER$.SPARE4 in addition to retaining the legacy 10g DES verifier in
-- SYS.USER$.PASSWORD (if SEC_CASE_SENSITIVE_LOGON = TRUE is in effect, the
-- 10g verifier may be NULL or disabled).
--
-- The SPARE4 column format:
--   S:<40-char SHA-1 hex hash><20-char hex salt>
--   Total length: 62 characters  (prefix "S:" + 40 + 20)
--
-- Required privilege: SELECT on SYS.USER$ or SELECT ANY DICTIONARY / DBA role
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Extract the 11g SHA-1 hash + salt (SPARE4) for all non-system users
-- ---------------------------------------------------------------------------
SELECT
    u.name                          AS username,
    u.spare4                        AS password_verifier_11g,
    SUBSTR(u.spare4, 3, 40)         AS sha1_hash,
    SUBSTR(u.spare4, 43, 20)        AS salt_hex,
    u.password                      AS password_hash_10g,  -- may be NULL in pure 11g mode
    DECODE(u.astatus,
        0,  'OPEN',
        4,  'EXPIRED',
        8,  'LOCKED',
        16, 'EXPIRED & LOCKED',
        'OTHER'
    )                               AS account_status,
    u.ctime                         AS created,
    u.ptime                         AS password_change_time
FROM
    sys.user$  u
WHERE
    u.type# = 1
    AND u.spare4 IS NOT NULL
    AND u.name NOT IN (
        'SYS','SYSTEM','DBSNMP','OUTLN','ANONYMOUS','PUBLIC'
    )
ORDER BY
    u.name;


-- ---------------------------------------------------------------------------
-- 2. Extract both 10g and 11g verifiers side-by-side (for migration audit)
-- ---------------------------------------------------------------------------
SELECT
    u.name                          AS username,
    u.password                      AS hash_10g_des,
    u.spare4                        AS hash_11g_sha1_full,
    CASE
        WHEN u.spare4 IS NOT NULL THEN 'SHA-1 (11g)'
        WHEN u.password IS NOT NULL THEN 'DES (10g only)'
        ELSE 'NONE / EXTERNAL'
    END                             AS active_verifier_type,
    u.astatus                       AS status_code
FROM
    sys.user$  u
WHERE
    u.type# = 1
ORDER BY
    u.name;


-- ---------------------------------------------------------------------------
-- 3. Check whether the 10g DES verifier is still being generated
--    (controlled by the SEC_CASE_SENSITIVE_LOGON parameter)
-- ---------------------------------------------------------------------------
SELECT
    name    AS parameter,
    value   AS current_value
FROM
    v$parameter
WHERE
    name IN (
        'sec_case_sensitive_logon',
        'sqlnet.allowed_logon_version'
    );


-- ---------------------------------------------------------------------------
-- 4. Extract a specific user's hashes
--    Replace &target_user with the username (Oracle stores usernames uppercase).
-- ---------------------------------------------------------------------------
SELECT
    name        AS username,
    password    AS hash_10g,
    spare4      AS hash_11g
FROM
    sys.user$
WHERE
    name = UPPER('&target_user');


-- ---------------------------------------------------------------------------
-- 5. Format output for offline cracking (Hashcat mode 112 – Oracle S: SHA-1)
--    Format expected by Hashcat: hash:salt  where both are uppercase hex.
--    Hashcat -m 112: sha1($salt.$pass) — Oracle 11g
-- ---------------------------------------------------------------------------
SELECT
    u.name
    || ':'
    || SUBSTR(u.spare4, 3, 40)          -- 40-char SHA-1 hash
    || ':'
    || SUBSTR(u.spare4, 43, 20)         AS hashcat_112_format
FROM
    sys.user$  u
WHERE
    u.type# = 1
    AND u.spare4 IS NOT NULL
ORDER BY
    u.name;


-- ---------------------------------------------------------------------------
-- 6. Full audit dump: username, both verifiers, status, timestamps
--    Useful for a security review or migration to 12c+ verifiers.
-- ---------------------------------------------------------------------------
SELECT
    u.name                              AS username,
    u.password                          AS verifier_10g,
    u.spare4                            AS verifier_11g,
    DECODE(u.astatus,
        0,  'OPEN',
        1,  'EXPIRED(GRACE)',
        2,  'EXPIRED',
        4,  'EXPIRED & LOCKED(TIMED)',
        8,  'LOCKED(TIMED)',
        16, 'EXPIRED & LOCKED',
        32, 'LOCKED',
        TO_CHAR(u.astatus)
    )                                   AS account_status,
    u.ctime                             AS created,
    u.ptime                             AS last_password_change,
    u.exptime                           AS password_expiry,
    u.ltime                             AS lock_time,
    p.name                              AS profile
FROM
    sys.user$  u
    JOIN sys.profname$ p ON p.profile# = u.resource$
WHERE
    u.type# = 1
ORDER BY
    u.name;


-- ---------------------------------------------------------------------------
-- Notes
-- ---------------------------------------------------------------------------
-- * Oracle 11g SHA-1 algorithm:
--     hash = SHA1( password || hex_decode(salt) )   (case-sensitive)
--   The 20-byte salt is randomly generated at password-set time.
-- * SPARE4 column layout:  S:<40-hex-hash><20-hex-salt>
-- * Hashcat mode -m 112:   sha1($salt.$pass) with hex salt
--   Example command:
--     hashcat -m 112 hashes.txt wordlist.txt
-- * John the Ripper format: --format=oracle11 (or --format=oracle11-opencl)
-- * If SEC_CASE_SENSITIVE_LOGON = FALSE, Oracle 11g falls back to the 10g
--   DES verifier for authentication, making it as weak as 10g.
-- * Oracle 12c introduced a bcrypt-style verifier (T: verifier in SPARE4);
--   use a separate script for 12c+ environments.
