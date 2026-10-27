import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

import { apiRequest } from "../lib/api";
import { Trip, DayRecord, TripSummary, Activity } from "../types";
import { useUIStore } from "../store/uiStore";
import { ActivityCard } from "../components/ActivityCard";
import { BudgetSummaryPanel } from "../components/BudgetSummaryPanel";
import { ShareModal } from "../components/ShareModal";
import {
  Sparkles,
  Share2,
  RefreshCw,
  ArrowLeft,
  AlertCircle,
} from "lucide-react";

export function TripDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const addToast = useUIStore((s) => s.addToast);

  const [activeDayNumber, setActiveDayNumber] = useState<number>(1);
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [regenInstruction, setRegenInstruction] = useState("");
  const [showRegenModal, setShowRegenModal] = useState(false);
  const [showConfirmTripRegen, setShowConfirmTripRegen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Queries
  const { data: trip, isLoading: isTripLoading } = useQuery<Trip>({
    queryKey: ["trip", id],
    queryFn: () => apiRequest<Trip>(`/api/v1/trips/${id}`),
    enabled: !!id,
  });

  const { data: days = [] } = useQuery<DayRecord[]>({
    queryKey: ["trip-days", id],
    queryFn: () => apiRequest<DayRecord[]>(`/api/v1/trips/${id}/days`),
    enabled: !!id,
  });

  const { data: summary } = useQuery<TripSummary>({
    queryKey: ["trip-summary", id],
    queryFn: () => apiRequest<TripSummary>(`/api/v1/trips/${id}/summary`),
    enabled: !!id,
  });

  // Mutations
  const updateDayMutation = useMutation({
    mutationFn: ({ dayNum, items }: { dayNum: number; items: Activity[] }) =>
      apiRequest(`/api/v1/trips/${id}/days/${dayNum}`, {
        method: "PATCH",
        body: JSON.stringify({ items }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trip-days", id] });
      queryClient.invalidateQueries({ queryKey: ["trip-summary", id] });
      addToast("success", "Day updated!");
    },
  });

  const regenDayMutation = useMutation({
    mutationFn: ({ dayNum, instruction }: { dayNum: number; instruction?: string }) =>
      apiRequest(`/api/v1/trips/${id}/days/${dayNum}/regenerate`, {
        method: "POST",
        body: JSON.stringify({ instruction }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trip-days", id] });
      queryClient.invalidateQueries({ queryKey: ["trip-summary", id] });
      setShowRegenModal(false);
      setRegenInstruction("");
      addToast("success", `Day ${activeDayNumber} refreshed by AI!`);
    },
    onError: (err: unknown) => {
      addToast("error", err instanceof Error ? err.message : "Failed to regenerate day");
    },
  });

  const regenTripMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/trips/${id}/generate`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trip", id] });
      queryClient.invalidateQueries({ queryKey: ["trip-days", id] });
      queryClient.invalidateQueries({ queryKey: ["trip-summary", id] });
      setShowConfirmTripRegen(false);
      addToast("success", "Trip regenerated successfully!");
    },
    onError: (err: unknown) => {
      addToast("error", err instanceof Error ? err.message : "Regeneration failed");
    },
  });

  if (isTripLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-20 bg-slate-200 dark:bg-slate-800 rounded-3xl" />
        <div className="h-96 bg-slate-200 dark:bg-slate-800 rounded-3xl" />
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="text-center py-16">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">Trip not found</h3>
        <Link to="/dashboard" className="text-indigo-600 text-sm mt-2 inline-block">
          &larr; Return to Dashboard
        </Link>
      </div>
    );
  }

  const activeDay = days.find((d) => d.day_number === activeDayNumber) || days[0];

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !activeDay) return;

    const items = [...activeDay.items];
    const oldIndex = items.findIndex((_, idx) => `activity-${idx}-${items[idx].title}` === active.id);
    const newIndex = items.findIndex((_, idx) => `activity-${idx}-${items[idx].title}` === over.id);

    if (oldIndex !== -1 && newIndex !== -1) {
      const reordered = arrayMove(items, oldIndex, newIndex);
      updateDayMutation.mutate({ dayNum: activeDay.day_number, items: reordered });
    }
  };

  const handleUpdateActivity = (index: number, updated: Activity) => {
    if (!activeDay) return;
    const items = [...activeDay.items];
    items[index] = updated;
    updateDayMutation.mutate({ dayNum: activeDay.day_number, items });
  };

  const handleDeleteActivity = (index: number) => {
    if (!activeDay) return;
    const items = activeDay.items.filter((_, i) => i !== index);
    updateDayMutation.mutate({ dayNum: activeDay.day_number, items });
  };

  return (
    <div className="space-y-8">
      {/* Top Header & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <Link
            to="/dashboard"
            className="text-xs font-semibold text-slate-400 hover:text-indigo-600 flex items-center gap-1 mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 dark:text-white">{trip.title}</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 capitalize">
              {trip.pacing}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-2">
            <span>{trip.destination}</span> • <span>{trip.start_date} to {trip.end_date}</span> • <span>{trip.group_size} travelers</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsShareOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 transition"
          >
            <Share2 className="w-3.5 h-3.5" /> Share
          </button>
          <button
            onClick={() => setShowConfirmTripRegen(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 dark:bg-white hover:bg-slate-800 dark:hover:bg-slate-100 text-white dark:text-slate-900 text-xs font-semibold shadow-sm transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Regenerate Trip
          </button>
        </div>
      </div>

      {/* Main Content Layout: Timeline (left 2/3) + Sticky Budget (right 1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Day Navigation Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
            {days.map((day) => (
              <button
                key={day.day_number}
                onClick={() => setActiveDayNumber(day.day_number)}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition whitespace-nowrap ${
                  activeDayNumber === day.day_number
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50"
                }`}
              >
                Day {day.day_number} {day.date ? `(${day.date.slice(5)})` : ""}
              </button>
            ))}
          </div>

          {/* Active Day Card */}
          {activeDay ? (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Day {activeDay.day_number} Overview
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">{activeDay.summary}</p>
                </div>
                <button
                  onClick={() => setShowRegenModal(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 text-xs font-semibold transition shrink-0 self-start sm:self-auto"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Regenerate this Day
                </button>
              </div>

              {/* Drag and drop activities */}
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={activeDay.items.map((act, i) => `activity-${i}-${act.title}`)}
                  strategy={verticalListSortingStrategy}
                >
                  <div className="space-y-3">
                    {activeDay.items.map((activity, index) => (
                      <ActivityCard
                        key={`act-${index}-${activity.title}`}
                        activity={activity}
                        index={index}
                        onUpdate={(updated) => handleUpdateActivity(index, updated)}
                        onDelete={() => handleDeleteActivity(index)}
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
            </div>
          ) : (
            <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
              <p className="text-sm text-slate-500">No days generated yet.</p>
            </div>
          )}
        </div>

        {/* Right Sticky Budget & Stay Breakdown */}
        <div className="lg:col-span-1">
          <BudgetSummaryPanel
            summary={summary || null}
            stay={trip.stay as { name?: string; area?: string; price_per_night?: number; why?: string }}
          />
        </div>
      </div>

      {/* Share Modal */}
      <ShareModal
        tripId={trip.id}
        isOpen={isShareOpen}
        onClose={() => setIsShareOpen(false)}
      />

      {/* Regenerate Day Modal */}
      {showRegenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-2xl space-y-4">
            <h3 className="font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-500" /> Regenerate Day {activeDayNumber}
            </h3>
            <p className="text-xs text-slate-400">
              Provide instructions to guide AI adjustments without repeating places from other days:
            </p>
            <textarea
              rows={3}
              value={regenInstruction}
              onChange={(e) => setRegenInstruction(e.target.value)}
              placeholder="e.g. Focus on historic architecture and vegetarian street food."
              className="w-full p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowRegenModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                disabled={regenDayMutation.isPending}
                onClick={() =>
                  regenDayMutation.mutate({
                    dayNum: activeDayNumber,
                    instruction: regenInstruction,
                  })
                }
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
              >
                {regenDayMutation.isPending ? "Regenerating..." : "Regenerate Day"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Trip Regenerate Modal */}
      {showConfirmTripRegen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-2xl space-y-4">
            <div className="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 flex items-center justify-center">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-base text-slate-900 dark:text-white">
              Regenerate Full Trip?
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              This will overwrite all current days, activities, and custom edits with a freshly generated itinerary.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowConfirmTripRegen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                disabled={regenTripMutation.isPending}
                onClick={() => regenTripMutation.mutate()}
                className="px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
              >
                {regenTripMutation.isPending ? "Generating..." : "Confirm & Regenerate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
