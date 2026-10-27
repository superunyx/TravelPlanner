import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiRequest } from "../lib/api";
import { Trip } from "../types";
import { useUIStore } from "../store/uiStore";
import {
  Compass,
  Calendar,
  Wallet,
  PlusCircle,
  Trash2,
  Users,
  MapPin,
  Sparkles,
} from "lucide-react";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const addToast = useUIStore((s) => s.addToast);

  const { data: trips = [], isLoading } = useQuery<Trip[]>({
    queryKey: ["trips"],
    queryFn: () => apiRequest<Trip[]>("/api/v1/trips"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/api/v1/trips/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      addToast("success", "Trip deleted successfully");
    },
    onError: (err: unknown) => {
      addToast("error", err instanceof Error ? err.message : "Failed to delete trip");
    },
  });

  // Calculate stats
  const totalTrips = trips.length;
  const totalBudget = trips.reduce((acc, t) => acc + (t.budget || 0), 0);
  const upcomingTrip = trips
    .filter((t) => new Date(t.start_date) >= new Date())
    .sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())[0];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Trip Overview
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Manage your AI-crafted adventures, itineraries, and group travel
          </p>
        </div>
        <Link
          to="/trips/new"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-sm transition"
        >
          <PlusCircle className="w-4 h-4" /> Plan New Trip
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
            <Compass className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Trips</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">{totalTrips}</p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
            <Calendar className="w-6 h-6" />
          </div>
          <div className="truncate">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Upcoming Trip</p>
            <p className="text-base font-bold text-slate-900 dark:text-white mt-0.5 truncate">
              {upcomingTrip ? upcomingTrip.destination : "None planned"}
            </p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
            <Wallet className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Planned Budget</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">
              ₹{totalBudget.toLocaleString("en-IN")}
            </p>
          </div>
        </div>
      </div>

      {/* Grid of Trips */}
      <div>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Your Itineraries</h2>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="h-56 rounded-2xl bg-slate-100 dark:bg-slate-800/50 animate-pulse border border-slate-200 dark:border-slate-800"
              />
            ))}
          </div>
        ) : trips.length === 0 ? (
          <div className="p-12 text-center rounded-3xl bg-white dark:bg-slate-900 border border-dashed border-slate-300 dark:border-slate-800 flex flex-col items-center">
            <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">No itineraries yet</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mt-1 mb-6">
              Start by telling us your dream destination, budget, and travel style to generate a custom itinerary.
            </p>
            <Link
              to="/trips/new"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition shadow-sm"
            >
              <PlusCircle className="w-4 h-4" /> Create Your First Trip
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trips.map((trip) => (
              <div
                key={trip.id}
                className="group relative rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                        trip.status === "generated"
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400"
                          : "bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400"
                      }`}
                    >
                      {trip.status === "generated" ? "Itinerary Ready" : "Draft"}
                    </span>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        if (confirm("Are you sure you want to delete this trip?")) {
                          deleteMutation.mutate(trip.id);
                        }
                      }}
                      className="text-slate-400 hover:text-rose-500 p-1.5 transition"
                      title="Delete trip"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <Link to={`/trips/${trip.id}`} className="block">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 transition">
                      {trip.title}
                    </h3>
                    <p className="text-sm font-medium text-slate-500 flex items-center gap-1.5 mt-1">
                      <MapPin className="w-4 h-4 text-indigo-500" /> {trip.destination}
                    </p>
                  </Link>

                  <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 space-y-2 text-xs text-slate-600 dark:text-slate-400">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {trip.start_date} &rarr; {trip.end_date}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Users className="w-3.5 h-3.5 text-slate-400" />
                        {trip.group_size} travelers
                      </span>
                    </div>
                    {trip.budget && (
                      <div className="flex items-center justify-between font-semibold text-slate-900 dark:text-white">
                        <span>Budget</span>
                        <span>₹{Number(trip.budget).toLocaleString("en-IN")}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-6 pt-4">
                  <Link
                    to={`/trips/${trip.id}`}
                    className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 hover:text-indigo-600 dark:hover:text-indigo-400 text-slate-700 dark:text-slate-300 font-semibold text-xs transition"
                  >
                    View Itinerary &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
