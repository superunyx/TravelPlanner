import { useUIStore } from "../store/uiStore";
import { Loader2 } from "lucide-react";

export function ServerWarmupBanner() {
  const isServerWakingUp = useUIStore((s) => s.isServerWakingUp);

  if (!isServerWakingUp) return null;

  return (
    <div className="bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 text-white px-4 py-2 text-xs sm:text-sm font-medium flex items-center justify-center gap-2 shadow-inner transition-all animate-pulse">
      <Loader2 className="w-4 h-4 animate-spin shrink-0" />
      <span>
        <strong>Waking up the server (~30s)...</strong> Render free tier instances spin down when idle. Your requests will process shortly.
      </span>
    </div>
  );
}
