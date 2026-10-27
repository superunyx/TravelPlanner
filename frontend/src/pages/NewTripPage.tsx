import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { apiRequest } from "../lib/api";
import { Trip } from "../types";
import { useUIStore } from "../store/uiStore";
import {
  MapPin,
  Wallet,
  Users,
  Compass,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";

const step1Schema = z.object({
  title: z.string().min(1, "Trip title is required"),
  destination: z.string().min(2, "Destination is required"),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().min(1, "End date is required"),
});

const step2Schema = z.object({
  budget: z.number().positive("Budget must be greater than zero"),
  currency: z.string().default("INR"),
  group_size: z.number().int().min(1).max(20),
  pacing: z.enum(["relaxed", "moderate", "packed"]),
});

const step3Schema = z.object({
  travel_style: z.string().min(1, "Travel style is required"),
  interests: z.array(z.string()).min(1, "Select at least one interest"),
  dietary: z.string().optional(),
});

const formSchema = step1Schema.merge(step2Schema).merge(step3Schema).refine(
  (data) => new Date(data.end_date) >= new Date(data.start_date),
  { message: "End date cannot be earlier than start date", path: ["end_date"] }
);

type FormValues = z.infer<typeof formSchema>;

const AVAILABLE_INTERESTS = [
  "Historical Forts",
  "Local Cuisine",
  "Beaches",
  "Temples & Spirituality",
  "Nature & Wildlife",
  "Museums & Art",
  "Street Markets",
  "Nightlife",
  "Trekking",
  "Photography",
];

const PACING_OPTIONS = [
  { value: "relaxed", label: "Relaxed", desc: "3-4 leisurely spots/day" },
  { value: "moderate", label: "Moderate", desc: "4-5 balanced activities" },
  { value: "packed", label: "Packed", desc: "5-6 sights, packed days" },
];

export function NewTripPage() {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState("Preparing trip parameters...");
  const navigate = useNavigate();
  const addToast = useUIStore((s) => s.addToast);

  const {
    register,
    handleSubmit,
    control,
    watch,
    trigger,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      title: "",
      destination: "",
      start_date: new Date().toISOString().split("T")[0],
      end_date: new Date(Date.now() + 3 * 86400000).toISOString().split("T")[0],
      budget: 35000,
      currency: "INR",
      group_size: 2,
      pacing: "moderate",
      travel_style: "cultural",
      interests: ["Historical Forts", "Local Cuisine"],
      dietary: "",
    },
  });

  const formValues = watch();

  const handleNextStep = async () => {
    let isValid = false;
    if (step === 1) {
      isValid = await trigger(["title", "destination", "start_date", "end_date"]);
    } else if (step === 2) {
      isValid = await trigger(["budget", "currency", "group_size", "pacing"]);
    } else if (step === 3) {
      isValid = await trigger(["travel_style", "interests"]);
    }
    if (isValid) {
      setStep((prev) => Math.min(prev + 1, 4) as 1 | 2 | 3 | 4);
    }
  };

  const onSubmit = async (data: FormValues) => {
    setIsGenerating(true);
    setGenerationStatus("Creating trip draft...");
    try {
      // 1. Create Trip draft
      const trip = await apiRequest<Trip>("/api/v1/trips", {
        method: "POST",
        body: JSON.stringify({
          title: data.title,
          destination: data.destination,
          start_date: data.start_date,
          end_date: data.end_date,
          budget: data.budget,
          currency: data.currency,
          travel_style: data.travel_style,
          pacing: data.pacing,
          group_size: data.group_size,
          interests: data.interests,
          preferences: { dietary: data.dietary },
        }),
      });

      // 2. Call AI generate
      setGenerationStatus("AI is curating attractions, stays, and authentic dining...");
      await apiRequest(`/api/v1/trips/${trip.id}/generate`, {
        method: "POST",
      });

      addToast("success", "Itinerary generated successfully!");
      navigate(`/trips/${trip.id}`);
    } catch (err: unknown) {
      addToast("error", err instanceof Error ? err.message : "Generation failed");
      setIsGenerating(false);
    }
  };

  if (isGenerating) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-6">
        <div className="w-16 h-16 rounded-3xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto animate-bounce shadow-xl">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Generating Itinerary</h2>
        <p className="text-slate-500 dark:text-slate-400 text-sm max-w-md mx-auto">{generationStatus}</p>

        <div className="w-full max-w-md mx-auto h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 animate-pulse w-3/4 rounded-full" />
        </div>

        <div className="space-y-3 pt-6 max-w-sm mx-auto text-left text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Calculating travel times & geographic clusters
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Aligning activities to budget constraint
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-indigo-500 animate-spin" /> Verifying schema with Pydantic guardrails
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Stepper Progress */}
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-200 dark:border-slate-800">
        {[
          { num: 1, label: "Destination" },
          { num: 2, label: "Budget & Pacing" },
          { num: 3, label: "Interests" },
          { num: 4, label: "Review" },
        ].map((s) => (
          <div key={s.num} className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                step === s.num
                  ? "bg-indigo-600 text-white"
                  : step > s.num
                  ? "bg-emerald-500 text-white"
                  : "bg-slate-200 dark:bg-slate-800 text-slate-500"
              }`}
            >
              {step > s.num ? "✓" : s.num}
            </div>
            <span
              className={`text-xs font-medium hidden sm:inline ${
                step === s.num
                  ? "text-indigo-600 dark:text-indigo-400 font-bold"
                  : "text-slate-400"
              }`}
            >
              {s.label}
            </span>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Step 1: Destination & Dates */}
        {step === 1 && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <MapPin className="w-5 h-5 text-indigo-500" /> Where & When
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Trip Name
                </label>
                <input
                  {...register("title")}
                  placeholder="e.g. Rajasthan Heritage Getaway"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                />
                {errors.title && <p className="text-xs text-rose-500 mt-1">{errors.title.message}</p>}
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Destination City / Region
                </label>
                <input
                  {...register("destination")}
                  placeholder="e.g. Udaipur, India"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                />
                {errors.destination && (
                  <p className="text-xs text-rose-500 mt-1">{errors.destination.message}</p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                    Start Date
                  </label>
                  <input
                    type="date"
                    {...register("start_date")}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                  />
                  {errors.start_date && (
                    <p className="text-xs text-rose-500 mt-1">{errors.start_date.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                    End Date
                  </label>
                  <input
                    type="date"
                    {...register("end_date")}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                  />
                  {errors.end_date && (
                    <p className="text-xs text-rose-500 mt-1">{errors.end_date.message}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Budget & Pacing */}
        {step === 2 && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Wallet className="w-5 h-5 text-indigo-500" /> Budget & Travelers
            </h2>

            <div className="space-y-6">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-xs font-semibold uppercase text-slate-500">
                    Total Estimated Budget
                  </label>
                  <span className="text-base font-bold text-indigo-600 dark:text-indigo-400">
                    ₹{formValues.budget?.toLocaleString("en-IN")}
                  </span>
                </div>
                <Controller
                  name="budget"
                  control={control}
                  render={({ field }) => (
                    <input
                      type="range"
                      min={5000}
                      max={300000}
                      step={2500}
                      value={field.value}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      className="w-full accent-indigo-600 cursor-pointer"
                    />
                  )}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-2">
                  Group Size
                </label>
                <div className="flex items-center gap-4">
                  <Users className="w-5 h-5 text-slate-400" />
                  <Controller
                    name="group_size"
                    control={control}
                    render={({ field }) => (
                      <input
                        type="number"
                        min={1}
                        max={20}
                        value={field.value}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                        className="w-24 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                      />
                    )}
                  />
                  <span className="text-xs text-slate-400">people traveling</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-2">
                  Itinerary Pacing
                </label>
                <Controller
                  name="pacing"
                  control={control}
                  render={({ field }) => (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {PACING_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => field.onChange(opt.value)}
                          className={`p-4 rounded-2xl border text-left transition ${
                            field.value === opt.value
                              ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 ring-2 ring-indigo-500"
                              : "border-slate-200 dark:border-slate-800 hover:border-slate-300"
                          }`}
                        >
                          <p className="font-bold text-sm text-slate-900 dark:text-white">{opt.label}</p>
                          <p className="text-xs text-slate-400 mt-1">{opt.desc}</p>
                        </button>
                      ))}
                    </div>
                  )}
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Interests & Style */}
        {step === 3 && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Compass className="w-5 h-5 text-indigo-500" /> Style & Interests
            </h2>

            <div className="space-y-6">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-2">
                  Select Interests (Chips)
                </label>
                <Controller
                  name="interests"
                  control={control}
                  render={({ field }) => (
                    <div className="flex flex-wrap gap-2">
                      {AVAILABLE_INTERESTS.map((interest) => {
                        const selected = field.value?.includes(interest);
                        return (
                          <button
                            key={interest}
                            type="button"
                            onClick={() => {
                              if (selected) {
                                field.onChange(field.value.filter((i: string) => i !== interest));
                              } else {
                                field.onChange([...(field.value || []), interest]);
                              }
                            }}
                            className={`px-4 py-2 rounded-xl text-xs font-semibold transition ${
                              selected
                                ? "bg-indigo-600 text-white shadow-sm"
                                : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200"
                            }`}
                          >
                            {selected ? `✓ ${interest}` : `+ ${interest}`}
                          </button>
                        );
                      })}
                    </div>
                  )}
                />
                {errors.interests && (
                  <p className="text-xs text-rose-500 mt-1">{errors.interests.message}</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Travel Style
                </label>
                <select
                  {...register("travel_style")}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                >
                  <option value="cultural">Cultural & Heritage</option>
                  <option value="leisure">Leisure & Relaxed</option>
                  <option value="adventure">Active & Adventure</option>
                  <option value="foodie">Culinary & Gastronomy</option>
                  <option value="luxury">Luxury & Premium</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
                  Dietary / Special Preferences (Optional)
                </label>
                <input
                  {...register("dietary")}
                  placeholder="e.g. Strictly vegetarian, prefer boutique hotels"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 4 && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-indigo-500" /> Review Trip Specs
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm bg-slate-50 dark:bg-slate-800/50 p-6 rounded-2xl">
              <div>
                <p className="text-xs uppercase text-slate-400 font-semibold">Title</p>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5">{formValues.title}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate-400 font-semibold">Destination</p>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5">{formValues.destination}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate-400 font-semibold">Dates</p>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5">
                  {formValues.start_date} to {formValues.end_date}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate-400 font-semibold">Budget</p>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5">
                  ₹{formValues.budget?.toLocaleString("en-IN")} ({formValues.group_size} travelers)
                </p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate-400 font-semibold">Pacing & Style</p>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5 capitalize">
                  {formValues.pacing} • {formValues.travel_style}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase text-slate-400 font-semibold">Interests</p>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5">
                  {formValues.interests?.join(", ")}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Form Controls */}
        <div className="flex items-center justify-between pt-4">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep((prev) => (prev - 1) as 1 | 2 | 3 | 4)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold text-sm transition"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <button
              type="button"
              onClick={handleNextStep}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition shadow-sm"
            >
              Next Step <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-sm transition shadow-lg shadow-indigo-600/30"
            >
              <Sparkles className="w-4 h-4" /> Generate AI Itinerary
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
