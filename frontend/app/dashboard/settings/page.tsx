"use client";

import { motion } from "framer-motion";
import { 
  Settings, 
  Bell, 
  ShieldCheck, 
  CreditCard, 
  Trash2,
  Lock,
  Smartphone,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  Shield
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function SettingsPage() {
  const [notifs, setNotifs] = useState([
    { title: "Application Success", desc: "Get an email every time the agent submits an application.", active: true },
    { title: "Daily Summary", desc: "Receive a roundup of all agent activity at 08:00 AM.", active: false },
    { title: "System Alerts", desc: "Notification for rate-limits, errors, or required actions.", active: true },
  ]);

  const toggleNotif = (index: number) => {
    const newNotifs = [...notifs];
    newNotifs[index].active = !newNotifs[index].active;
    setNotifs(newNotifs);
  };

  return (
    <div className="space-y-12 pb-20">
      <div className="px-2">
        <h1 className="text-4xl font-extrabold uppercase tracking-tight text-slate-900 mb-2">Protocol Settings</h1>
        <p className="text-slate-400 text-sm font-bold">Configure your account security and operational parameters.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        <div className="lg:col-span-2 space-y-10">
            {/* Account Settings */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-10 transition-all hover:border-accent-purple/20 group">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900 mb-8 font-sans">
                    <Lock className="w-4 h-4 text-accent-purple" /> Security & Access
                </h3>
                
                <div className="space-y-8">
                    <div className="space-y-3">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black block ml-1">Current Active Password</label>
                        <div className="relative">
                            <input type="password" underline="true" className="w-full bg-slate-50 border-2 border-slate-50 p-5 rounded-2xl outline-none text-sm font-bold text-slate-400 cursor-not-allowed" value="••••••••••••" disabled />
                            <Lock className="absolute right-5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-200" />
                        </div>
                    </div>
                    <button className="px-8 py-3.5 bg-white border border-slate-100 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:border-accent-purple hover:text-accent-purple transition-all shadow-sm active:scale-95">
                        Refresh Credentials
                    </button>
                    
                    <div className="h-px bg-slate-50 w-full" />
                    
                    <div className="flex items-center justify-between p-8 bg-slate-50/50 rounded-[32px] border border-slate-100 transition-all group-hover:bg-white group-hover:border-accent-purple/10">
                        <div className="flex items-center gap-6">
                            <div className="w-14 h-14 rounded-2xl bg-white border border-slate-100 flex items-center justify-center text-accent-purple shadow-sm">
                                <Smartphone className="w-6 h-6" />
                            </div>
                            <div className="space-y-1">
                                <h4 className="text-sm font-extrabold uppercase tracking-tight">Two-Factor Auth</h4>
                                <p className="text-[11px] text-slate-400 font-bold">TOTP Protocol: ACTIVE</p>
                            </div>
                        </div>
                        <span className="text-[10px] font-black text-accent-purple bg-accent-purple/5 border border-accent-purple/20 px-4 py-2 rounded-full uppercase tracking-widest">Protocol Enabled</span>
                    </div>
                </div>
            </div>

            {/* Notifications */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-10 transition-all hover:border-accent-purple/20">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900 mb-8 font-sans">
                    <Bell className="w-4 h-4 text-accent-gold" /> Communication Loop
                </h3>
                
                <div className="space-y-6">
                    {notifs.map((notif, i) => (
                        <div key={i} className="flex items-center justify-between p-8 bg-slate-50/30 rounded-[32px] border border-slate-50 hover:border-accent-purple/10 hover:bg-white transition-all group cursor-pointer" onClick={() => toggleNotif(i)}>
                            <div className="space-y-2">
                                <h4 className="text-sm font-extrabold uppercase tracking-tight text-slate-800 group-hover:text-accent-purple transition-colors">{notif.title}</h4>
                                <p className="text-[11px] text-slate-400 font-bold leading-relaxed max-w-sm">{notif.desc}</p>
                            </div>
                            <button className={`w-14 h-7 rounded-full relative transition-all duration-500 ${notif.active ? 'bg-accent-purple shadow-md' : 'bg-slate-200'}`}>
                                <motion.div 
                                    animate={{ x: notif.active ? 30 : 4 }}
                                    className="absolute top-1.5 w-4 h-4 rounded-full bg-white shadow-sm"
                                />
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Danger Zone */}
            <div className="bg-red-50/20 p-10 rounded-[40px] border border-red-100 space-y-8">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-red-500 font-sans">
                    <Trash2 className="w-4 h-4" /> Purge Protocol
                </h3>
                <p className="text-sm text-red-400/80 font-bold leading-relaxed max-w-xl">
                    Once you initiate account purging, the operation is irreversible. All application history, neural blueprint data, and custom weights will be permanently erased.
                </p>
                <button className="px-10 py-4 border-2 border-red-100 text-red-500 hover:bg-red-500 hover:text-white transition-all rounded-full text-[11px] font-black uppercase tracking-widest shadow-sm active:scale-95">
                    Deactivate & Purge
                </button>
            </div>
        </div>

        {/* Right: Subscription Detail */}
        <div className="space-y-10">
            <div className="bg-black p-10 rounded-[40px] text-white shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-64 h-64 bg-accent-purple/10 blur-[100px] rounded-full translate-x-1/3 -translate-y-1/3" />
                
                <div className="flex justify-between items-start mb-12 relative z-10">
                    <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center justify-center text-accent-gold shadow-sm group-hover:scale-110 transition-transform">
                        <CreditCard className="w-8 h-8" />
                    </div>
                    <span className="text-[10px] font-black text-accent-gold border-2 border-accent-gold/20 px-5 py-2 rounded-full uppercase tracking-widest bg-accent-gold/5">LICENSED</span>
                </div>
                
                <div className="space-y-2 mb-10 relative z-10">
                    <h3 className="text-[11px] font-black uppercase tracking-[0.4em] text-neutral-500 font-sans">Deployment Tier</h3>
                    <div className="text-4xl font-extrabold uppercase tracking-tighter">Enterprise PRO</div>
                </div>

                <div className="space-y-6 mb-10 relative z-10">
                    <div className="flex justify-between items-center text-xs font-bold px-1">
                        <span className="text-neutral-500 uppercase tracking-widest text-[9px]">Cycles Refresh</span>
                        <span className="text-white">APR 05, 2026</span>
                    </div>
                    <div className="flex justify-between items-center text-xs font-bold px-1">
                        <span className="text-neutral-500 uppercase tracking-widest text-[9px]">Licensing Rate</span>
                        <span className="text-white">$19.00 / CYCLE</span>
                    </div>
                </div>

                <div className="pt-8 border-t border-white/5 space-y-4 relative z-10">
                    <button className="w-full bg-accent-gold text-white py-4 rounded-2xl text-[11px] font-black uppercase tracking-widest flex items-center justify-center gap-3 hover:bg-white hover:text-black transition-all shadow-xl active:scale-95">
                        Billing Portal <ExternalLink className="w-4 h-4" />
                    </button>
                    <Link href="/pricing" className="w-full bg-white/[0.02] border border-white/5 text-neutral-400 py-4 rounded-2xl text-[11px] font-black uppercase tracking-widest flex items-center justify-center gap-3 hover:bg-white/[0.05] transition-all">
                        Upgrade Deployment Tier
                    </Link>
                </div>
            </div>

            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm flex flex-col items-center gap-6 text-center group hover:border-accent-purple/20 transition-all">
                <div className="w-16 h-16 rounded-2xl bg-green-50 border border-green-100 flex items-center justify-center text-green-500 shadow-sm group-hover:scale-110 transition-transform">
                    <ShieldCheck className="w-8 h-8" />
                </div>
                <div className="space-y-2">
                    <div className="text-sm font-extrabold uppercase tracking-tight text-slate-800">Bank-Grade Security</div>
                    <p className="text-[11px] text-slate-400 font-bold uppercase tracking-widest">Encrypted Vault_Protected</p>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}
