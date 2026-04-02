# Oracle Password Hash Extraction Scripts

SQL scripts to extract password hashes from Oracle Database **10g** and **11g** for security auditing, penetration testing, and hash-cracking research.

---

## Files

| File | Description |
|------|-------------|
| `oracle_10g_password.sql` | Extract DES-based password hashes from Oracle 10g (and earlier) |
| `oracle_11g_password.sql` | Extract SHA-1-based password hashes from Oracle 11g |
| `oracle_password_combined.sql` | Auto-detecting combined script covering both versions |

---

## Background

Oracle stores password verifiers in the `SYS.USER$` system table:

| Column | Version | Algorithm | Notes |
|--------|---------|-----------|-------|
| `PASSWORD` | 10g and earlier | DES (16-char hex) | Case-insensitive; same hash for upper/lowercase passwords |
| `SPARE4` | 11g+ | SHA-1 with random salt (format `S:<40-hex-hash><20-hex-salt>`) | Case-sensitive by default |

In 11g, both verifiers may co-exist depending on the `SEC_CASE_SENSITIVE_LOGON` parameter.

---

## Requirements

- **Oracle Database 10g** (10.1.x / 10.2.x) or **Oracle Database 11g** (11.1.x / 11.2.x)
- Connect as **SYS** (`AS SYSDBA`) or a user with:
  - `SELECT` on `SYS.USER$`
  - `SELECT` on `V$VERSION`, `V$PARAMETER`
  - The **DBA** role satisfies all of the above.

---

## Usage

### Run the combined script (recommended)

```sql
sqlplus / as sysdba @oracle_password_combined.sql
```

### Run a version-specific script

```sql
-- Oracle 10g
sqlplus / as sysdba @oracle_10g_password.sql

-- Oracle 11g
sqlplus / as sysdba @oracle_11g_password.sql
```

### Spool output to a file

```sql
SPOOL /tmp/hashes.txt
@oracle_password_combined.sql
SPOOL OFF
```

---

## Hash Cracking Reference

### Oracle 10g — DES (Hashcat mode 3100)

The 10g verifier is a DES encryption of `UPPER(username) || UPPER(password)`.

```bash
# Hashcat
hashcat -m 3100 hashes_10g.txt wordlist.txt

# John the Ripper
john --format=oracle hashes_10g.txt
```

Hash format expected: `username:HASH` (e.g. `SCOTT:F894844C34402B67`)

### Oracle 11g — SHA-1 (Hashcat mode 112)

The 11g verifier is `SHA1(password || hex_decode(salt))` with a 10-byte random salt.

```bash
# Hashcat
hashcat -m 112 hashes_11g.txt wordlist.txt

# John the Ripper
john --format=oracle11 hashes_11g.txt
```

Hash format expected: `sha1_hash:salt_hex` (e.g. `7C9B...:2A3F...`)

---

## Key Oracle 11g Security Parameters

| Parameter | Effect |
|-----------|--------|
| `SEC_CASE_SENSITIVE_LOGON = TRUE` (default) | Passwords are case-sensitive; 11g SHA-1 verifier used |
| `SEC_CASE_SENSITIVE_LOGON = FALSE` | Falls back to 10g DES verifier; case-insensitive |
| `SQLNET.ALLOWED_LOGON_VERSION` | Minimum client authentication protocol version |

Check current settings:

```sql
SELECT name, value FROM v$parameter
WHERE name LIKE '%sec_case%' OR name LIKE '%logon_version%';
```

---

## Disclaimer

These scripts are provided for **authorized security auditing and penetration testing only**. Unauthorized access to computer systems or databases is illegal. Always obtain explicit written permission before running these scripts on any system.
