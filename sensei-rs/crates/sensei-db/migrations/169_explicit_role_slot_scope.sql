-- Twenty-ninth-audit Wave A item 5 (explicit role-slot scope): a slot's
-- operational scope becomes EXPLICIT and typed instead of implicit from
-- scope_site_id alone (NULL meant unscoped, an id meant the site — there
-- was no way to express a TENANT-WIDE slot or a WORK-CENTER slot whose
-- site resolves through work_centers.site_id).
--
-- The ADD COLUMN default 'site' populates existing rows BEFORE the
-- backfill; the backfill then rewrites NULL-site rows to 'none' and
-- site rows to 'site' BEFORE the shape CHECK is added — with NOT NULL
-- DEFAULT the CHECK would otherwise reject every legacy NULL-site row.
ALTER TABLE role_slots
    ADD COLUMN scope_kind TEXT NOT NULL DEFAULT 'site';
ALTER TABLE role_slots
    ADD COLUMN scope_work_center_id UUID;

UPDATE role_slots
   SET scope_kind = CASE
                        WHEN scope_site_id IS NULL THEN 'none'
                        ELSE 'site'
                    END;

ALTER TABLE role_slots
    ADD CONSTRAINT role_slots_scope_kind_check
    CHECK (scope_kind IN ('none', 'site', 'tenant', 'work_center'));

-- Shape pairs: the scope_kind and the id columns it carries must agree.
-- 'none' and 'tenant' carry no ids; 'site' carries exactly scope_site_id;
-- 'work_center' carries its work center AND the denormalized owning site
-- (work_centers.site_id) so every site-scoped read that joins through
-- role_slots.scope_site_id keeps working for work-center slots.
ALTER TABLE role_slots
    ADD CONSTRAINT role_slots_scope_shape_check
    CHECK (
        (scope_kind = 'none'        AND scope_site_id IS NULL         AND scope_work_center_id IS NULL)
     OR (scope_kind = 'tenant'      AND scope_site_id IS NULL         AND scope_work_center_id IS NULL)
     OR (scope_kind = 'site'        AND scope_site_id IS NOT NULL     AND scope_work_center_id IS NULL)
     OR (scope_kind = 'work_center' AND scope_site_id IS NOT NULL     AND scope_work_center_id IS NOT NULL)
    );

CREATE INDEX IF NOT EXISTS idx_role_slots_scope_work_center
    ON role_slots (scope_work_center_id);
