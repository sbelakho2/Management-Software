# Data Classification

| Class | Examples | Storage | AI context | Caching |
|-------|----------|---------|------------|---------|
| public | brand material | normal | allowed | allowed |
| internal | process data, standards | normal | allowed | allowed (trust domain) |
| restricted | NCRs, customer commitments | scoped | requires role + scope | salt-isolated |
| personal | employee records | scoped | explicit authorization only | never shared across principals |
| commercial | pricing, supplier terms | scoped | role-gated | trust-domain salted |
| quality-controlled | released standards | immutable revisions | allowed, authority-ranked | allowed |
| engineering-controlled | drawings, revisions | scoped | role-gated | allowed |
| security-sensitive | credentials, tokens | encrypted | never | never cached |

Rules: aggregation cannot bypass site authorization (A24); restricted/personal data
never enters a shared KV cache; retention and export follow the class.
