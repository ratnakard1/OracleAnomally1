# SSH error: "no hostkey alg"

If you see:

```text
$ ssh ilcemtr237.corp.amdocs.com
no hostkey alg
```

it usually means your SSH client and the server **cannot agree on a host key algorithm**. Most commonly, the server only offers legacy `ssh-rsa` (SHA-1), which newer OpenSSH clients disable by default.

## One-off connection (recommended for testing)

```bash
ssh \
  -o HostKeyAlgorithms=+ssh-rsa \
  -o PubkeyAcceptedAlgorithms=+ssh-rsa \
  ilcemtr237.corp.amdocs.com
```

If you still can’t connect, run with debugging to see what the server offers:

```bash
ssh -vvv ilcemtr237.corp.amdocs.com
```

## Permanent fix (scoped to one host)

Add this to `~/.ssh/config` on the client machine:

```sshconfig
Host ilcemtr237.corp.amdocs.com
  HostKeyAlgorithms +ssh-rsa
  PubkeyAcceptedAlgorithms +ssh-rsa
```

## Best fix (server-side)

If you manage the server, update it to present modern host keys (e.g. `ssh-ed25519` or RSA SHA-2 `rsa-sha2-256` / `rsa-sha2-512`) so clients don’t need legacy overrides.

