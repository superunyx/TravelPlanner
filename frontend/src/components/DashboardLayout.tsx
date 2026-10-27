import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { useUIStore } from "../store/uiStore";
import {
  Compass,
  MapPin,
  PlusCircle,
  Sun,
  Moon,
  LogOut,
  User as UserIcon,
} from "lucide-react";

interface LayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: LayoutProps) {
  const { user, signOut } = useAuthStore();
  const { isDarkMode, toggleDarkMode } = useUIStore();
  const location = useLocation();

  const navItems = [
    { name: "My Trips", path: "/dashboard", icon: Compass },
    { name: "Plan New Trip", path: "/trips/new", icon: PlusCircle },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex transition-colors">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col shrink-0">
        <div className="p-6 flex items-center gap-3 border-b border-slate-100 dark:border-slate-800">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <MapPin className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-base leading-none bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              TravelPlanner
            </h1>
            <span className="text-xs text-slate-500 dark:text-slate-400">AI Itinerary Pro</span>
          </div>
        </div>

        <nav className="p-4 space-y-1.5 flex-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-semibold shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100"
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User Card */}
        <div className="p-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 flex items-center justify-center shrink-0">
              <UserIcon className="w-4 h-4 text-slate-600 dark:text-slate-300" />
            </div>
            <div className="truncate text-xs">
              <p className="font-medium truncate">{user?.email || "Traveler"}</p>
              <span className="text-slate-400">Online</span>
            </div>
          </div>
          <button
            onClick={() => void signOut()}
            title="Sign out"
            className="p-1.5 text-slate-400 hover:text-rose-500 dark:hover:text-rose-400 transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-30">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
            {location.pathname === "/dashboard" && "Dashboard"}
            {location.pathname === "/trips/new" && "Smart Trip Planner"}
            {location.pathname.startsWith("/trips/") && location.pathname !== "/trips/new" && "Itinerary Studio"}
          </h2>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-xl text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              title="Toggle theme"
            >
              {isDarkMode ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-slate-600" />}
            </button>
            <Link
              to="/trips/new"
              className="hidden sm:flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 transition"
            >
              <PlusCircle className="w-4 h-4" /> New Trip
            </Link>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 p-8 max-w-7xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
