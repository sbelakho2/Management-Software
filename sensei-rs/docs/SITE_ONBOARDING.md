# Site Onboarding

Target (item 83/93): a competent team brings a new plant onto Starz Forge WITHOUT
modifying core domain code. Declarative inputs:

- SiteManifest: id, country, timezone, languages, currency, capabilities,
  integrations, policy bundle.
- ERP/CRM mapping (canonical adapters — ExternalReference keeps source identity).
- Process capability map, org/role map (role slots), equipment map, standards
  (TWI job standards), country policy, localization, validation, go-live criteria.

Design today: site_id is a first-class column on every operational table (migration
112); roles are slot-based (114); the canonical event envelope (113) is source-
agnostic; metric definitions are per-tenant seeded (115). A new site is a set of
records, not a fork.
