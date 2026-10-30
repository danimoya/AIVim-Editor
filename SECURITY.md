# Security and privacy

AIVim edits files as the local OS user. The browser CLI accepts loopback callers only and validates Host, Origin and CSRF; the authenticated factory requires explicit principals, provider grants, signing keys, allowed hosts and shared quota storage. No multi-tenant document storage is advertised. Do not infer deployment identity or provider entitlement from a configured model name.

AI requests transmit the current snapshot and explicitly selected context. Default logs contain no source text or credentials. Content logging is explicitly enabled and uses restricted files with retention. Provider errors and truncated output cannot become code. AI edits require validated snapshot proposals; stale/cancelled output is discarded. Text results are rendered as inert text with a restrictive content policy.

Normal install has no bundled models. Native inference needs separately installed optional dependencies and operator-selected weights/digests. Model processes have deadlines and process termination; POSIX memory/CPU limits are enforced. Download recovery preserves identified partial data and verifies the complete digest before installation.

Use the repository's issue tracker for reproducible non-sensitive reports. Do not attach keys, customer documents, provider prompts or private file contents. No automatic updates, credential rotation or security inbox service is configured in this candidate.
