"use client";

import { motion, AnimatePresence } from "framer-motion";
import { 
  History, 
  User as UserIcon, 
  Settings, 
  Power,
  Globe,
  Plus,
  ArrowUpRight,
  LogOut,
  Sliders,
  Bell,
  LayoutDashboard,
  Cpu,
  Target,
  Briefcase
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/store/auth";
import api from "@/lib/api";
import { toast } from "sonner";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Logo } from "@/components/Logo";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, updateUser, logout } = useAuth();
  const [active, setActive] = useState(user?.agent_enabled ?? false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setActive(user?.agent_enabled ?? false);
  }, [user]);

  const toggleAgent = async () => {
    try {
      const newStatus = !active;
      await api.put('/users/profile', { agent_enabled: newStatus });
      updateUser({ ...user!, agent_enabled: newStatus });
      setActive(newStatus);
      toast.success(`Agent ${newStatus ? 'Activated' : 'Paused'}`);
    } catch (err) {
      toast.error("Failed to toggle agent");
    }
  };

  const navItems = [
    { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { label: "Applications", href: "/dashboard/applications", icon: History },
    { label: "Role Strategy", href: "/dashboard/preferences", icon: Target },
    { label: "Profile", href: "/dashboard/profile", icon: UserIcon },
    { label: "Configure", href: "/dashboard/settings", icon: Settings },
  ];

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex font-main selection:bg-accent-purple selection:text-white">
      {/* Sidebar - Command Panel */}
      <aside className="w-80 border-r border-slate-100 bg-white flex flex-col hidden lg:flex fixed h-full z-50 overflow-hidden shadow-2xl">
        <div className="p-12 mb-8 flex flex-col items-center">
          <Logo theme="light" />
        </div>

        <nav className="flex-grow px-8 space-y-3">
          <div className="px-5 mb-8">
            <span className="text-[10px] uppercase tracking-[0.6em] font-black text-slate-300">Operator Protocol</span>
          </div>
          {navItems.map((item) => (
            <Link 
              key={item.label} 
              href={item.href}
              className={`flex items-center justify-between px-6 py-4 rounded-2xl transition-all group relative border-2 ${
                pathname === item.href 
                ? 'bg-accent-purple/5 text-accent-purple border-accent-purple/10' 
                : 'text-slate-400 hover:text-accent-purple hover:bg-slate-50 border-transparent hover:border-slate-100'
              }`}
            >
              <div className="flex items-center gap-4">
                <item.icon className={`w-4 h-4 transition-colors ${pathname === item.href ? 'text-accent-purple' : 'text-slate-300 group-hover:text-accent-purple'}`} />
                <span className="text-xs font-black uppercase tracking-[0.2em]">{item.label}</span>
              </div>
              {pathname === item.href && (
                  <motion.div layoutId="nav-active" className="w-2 h-2 rounded-full bg-accent-purple shadow-[0_0_15px_rgba(99,102,241,0.5)]" />
              )}
            </Link>
          ))}
        </nav>

        <div className="mt-auto">
            {/* Agent Control Block */}
            <div className="m-8 p-10 bg-slate-50 rounded-[40px] border border-slate-100 space-y-8 relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-20 h-20 bg-accent-purple/5 blur-2xl rounded-full translate-x-1/2 -translate-y-1/2" />
                
                <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black tracking-[0.4em] text-slate-300 uppercase">DEVA_CONCIERGE</span>
                    <button 
                        onClick={toggleAgent}
                        className={`w-12 h-6 rounded-full relative transition-all duration-700 ${active ? 'bg-accent-purple shadow-lg' : 'bg-slate-200'}`}
                    >
                        <motion.div 
                            animate={{ x: active ? 26 : 4 }}
                            className="absolute top-1 w-4 h-4 rounded-full bg-white shadow-xl"
                        />
                    </button>
                </div>
                <div className="flex items-center gap-5">
                    <div className={`w-12 h-12 rounded-2xl bg-white flex items-center justify-center border shadow-sm ${active ? 'border-accent-purple/40 text-accent-purple' : 'border-slate-100 text-slate-300'}`}>
                        <Power className="w-5 h-5 transition-colors" />
                    </div>
                    <div>
                        <p className="text-[10px] font-black uppercase tracking-[0.4em]">{active ? 'DEPLOYED' : 'STANDBY'}</p>
                        <p className="text-[9px] text-slate-400 mt-1 font-extrabold tracking-tight uppercase">Activity @ 06:00 UTC</p>
                    </div>
                </div>
            </div>

            {/* Admin Footer */}
            <div className="p-10 border-t border-slate-100 flex items-center gap-5 bg-white relative">
              <div className="w-12 h-12 rounded-2xl bg-accent-purple/5 flex items-center justify-center font-bold text-accent-purple text-lg border-2 border-accent-purple/10 shadow-sm transition-all hover:scale-105 active:scale-95">
                {user?.full_name?.[0] || 'A'}
              </div>
              <div className="flex-grow min-w-0">
                <p className="text-sm font-black text-slate-900 truncate tracking-tight">{user?.full_name || 'Operator'}</p>
                <p className="text-[9px] text-accent-gold font-black uppercase tracking-[0.4em] mt-1">{user?.tier || 'Premium'} Member</p>
              </div>
              <button 
                onClick={logout}
                className="text-slate-300 hover:text-red-500 transition-colors p-3 hover:bg-slate-50 rounded-xl"
                title="Disconnect"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
        </div>
      </aside>

      {/* Main Command Window */}
      <main className="flex-grow lg:ml-80 bg-slate-50 min-h-screen">
        {/* Executive Header */}
        <header className="h-28 px-16 flex items-center justify-between border-b border-slate-100 sticky top-0 bg-slate-50/80 backdrop-blur-3xl z-40">
          <div className="flex items-center gap-8 text-[11px] font-sans text-slate-400 font-extrabold uppercase tracking-[0.5em]">
            <span className="flex items-center gap-3 text-slate-900">NODE_01</span>
            <div className={`w-2 h-2 rounded-full ${active ? 'bg-accent-purple shadow-[0_0_10px_rgba(99,102,241,0.5)] animate-pulse' : 'bg-slate-300'}`} />
            <span className="opacity-30">/</span>
            <span className="text-slate-500 tracking-[0.3em] font-black">{pathname.split('/').pop() || 'overview'}</span>
          </div>

          <div className="flex items-center gap-12">
            <div className="hidden md:flex flex-col items-end gap-1.5">
                <span className="text-sm font-black text-slate-900">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })} UTC</span>
                <span className="text-[9px] text-slate-300 uppercase tracking-[0.6em] font-black">Sync Operational</span>
            </div>
            <button className="w-14 h-14 flex items-center justify-center rounded-2xl bg-white border border-slate-100 hover:border-accent-purple/30 hover:bg-slate-50 transition-all relative group shadow-sm transition-all active:scale-95">
                <Bell className="w-5 h-5 text-slate-300 group-hover:text-accent-purple transition-colors" />
                <span className="absolute top-5 right-5 w-2.5 h-2.5 rounded-full bg-accent-purple border-[3px] border-white shadow-sm" />
            </button>
          </div>
        </header>

        {/* Content Viewport */}
        <div className="p-16 max-w-[1500px] mx-auto min-h-[calc(100vh-7rem)]">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
