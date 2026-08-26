-- Email identity is GLOBAL after normalization: login is email+password
-- without a workspace, so the same normalized email must never exist in two
-- tenants (which account would authenticate becomes ambiguous otherwise).
CREATE UNIQUE INDEX IF NOT EXISTS users_email_normalized_unique
    ON users ((lower(email)));
