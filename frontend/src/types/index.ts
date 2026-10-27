export type PacingType = "relaxed" | "moderate" | "packed";
export type TripStatusType = "draft" | "generated";
export type TimeSlotType = "morning" | "afternoon" | "evening" | "night";
export type ActivityType = "attraction" | "dining" | "transport" | "stay" | "activity";

export interface Activity {
  time_slot: TimeSlotType;
  start_time: string;
  end_time: string;
  title: string;
  type: ActivityType;
  description: string;
  location: string;
  est_cost: number;
  travel_time_from_previous_min: number;
  tips?: string;
}

export interface DayPlan {
  day_number: number;
  date: string;
  theme?: string;
  summary: string;
  activities: Activity[];
  day_total_cost: number;
}

export interface Accommodation {
  name: string;
  area: string;
  price_per_night: number;
  why: string;
}

export interface Itinerary {
  destination: string;
  days: DayPlan[];
  accommodation: Accommodation;
  total_estimated_cost: number;
  budget_status: "under_budget" | "on_budget" | "over_budget";
  packing_tips: string[];
}

export interface Trip {
  id: string;
  owner_id: string;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget: number | null;
  currency: string;
  travel_style: string | null;
  pacing: PacingType;
  group_size: number;
  interests: string[];
  preferences: Record<string, unknown>;
  stay: Record<string, unknown>;
  status: TripStatusType;
  created_at: string;
  updated_at: string;
}

export interface DayRecord {
  id: string;
  trip_id: string;
  day_number: number;
  date: string | null;
  summary: string;
  items: Activity[];
  est_cost: number;
}

export interface CategoryBreakdown {
  category: string;
  total_cost: number;
  percentage: number;
}

export interface TripSummary {
  trip_id: string;
  currency: string;
  budget: number | null;
  total_estimated_cost: number;
  accommodation_cost: number;
  activities_cost: number;
  budget_status: string;
  difference: number;
  categories: CategoryBreakdown[];
}
