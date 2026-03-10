"use client";

import { motion } from "framer-motion";
import { 
  User as UserIcon, 
  Mail, 
  Linkedin, 
  FileText, 
  Camera, 
  Save,
  CheckCircle2,
  ShieldCheck,
  Globe,
  Plus
} from "lucide-react";
import { useState, useEffect } from "react";
import { useAuth } from "@/store/auth";
import api from "@/lib/api";
import { toast } from "sonner";

export default function ProfilePage() {
  const { user, updateUser } = useAuth();
  const [formData, setFormData] = useState({
    full_name: user?.full_name || "",
    email: user?.email || "",
    bio: user?.bio || "",
    linkedin_url: user?.linkedin_url || "",
  });

  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name,
        email: user.email,
        bio: user.bio,
        linkedin_url: user.linkedin_url,
      });
    }
  }, [user]);

  const handleSave = async () => {
    try {
      const resp = await api.put("/users/profile", formData);
      updateUser(resp.data);
      toast.success("Identity Matrix Updated.");
    } catch (err) {
      toast.error("Failed to update profile nodes.");
    }
  };

  return (
    <div className="space-y-12 pb-20">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 px-2">
        <div>
          <h1 className="text-4xl font-extrabold uppercase tracking-tight text-slate-900 mb-2">Operator Identity</h1>
          <p className="text-slate-400 text-sm font-bold">Manage your professional credentials and neural blueprint data.</p>
        </div>
        <button onClick={handleSave} className="btn-purple flex items-center gap-3 px-10 py-4 shadow-xl active:scale-95 transition-all">
            <Save className="w-4 h-4" /> Save Identity
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        <div className="lg:col-span-2 space-y-10">
            {/* Personal Details */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-10 transition-all hover:border-accent-purple/20">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900 mb-8 font-sans">
                    <UserIcon className="w-4 h-4 text-accent-purple" /> Personal Core
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-3">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black block ml-1">Legal Full Name</label>
                        <input 
                            className="w-full bg-slate-50 border-2 border-slate-50 p-5 rounded-2xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all text-slate-900 font-bold" 
                            value={formData.full_name}
                            onChange={e => setFormData({...formData, full_name: e.target.value})}
                        />
                    </div>
                    <div className="space-y-3 opacity-60">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black block ml-1">Email Endpoint (Protected)</label>
                        <div className="relative group">
                            <Mail className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
                            <input className="w-full bg-slate-50 border-2 border-slate-50 p-5 pl-14 rounded-2xl outline-none text-sm cursor-not-allowed font-bold" value={formData.email} readOnly />
                        </div>
                    </div>
                </div>

                <div className="space-y-3">
                    <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black block ml-1">Experience Summary</label>
                    <textarea 
                        className="w-full bg-slate-50 border-2 border-slate-50 p-6 rounded-[32px] focus:border-accent-purple focus:bg-white outline-none text-sm h-48 resize-none text-slate-900 leading-relaxed font-bold transition-all" 
                        value={formData.bio}
                        onChange={e => setFormData({...formData, bio: e.target.value})}
                        placeholder="Detail your primary architectural achievements and career trajectory..."
                    />
                </div>
            </div>

            {/* Resume Management */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-8 transition-all hover:border-accent-purple/20">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900 mb-6 font-sans">
                    <FileText className="w-4 h-4 text-accent-gold" /> Neural Blueprint (Resume)
                </h3>
                <div className="flex flex-col md:flex-row items-center justify-between p-8 bg-slate-50/50 rounded-[32px] border border-slate-100 gap-6 transition-all hover:border-accent-gold/20">
                    <div className="flex items-center gap-6">
                        <div className="w-16 h-16 rounded-2xl bg-white border border-slate-100 flex items-center justify-center shadow-sm text-accent-gold">
                            <FileText className="w-8 h-8" />
                        </div>
                        <div>
                            <p className="text-base font-extrabold text-slate-900 truncate max-w-[200px]">current_resume.pdf</p>
                            <p className="text-[10px] text-slate-300 font-black uppercase tracking-[0.2em] mt-1">Verified Nodes_OK</p>
                        </div>
                    </div>
                    <div className="flex gap-4 w-full md:w-auto">
                        <button className="flex-grow md:flex-grow-0 px-8 py-3.5 bg-white border border-slate-100 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:border-accent-purple hover:text-accent-purple transition-all shadow-sm active:scale-95">
                            Update Blueprint
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div className="space-y-10">
            {/* Social / External */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-10 transition-all hover:border-accent-purple/20">
                <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-slate-900 mb-8 font-sans">
                    <Linkedin className="w-4 h-4 text-accent-purple" /> Global Feed (LinkedIn)
                </h3>
                <div className="space-y-6">
                    <div className="space-y-3">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black block ml-1">Portfolio URL</label>
                        <div className="relative group">
                            <Globe className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
                            <input 
                                className="w-full bg-slate-50 border-2 border-slate-50 p-5 pl-14 rounded-2xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold text-slate-900" 
                                value={formData.linkedin_url}
                                onChange={e => setFormData({...formData, linkedin_url: e.target.value})}
                                placeholder="https://linkedin.com/in/operator"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Profile Health */}
            <div className="bg-black p-10 rounded-[40px] text-white shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-48 h-48 bg-accent-purple/10 blur-[80px] rounded-full translate-x-1/2 -translate-y-1/2" />
                
                <div className="flex justify-between items-center mb-10 relative z-10">
                    <h3 className="text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-3 text-white font-sans">
                        <CheckCircle2 className="w-4 h-4 text-green-400" /> Matrix Health
                    </h3>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_10px_rgba(74,222,128,0.5)]" />
                        <span className="text-[10px] font-black tracking-widest text-green-400 uppercase">Synced</span>
                    </div>
                </div>
                <div className="space-y-8 relative z-10">
                    <div className="flex justify-between items-end">
                        <div className="space-y-1">
                            <span className="text-[10px] uppercase tracking-[0.4em] text-neutral-500 font-black">Sync Completion</span>
                            <div className="text-3xl font-extrabold uppercase tracking-tight">100% Core</div>
                        </div>
                    </div>
                    <div className="h-2 w-full bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                        <motion.div initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: 1.5, ease: "easeOut" }} className="h-full bg-green-400 shadow-[0_0_20px_rgba(74,222,128,0.4)]" />
                    </div>
                    <div className="p-8 bg-neutral-900 shadow-inner rounded-[32px] border border-white/5 space-y-4">
                        <ShieldCheck className="w-8 h-8 text-accent-purple" />
                        <p className="text-[11px] text-neutral-400 leading-relaxed font-bold">
                            Your Identity Matrix is fully optimized. The agent has sufficient context to articulate complex value propositions on your behalf.
                        </p>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}
