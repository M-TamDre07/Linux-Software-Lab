-- Keep the RLS-enforcement event trigger internal to PostgreSQL.
-- The event trigger "ensure_rls" remains enabled; direct API execution is not needed.
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated, service_role;
