-- Twenty-fourth audit P1 (integration revision race): the checkpoint row
-- records the EXACT configuration revision the run certified. A bridge
-- run starts against the instance's CURRENT configuration revision and
-- sends that tested revision with its completion write
-- (verified_configuration_revision); the instance's verification stamp
-- (integration_instances.last_verified_revision) is only advanced while
-- the instance is STILL at the tested revision (a guarded conditional
-- UPDATE in write_checkpoint). Persisting the tested revision on the
-- checkpoint row makes the durable cursor itself name what it certified
-- — a row stamped by a run of an older configuration can never be
-- confused with one that verified the current configuration.
ALTER TABLE integration_checkpoints
    ADD COLUMN IF NOT EXISTS verified_revision BIGINT;
