-- =============================================================================
-- Migration: 001_init.sql
-- Description: Initial schema for Personalized Travel Itinerary Planner
--              (trips, itinerary_days, trip_members), indexes, triggers, and RLS.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. Tables
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    destination TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget NUMERIC(12, 2),
    currency TEXT NOT NULL DEFAULT 'INR',
    travel_style TEXT,
    pacing TEXT NOT NULL DEFAULT 'moderate' CHECK (pacing IN ('relaxed', 'moderate', 'packed')),
    group_size INT NOT NULL DEFAULT 1 CHECK (group_size >= 1),
    interests TEXT[] NOT NULL DEFAULT '{}',
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    stay JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'generated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT trips_valid_date_range CHECK (end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS public.itinerary_days (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    day_number INT NOT NULL CHECK (day_number >= 1),
    date DATE,
    summary TEXT NOT NULL DEFAULT '',
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    est_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    UNIQUE (trip_id, day_number)
);

CREATE TABLE IF NOT EXISTS public.trip_members (
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'editor', 'viewer')),
    PRIMARY KEY (trip_id, user_id)
);

-- -----------------------------------------------------------------------------
-- 2. Indexes
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_trips_owner_id ON public.trips(owner_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON public.trips(status);
CREATE INDEX IF NOT EXISTS idx_itinerary_days_trip_id ON public.itinerary_days(trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_members_user_id ON public.trip_members(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_members_trip_id ON public.trip_members(trip_id);

-- -----------------------------------------------------------------------------
-- 3. Triggers (updated_at on trips)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_trips_updated_at ON public.trips;
CREATE TRIGGER trg_trips_updated_at
BEFORE UPDATE ON public.trips
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

-- -----------------------------------------------------------------------------
-- 4. Row Level Security (RLS) Helpers & Policies
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.is_trip_owner(check_trip_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.trips t
        WHERE t.id = check_trip_id
          AND t.owner_id = auth.uid()
    );
$$;

CREATE OR REPLACE FUNCTION public.is_trip_member(check_trip_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.trip_members tm
        WHERE tm.trip_id = check_trip_id
          AND tm.user_id = auth.uid()
    );
$$;

CREATE OR REPLACE FUNCTION public.can_edit_trip_days(check_trip_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT public.is_trip_owner(check_trip_id)
        OR EXISTS (
            SELECT 1
            FROM public.trip_members tm
            WHERE tm.trip_id = check_trip_id
              AND tm.user_id = auth.uid()
              AND tm.role IN ('owner', 'editor')
        );
$$;

ALTER TABLE public.trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.itinerary_days ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trip_members ENABLE ROW LEVEL SECURITY;

-- Policies for public.trips
DROP POLICY IF EXISTS trips_owner_all ON public.trips;
CREATE POLICY trips_owner_all
ON public.trips
FOR ALL
USING (owner_id = auth.uid())
WITH CHECK (owner_id = auth.uid());

DROP POLICY IF EXISTS trips_member_select ON public.trips;
CREATE POLICY trips_member_select
ON public.trips
FOR SELECT
USING (public.is_trip_member(id));

-- Policies for public.itinerary_days
DROP POLICY IF EXISTS itinerary_days_owner_all ON public.itinerary_days;
CREATE POLICY itinerary_days_owner_all
ON public.itinerary_days
FOR ALL
USING (public.is_trip_owner(trip_id))
WITH CHECK (public.is_trip_owner(trip_id));

DROP POLICY IF EXISTS itinerary_days_member_select ON public.itinerary_days;
CREATE POLICY itinerary_days_member_select
ON public.itinerary_days
FOR SELECT
USING (public.is_trip_member(trip_id));

DROP POLICY IF EXISTS itinerary_days_editor_update ON public.itinerary_days;
CREATE POLICY itinerary_days_editor_update
ON public.itinerary_days
FOR UPDATE
USING (public.can_edit_trip_days(trip_id))
WITH CHECK (public.can_edit_trip_days(trip_id));

-- Policies for public.trip_members
DROP POLICY IF EXISTS trip_members_owner_all ON public.trip_members;
CREATE POLICY trip_members_owner_all
ON public.trip_members
FOR ALL
USING (public.is_trip_owner(trip_id))
WITH CHECK (public.is_trip_owner(trip_id));

DROP POLICY IF EXISTS trip_members_member_select ON public.trip_members;
CREATE POLICY trip_members_member_select
ON public.trip_members
FOR SELECT
USING (user_id = auth.uid() OR public.is_trip_member(trip_id));
