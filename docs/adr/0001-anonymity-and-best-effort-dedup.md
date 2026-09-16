# Anonymity and best-effort dedup

We collect the survey with no PII whatsoever — no names, emails, IPs, or user agents, and IP logging is disabled at the proxy — because honest answers about AI use depend on students trusting that responses can't be traced back to them. As a result, dedup is deliberately weak: a single server-generated UUIDv4 (the **Survey token**) is set in a short-lived cookie on first load and stored as the submission's row id, and a re-submit from the same cookie is rejected. Clearing cookies or using incognito defeats this, which we accept — this is an informal, one-shot in-class survey, not a controlled instrument.

## Consequences

- The cookie token *is* the stored row id — there is intentionally no separate identity. It is a random UUID tied to no person, so this does not deanonymize anyone; it just means "one browser, one submission" until the cookie is cleared.
- Do **not** "harden" this later with IP-based rate limiting, device fingerprinting, or stored request metadata. Each of those reintroduces PII and breaks the anonymity guarantee that is the whole point. Stronger dedup and anonymity are in direct tension here, and anonymity wins.
