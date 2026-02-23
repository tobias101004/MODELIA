-- ================================================================
-- MODELIA Credits System — Supabase SQL Setup
-- Run this in Supabase SQL Editor (https://supabase.com/dashboard)
-- ================================================================

-- 1. Create user_credits table
-- ================================================================
CREATE TABLE public.user_credits (
  user_id    uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  credits    integer NOT NULL DEFAULT 0 CHECK (credits >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Auto-create row on signup (trigger)
-- ================================================================
CREATE OR REPLACE FUNCTION public.handle_new_user_credits()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  INSERT INTO public.user_credits (user_id, credits)
  VALUES (NEW.id, 0);
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created_credits
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user_credits();

-- 3. Row Level Security
-- ================================================================
ALTER TABLE public.user_credits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own credits"
  ON public.user_credits
  FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "Users can update own credits"
  ON public.user_credits
  FOR UPDATE
  USING (user_id = auth.uid());

-- 4. RPC: use_credit — atomic decrement, returns false if no credits
-- ================================================================
CREATE OR REPLACE FUNCTION public.use_credit()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  rows_affected integer;
BEGIN
  UPDATE public.user_credits
  SET credits = credits - 1,
      updated_at = now()
  WHERE user_id = auth.uid()
    AND credits > 0;

  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  RETURN rows_affected > 0;
END;
$$;

-- 5. RPC: add_credits(amount) — atomic increment for purchases
-- ================================================================
CREATE OR REPLACE FUNCTION public.add_credits(amount integer)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE public.user_credits
  SET credits = credits + amount,
      updated_at = now()
  WHERE user_id = auth.uid();

  -- If no row exists yet (user registered before this system), create one
  IF NOT FOUND THEN
    INSERT INTO public.user_credits (user_id, credits)
    VALUES (auth.uid(), amount);
  END IF;
END;
$$;

-- 6. Backfill: create rows for existing users who don't have one yet
-- ================================================================
INSERT INTO public.user_credits (user_id, credits)
SELECT id, 0 FROM auth.users
WHERE id NOT IN (SELECT user_id FROM public.user_credits);
