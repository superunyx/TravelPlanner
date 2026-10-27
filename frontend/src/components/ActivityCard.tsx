import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Activity, ActivityType } from "../types";
import {
  GripVertical,
  Trash2,
  Edit2,
  Check,
  X,
  Compass,
  Utensils,
  Car,
  Bed,
  MapPin,
  Clock,
  Coins,
} from "lucide-react";

interface ActivityCardProps {
  activity: Activity;
  index: number;
  onUpdate: (updated: Activity) => void;
  onDelete: () => void;
}

const TYPE_ICONS: Record<ActivityType, typeof Compass> = {
  attraction: Compass,
  dining: Utensils,
  transport: Car,
  stay: Bed,
  activity: Compass,
};

export function ActivityCard({
  activity,
  index,
  onUpdate,
  onDelete,
}: ActivityCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(activity.title);
  const [editCost, setEditCost] = useState(activity.est_cost);
  const [editDesc, setEditDesc] = useState(activity.description);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `activity-${index}-${activity.title}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const Icon = TYPE_ICONS[activity.type] || Compass;

  const handleSaveEdit = () => {
    onUpdate({
      ...activity,
      title: editTitle,
      est_cost: Number(editCost),
      description: editDesc,
    });
    setIsEditing(false);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-start gap-4 transition"
    >
      <button
        {...attributes}
        {...listeners}
        className="text-slate-300 dark:text-slate-600 hover:text-slate-500 cursor-grab active:cursor-grabbing p-1 mt-1"
        title="Drag to reorder"
      >
        <GripVertical className="w-4 h-4" />
      </button>

      <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 mt-0.5">
        <Icon className="w-5 h-5" />
      </div>

      <div className="flex-1 min-w-0">
        {isEditing ? (
          <div className="space-y-3">
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-bold text-slate-900 dark:text-white"
            />
            <textarea
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              rows={2}
              className="w-full px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-600 dark:text-slate-300"
            />
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400">Est. Cost (₹):</span>
              <input
                type="number"
                value={editCost}
                onChange={(e) => setEditCost(Number(e.target.value))}
                className="w-24 px-2 py-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-semibold"
              />
              <div className="flex-1 flex justify-end gap-1.5">
                <button
                  onClick={() => setIsEditing(false)}
                  className="p-1 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-4 h-4" />
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="p-1 text-emerald-600 hover:text-emerald-500"
                >
                  <Check className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between gap-2">
              <h4 className="font-bold text-sm text-slate-900 dark:text-white truncate">
                {activity.title}
              </h4>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => setIsEditing(true)}
                  className="p-1 text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition"
                  title="Edit activity"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={onDelete}
                  className="p-1 text-slate-400 hover:text-rose-500 transition"
                  title="Remove activity"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
              {activity.description}
            </p>

            <div className="mt-3 flex flex-wrap items-center gap-4 text-xs font-medium text-slate-400">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                {activity.start_time} - {activity.end_time}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                {activity.location}
              </span>
              <span className="flex items-center gap-1 font-semibold text-slate-700 dark:text-slate-300">
                <Coins className="w-3.5 h-3.5 text-amber-500" />
                ₹{Number(activity.est_cost).toLocaleString("en-IN")}
              </span>
              {activity.travel_time_from_previous_min > 0 && (
                <span className="text-slate-400">
                  +{activity.travel_time_from_previous_min}m transit
                </span>
              )}
            </div>

            {activity.tips && (
              <p className="mt-2.5 text-[11px] bg-indigo-50/60 dark:bg-indigo-950/30 text-indigo-700 dark:text-indigo-300 px-3 py-1.5 rounded-lg">
                💡 Tip: {activity.tips}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
