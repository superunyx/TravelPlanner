import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import { TripSummary } from "../types";
import { Wallet, Bed, CheckCircle2, AlertCircle } from "lucide-react";

interface BudgetSummaryPanelProps {
  summary: TripSummary | null;
  stay: { name?: string; area?: string; price_per_night?: number; why?: string };
}

const CATEGORY_COLORS: Record<string, string> = {
  attraction: "#6366F1", // indigo
  dining: "#F59E0B", // amber
  transport: "#10B981", // emerald
  stay: "#8B5CF6", // purple
  activity: "#EC4899", // pink
};

export function BudgetSummaryPanel({ summary, stay }: BudgetSummaryPanelProps) {
  if (!summary) return null;

  const chartData = summary.categories
    .filter((c) => c.total_cost > 0)
    .map((c) => ({
      name: c.category.charAt(0).toUpperCase() + c.category.slice(1),
      value: c.total_cost,
      color: CATEGORY_COLORS[c.category] || "#94A3B8",
    }));

  return (
    <div className="space-y-6">
      {/* Accommodation Card */}
      {stay && stay.name && (
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 flex items-center justify-center">
              <Bed className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs uppercase font-semibold text-slate-400">Curated Accommodation</p>
              <h4 className="font-bold text-sm text-slate-900 dark:text-white">{stay.name}</h4>
            </div>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">{stay.why}</p>
          <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-100 dark:border-slate-800">
            <span className="text-slate-400">Area: {stay.area}</span>
            <span className="font-semibold text-slate-900 dark:text-white">
              ₹{Number(stay.price_per_night).toLocaleString("en-IN")} / night
            </span>
          </div>
        </div>
      )}

      {/* Sticky Budget Panel */}
      <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6 sticky top-24">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wallet className="w-5 h-5 text-indigo-500" />
            <h3 className="font-bold text-base text-slate-900 dark:text-white">Budget Overview</h3>
          </div>
          <span
            className={`text-xs font-semibold px-2.5 py-1 rounded-full flex items-center gap-1 ${
              summary.budget_status === "over_budget"
                ? "bg-rose-50 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400"
                : "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400"
            }`}
          >
            {summary.budget_status === "over_budget" ? (
              <>
                <AlertCircle className="w-3 h-3" /> Over Budget
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3 h-3" /> On Track
              </>
            )}
          </span>
        </div>

        {/* Cost vs Budget */}
        <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50">
          <div>
            <p className="text-xs text-slate-400">Estimated Total</p>
            <p className="text-lg font-extrabold text-slate-900 dark:text-white mt-0.5">
              ₹{summary.total_estimated_cost.toLocaleString("en-IN")}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Target Budget</p>
            <p className="text-lg font-extrabold text-slate-900 dark:text-white mt-0.5">
              ₹{(summary.budget || 0).toLocaleString("en-IN")}
            </p>
          </div>
        </div>

        {/* Category Breakdown Chart */}
        {chartData.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase text-slate-400 mb-2">Cost by Category</p>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={65}
                    paddingAngle={3}
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val?: unknown) =>
                      `₹${Number(val || 0).toLocaleString("en-IN")}`
                    }
                    contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1)" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-1.5 mt-2">
              {summary.categories.map((cat) => (
                <div key={cat.category} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: CATEGORY_COLORS[cat.category] || "#94A3B8" }}
                    />
                    <span className="capitalize text-slate-600 dark:text-slate-300">
                      {cat.category}
                    </span>
                  </div>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    ₹{cat.total_cost.toLocaleString("en-IN")} ({cat.percentage}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
