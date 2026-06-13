-- =============================================================================
-- MODELIA — politicas de seguridad de Supabase
-- =============================================================================
-- Pega este fichero entero en el SQL Editor de Supabase (Dashboard → SQL).
-- Se puede ejecutar varias veces sin problemas (todo es idempotente).
--
-- Lo que hace:
--   1. Bloquea el alta de usuarios cuyo email NO termine en
--      @cardenas-grancanaria.com.
--   2. Activa Row Level Security en las 5 tablas de la app y crea politicas
--      que solo permiten acceso a usuarios autenticados (los unicos que
--      pueden estar autenticados son los del dominio permitido).
--   3. Politicas del bucket Storage 'hojas-visita': solo autenticados.
--
-- IMPORTANTE: tras pegar, comprueba en Authentication → Users que tu propio
-- usuario sigue pudiendo entrar. Si te bloqueaste, en SQL Editor:
--   delete from auth.users where email = 'tu_email_problemico@dominio.com';
-- =============================================================================


-- =============================================================================
-- 1. Trigger: solo se aceptan altas con email @cardenas-grancanaria.com
-- =============================================================================

create or replace function public.enforce_email_domain()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.email is null or position('@cardenas-grancanaria.com' in lower(new.email)) = 0
     or lower(new.email) not like '%@cardenas-grancanaria.com' then
    raise exception 'Solo se permiten emails @cardenas-grancanaria.com (recibido: %)', new.email;
  end if;
  return new;
end;
$$;

drop trigger if exists enforce_email_domain_trigger on auth.users;

create trigger enforce_email_domain_trigger
before insert on auth.users
for each row
execute function public.enforce_email_domain();

-- Tambien bloqueamos UPDATE: nadie puede cambiar su email a otro dominio
drop trigger if exists enforce_email_domain_update_trigger on auth.users;

create trigger enforce_email_domain_update_trigger
before update of email on auth.users
for each row
when (new.email is distinct from old.email)
execute function public.enforce_email_domain();


-- =============================================================================
-- 2. RLS en tablas de la app
-- =============================================================================
-- Estrategia: solo usuarios autenticados pueden leer/escribir. Como el alta
-- esta filtrada por dominio, "autenticado" = "miembro del equipo Cardenas".
--
-- Si en el futuro quereis aislar por usuario (que cada uno solo vea SUS
-- auditorias), basta con anadir columna user_id uuid references auth.users
-- y cambiar 'using (true)' por 'using (auth.uid() = user_id)'.

-- --- audit_sessions ----------------------------------------------------------
alter table if exists public.audit_sessions enable row level security;

drop policy if exists "audit_sessions_authenticated_read"   on public.audit_sessions;
drop policy if exists "audit_sessions_authenticated_write"  on public.audit_sessions;
drop policy if exists "audit_sessions_authenticated_update" on public.audit_sessions;
drop policy if exists "audit_sessions_authenticated_delete" on public.audit_sessions;

create policy "audit_sessions_authenticated_read"
  on public.audit_sessions for select to authenticated using (true);
create policy "audit_sessions_authenticated_write"
  on public.audit_sessions for insert to authenticated with check (true);
create policy "audit_sessions_authenticated_update"
  on public.audit_sessions for update to authenticated using (true) with check (true);
create policy "audit_sessions_authenticated_delete"
  on public.audit_sessions for delete to authenticated using (true);


-- --- audit_checks ------------------------------------------------------------
alter table if exists public.audit_checks enable row level security;

drop policy if exists "audit_checks_authenticated_read"   on public.audit_checks;
drop policy if exists "audit_checks_authenticated_write"  on public.audit_checks;
drop policy if exists "audit_checks_authenticated_update" on public.audit_checks;
drop policy if exists "audit_checks_authenticated_delete" on public.audit_checks;

create policy "audit_checks_authenticated_read"
  on public.audit_checks for select to authenticated using (true);
create policy "audit_checks_authenticated_write"
  on public.audit_checks for insert to authenticated with check (true);
create policy "audit_checks_authenticated_update"
  on public.audit_checks for update to authenticated using (true) with check (true);
create policy "audit_checks_authenticated_delete"
  on public.audit_checks for delete to authenticated using (true);


-- --- leads -------------------------------------------------------------------
alter table if exists public.leads enable row level security;

drop policy if exists "leads_authenticated_read"   on public.leads;
drop policy if exists "leads_authenticated_write"  on public.leads;
drop policy if exists "leads_authenticated_update" on public.leads;
drop policy if exists "leads_authenticated_delete" on public.leads;

create policy "leads_authenticated_read"
  on public.leads for select to authenticated using (true);
create policy "leads_authenticated_write"
  on public.leads for insert to authenticated with check (true);
create policy "leads_authenticated_update"
  on public.leads for update to authenticated using (true) with check (true);
create policy "leads_authenticated_delete"
  on public.leads for delete to authenticated using (true);


-- --- chat_logs ---------------------------------------------------------------
alter table if exists public.chat_logs enable row level security;

drop policy if exists "chat_logs_authenticated_read"   on public.chat_logs;
drop policy if exists "chat_logs_authenticated_write"  on public.chat_logs;
drop policy if exists "chat_logs_authenticated_update" on public.chat_logs;
drop policy if exists "chat_logs_authenticated_delete" on public.chat_logs;

create policy "chat_logs_authenticated_read"
  on public.chat_logs for select to authenticated using (true);
create policy "chat_logs_authenticated_write"
  on public.chat_logs for insert to authenticated with check (true);
create policy "chat_logs_authenticated_update"
  on public.chat_logs for update to authenticated using (true) with check (true);
create policy "chat_logs_authenticated_delete"
  on public.chat_logs for delete to authenticated using (true);


-- --- properties --------------------------------------------------------------
alter table if exists public.properties enable row level security;

drop policy if exists "properties_authenticated_read"   on public.properties;
drop policy if exists "properties_authenticated_write"  on public.properties;
drop policy if exists "properties_authenticated_update" on public.properties;
drop policy if exists "properties_authenticated_delete" on public.properties;

create policy "properties_authenticated_read"
  on public.properties for select to authenticated using (true);
create policy "properties_authenticated_write"
  on public.properties for insert to authenticated with check (true);
create policy "properties_authenticated_update"
  on public.properties for update to authenticated using (true) with check (true);
create policy "properties_authenticated_delete"
  on public.properties for delete to authenticated using (true);


-- =============================================================================
-- 3. Storage: bucket 'hojas-visita' — solo autenticados
-- =============================================================================
-- Nota: en Supabase, las policies de Storage viven en la tabla
-- storage.objects con bucket_id como filtro.

drop policy if exists "hojas_visita_authenticated_read"   on storage.objects;
drop policy if exists "hojas_visita_authenticated_write"  on storage.objects;
drop policy if exists "hojas_visita_authenticated_update" on storage.objects;
drop policy if exists "hojas_visita_authenticated_delete" on storage.objects;

create policy "hojas_visita_authenticated_read"
  on storage.objects for select to authenticated
  using (bucket_id = 'hojas-visita');

create policy "hojas_visita_authenticated_write"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'hojas-visita');

create policy "hojas_visita_authenticated_update"
  on storage.objects for update to authenticated
  using (bucket_id = 'hojas-visita')
  with check (bucket_id = 'hojas-visita');

create policy "hojas_visita_authenticated_delete"
  on storage.objects for delete to authenticated
  using (bucket_id = 'hojas-visita');


-- =============================================================================
-- LISTO. Verifica:
--   select rowsecurity from pg_tables
--    where schemaname='public' and tablename in
--          ('audit_sessions','audit_checks','leads','chat_logs','properties');
--   -- todas deben mostrar rowsecurity = true
-- =============================================================================
