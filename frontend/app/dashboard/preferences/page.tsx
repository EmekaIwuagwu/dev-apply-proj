"use client";

import { motion, AnimatePresence } from "framer-motion";
import { 
  Sliders, 
  Plus, 
  X, 
  Save, 
  Info,
  Building2,
  MapPin,
  DollarSign,
  Briefcase,
  ShieldCheck,
  ChevronRight,
  Target
} from "lucide-react";
import { useState } from "react";

export default function PreferencesPage() {
  const [titles, setTitles] = useState(["Senior Backend Engineer", "Python Architect", "AI Solutions Engineer"]);
  const [skills, setSkills] = useState(["Python", "Rust", "FastAPI", "React", "Next.js", "Docker", "PostgreSQL"]);

  return (
    <div className="space-y-12 pb-20">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 px-2">
        <div>
          <h1 className="text-4xl font-extrabold uppercase tracking-tight text-slate-900 mb-2">Target Strategy</h1>
          <p className="text-slate-400 text-sm font-bold">Configure the neural targeting parameters for your autonomous job search.</p>
        </div>
        <button className="btn-purple flex items-center gap-3 px-10 py-4 shadow-xl active:scale-95 transition-all">
            <Save className="w-4 h-4" /> Save Strategy
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div className="space-y-10">
            {/* Job Titles */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-8 transition-all hover:border-accent-purple/20">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900 mb-8">
                    <Briefcase className="w-4 h-4 text-accent-purple" /> Primary Targets
                </h3>
                <div className="flex flex-wrap gap-3">
                    {titles.map(t => (
                        <div key={t} className="bg-slate-50 border border-slate-100 px-5 py-2.5 rounded-2xl text-xs font-bold text-slate-600 flex items-center gap-3 group transition-all hover:border-accent-purple/30 hover:bg-white shadow-sm">
                            {t}
                            <button className="text-slate-300 hover:text-red-500 transition-colors"><X className="w-4 h-4" /></button>
                        </div>
                    ))}
                    <button className="border-2 border-dashed border-slate-100 px-5 py-2.5 rounded-2xl text-xs text-slate-300 hover:text-accent-purple hover:border-accent-purple/30 transition-all flex items-center gap-3 font-black uppercase tracking-widest">
                        <Plus className="w-4 h-4" /> Add Title
                    </button>
                </div>
            </div>

            {/* Skills */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-8 transition-all hover:border-accent-purple/20">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900 mb-8">
                    <Sliders className="w-4 h-4 text-accent-gold" /> Critical Tech Node
                </h3>
                <div className="flex flex-wrap gap-3">
                    {skills.map(s => (
                        <div key={s} className="bg-accent-gold/5 border border-accent-gold/20 px-5 py-2.5 rounded-2xl text-xs font-bold text-accent-gold flex items-center gap-3 group transition-all hover:bg-accent-gold/10 shadow-sm">
                            {s}
                            <button className="text-accent-gold/40 hover:text-red-500 transition-colors"><X className="w-4 h-4" /></button>
                        </div>
                    ))}
                    <button className="border-2 border-dashed border-slate-100 px-5 py-2.5 rounded-2xl text-xs text-slate-300 hover:text-accent-purple hover:border-accent-purple/30 transition-all flex items-center gap-3 font-black uppercase tracking-widest">
                        <Plus className="w-4 h-4" /> Add Skill
                    </button>
                </div>
            </div>
            
            {/* Excluded Companies */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-8 transition-all hover:border-accent-purple/20">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900 mb-6">
                    <Building2 className="w-4 h-4 text-red-400" /> Negative Constraints
                </h3>
                <div className="relative group">
                    <input className="w-full bg-slate-50 border-2 border-slate-50 p-5 rounded-2xl focus:border-red-400 focus:bg-white outline-none text-sm transition-all font-bold placeholder:text-slate-300" placeholder="Exclude specific company domains..." />
                    <Info className="absolute right-5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-200 group-hover:text-red-400 transition-colors" />
                </div>
            </div>
        </div>

        <div className="space-y-10">
            {/* Parameters */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-10 transition-all hover:border-accent-purple/20">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900">
                    <MapPin className="w-4 h-4 text-accent-purple" /> Selection Matrix
                </h3>
                
                <div className="space-y-10">
                    <div className="space-y-4">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black block ml-1">Experience Logic</label>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                            {["Junior", "Mid", "Senior", "Lead"].map(lvl => (
                                <button key={lvl} className={`px-4 py-3.5 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all border-2 ${
                                    lvl === "Senior" ? 'bg-accent-purple border-accent-purple text-white shadow-lg' : 'bg-slate-50 border-slate-50 text-slate-400 hover:border-slate-200'
                                }`}>{lvl}</button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-4">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black block ml-1">Work Protocol</label>
                        <div className="flex gap-4">
                            {["Remote", "Hybrid", "On-site"].map(type => (
                                <button key={type} className={`px-8 py-3.5 rounded-full text-[10px] font-black uppercase tracking-[0.3em] transition-all border-2 ${
                                    type === "Remote" ? 'bg-accent-purple/10 border-accent-purple text-accent-purple' : 'bg-slate-50 border-slate-50 text-slate-400 hover:border-slate-200'
                                }`}>{type}</button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-4">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black block ml-1">Value Threshold (Minimum)</label>
                        <div className="relative group">
                            <DollarSign className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
                            <input className="w-full bg-slate-50 border-2 border-slate-50 p-5 pl-14 rounded-2xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold text-slate-900" defaultValue="140,000" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Performance Mode */}
            <div className="bg-black p-10 rounded-[40px] text-white shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-48 h-48 bg-accent-purple/10 blur-[80px] rounded-full translate-x-1/2 -translate-y-1/2" />
                
                <div className="flex justify-between items-center mb-10 relative z-10">
                    <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-white">
                        <Target className="w-4 h-4 text-accent-gold" /> Throughput Mode
                    </h3>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-accent-gold shadow-[0_0_10px_var(--accent-gold)]" />
                        <span className="text-[10px] font-black tracking-widest text-accent-gold uppercase">Optimized</span>
                    </div>
                </div>
                <div className="space-y-8 relative z-10">
                    <div className="flex justify-between items-end">
                        <div className="space-y-1">
                            <span className="text-[10px] uppercase tracking-[0.4em] text-neutral-500 font-black">Daily Acquisition Cap</span>
                            <div className="text-3xl font-extrabold uppercase tracking-tight">15 Nodes</div>
                        </div>
                        <span className="text-[10px] font-black text-accent-gold bg-accent-gold/10 px-4 py-1.5 rounded-full border border-accent-gold/20 uppercase tracking-widest">75% Capacity</span>
                    </div>
                    <div className="h-2 w-full bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                        <motion.div initial={{ width: 0 }} animate={{ width: "75%" }} transition={{ duration: 1.5, ease: "easeOut" }} className="h-full bg-accent-gold shadow-[0_0_20px_rgba(212,175,55,0.4)]" />
                    </div>
                    <div className="p-6 bg-neutral-900 shadow-inner rounded-3xl border border-white/5">
                        <p className="text-[11px] text-neutral-400 leading-relaxed font-bold">
                            Balanced throughput minimizes rate-limiting on external Company Nodes. Tier 02 Operators can scale to 50 Daily Nodes.
                        </p>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}
