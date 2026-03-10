"use client";

import { motion, AnimatePresence } from "framer-motion";
import { User as UserIcon, Mail, Lock, Linkedin, FileText, ArrowRight, CheckCircle2, ShieldCheck, Globe, Briefcase, Plus, Terminal, Cpu, Rocket, ChevronRight, Binary } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/store/auth";
import api from "@/lib/api";
import { toast } from "sonner";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    salutation: "Mr",
    fullName: "",
    email: "",
    tel: "",
    password: "",
    linkedin: "",
    bio: "",
    jobTitles: [] as string[],
    skills: [] as string[],
    experience: "Mid",
    resume: null as File | null,
    resumeBase64: "",
  });

  const { setAuth } = useAuth();
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFormData({ ...formData, resume: file });
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        setFormData(prev => ({ ...prev, resumeBase64: base64String.split(',')[1] }));
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const payload = {
        email: formData.email,
        full_name: formData.fullName,
        salutation: formData.salutation,
        telephone: formData.tel || "N/A",
        password: formData.password,
        linkedin_url: formData.linkedin || "",
        bio: formData.bio || "Agent-initialized profile.",
        resume_base64: formData.resumeBase64,
        resume_filename: formData.resume?.name || "resume.pdf",
        tier: "free"
      };

      const resp = await api.post("/auth/register", payload);
      setAuth(resp.data.user, resp.data.access_token);
      toast.success("Identity Matrix Initialized. Welcome Operator.");
      router.push("/dashboard");
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || "Registration failed. Check your data.";
      toast.error(typeof errorDetail === 'string' ? errorDetail : "Error initializing matrix.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white font-main selection:bg-accent-purple selection:text-white flex flex-col">
      <Header />

      <main className="flex-grow flex flex-col lg:flex-row min-h-screen pt-20 lg:pt-0">
        {/* Left Visual Panel - High Fidelity imagery */}
        <div className="hidden lg:flex lg:w-2/5 bg-black relative overflow-hidden items-center justify-center p-20 sticky top-0 h-screen">
          <div className="absolute inset-0 opacity-40">
             <img 
               src="https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=2070&auto=format&fit=crop" 
               className="w-full h-full object-cover"
               alt="Digital Core"
             />
          </div>
          <div className="absolute inset-0 bg-gradient-to-br from-accent-purple/30 via-transparent to-black" />
          
          <div className="relative z-10 w-full max-w-md">
             <div className="badge-purple bg-white shadow-2xl px-6 py-2 rounded-full border border-accent-purple/20 text-[10px] uppercase tracking-[0.5em] font-black text-accent-purple mb-12 inline-block">
                Deployment Stage_{step}
             </div>
             <h2 className="text-7xl font-extrabold text-white leading-[0.85] tracking-tighter uppercase mb-10">
               Initialize <br /> Your Agent.
             </h2>
             
             <div className="space-y-6 mt-20">
                {[
                    { n: 1, label: "Identity Matrix" },
                    { n: 2, label: "Professional Echo" },
                    { n: 3, label: "Binary Blueprint" },
                    { n: 4, label: "Security Protocol" }
                ].map(s => (
                    <div key={s.n} className={`flex items-center gap-6 transition-all duration-500 ${step === s.n ? 'translate-x-4 opacity-100' : 'opacity-30'}`}>
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-sm border-2 ${step >= s.n ? 'bg-accent-purple border-accent-purple text-white' : 'bg-transparent border-white/20 text-white'}`}>
                            {step > s.n ? <CheckCircle2 className="w-6 h-6" /> : s.n}
                        </div>
                        <span className="text-[12px] uppercase tracking-[0.4em] font-black text-white">{s.label}</span>
                    </div>
                ))}
             </div>
          </div>
        </div>

        {/* Right Form Interface */}
        <div className="flex-grow flex items-center justify-center p-8 lg:p-24 bg-white">
          <div className="w-full max-w-2xl">
            <AnimatePresence mode="wait">
              {step === 1 && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} key="step1" className="space-y-12">
                  <div className="space-y-4">
                    <h3 className="text-4xl font-extrabold text-slate-900 uppercase tracking-tight">Biometrics & Contact</h3>
                    <p className="text-slate-500 font-bold">Standard operator identification required for system entry.</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                    <div className="space-y-3">
                      <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black ml-1">Salutation</label>
                      <select 
                        className="w-full bg-slate-50 border-2 border-slate-50 p-6 rounded-3xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold text-slate-900 appearance-none" 
                        value={formData.salutation} 
                        onChange={e => setFormData({...formData, salutation: e.target.value})}
                      >
                        <option>Mr</option>
                        <option>Ms</option>
                        <option>Dr</option>
                        <option>Mx</option>
                      </select>
                    </div>
                    <div className="space-y-3">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black ml-1">Legal Name</label>
                        <div className="relative group">
                          <UserIcon className="absolute left-6 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
                          <input 
                            className="w-full bg-slate-50 border-2 border-slate-50 p-6 pl-16 rounded-3xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold text-slate-900 placeholder:text-slate-300" 
                            placeholder="John Doe" 
                            value={formData.fullName} 
                            onChange={e => setFormData({...formData, fullName: e.target.value})}
                          />
                        </div>
                    </div>
                    <div className="space-y-3 md:col-span-2">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black ml-1">Deployment Email</label>
                        <div className="relative group">
                          <Mail className="absolute left-6 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
                          <input 
                            type="email"
                            className="w-full bg-slate-50 border-2 border-slate-50 p-6 pl-16 rounded-3xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold text-slate-900 placeholder:text-slate-300" 
                            placeholder="operator@devapply.io" 
                            value={formData.email} 
                            onChange={e => setFormData({...formData, email: e.target.value})}
                          />
                        </div>
                    </div>
                  </div>

                  <button onClick={() => setStep(2)} className="w-full btn-black py-7 text-sm flex items-center justify-center gap-4 hover:scale-[1.02] shadow-2xl">
                    Next Protocol Step
                    <ArrowRight className="w-5 h-5" />
                  </button>
                </motion.div>
              )}

              {step === 2 && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} key="step2" className="space-y-12">
                  <div className="space-y-4">
                    <h3 className="text-4xl font-extrabold text-slate-900 uppercase tracking-tight">Professional Sync</h3>
                    <p className="text-slate-500 font-bold">Connect your digital footprints to calibrate the matching engine.</p>
                  </div>

                  <div className="space-y-10">
                    <div className="space-y-3">
                      <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black ml-1">LinkedIn URL</label>
                      <div className="relative group">
                        <Linkedin className="absolute left-6 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
                        <input 
                          className="w-full bg-slate-50 border-2 border-slate-50 p-6 pl-16 rounded-3xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold text-slate-900 placeholder:text-slate-300" 
                          placeholder="https://linkedin.com/in/operator" 
                          value={formData.linkedin} 
                          onChange={e => setFormData({...formData, linkedin: e.target.value})}
                        />
                      </div>
                    </div>
                    <div className="space-y-3">
                      <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black ml-1">Carrier Bio</label>
                      <textarea 
                        className="w-full bg-slate-50 border-2 border-slate-50 p-8 rounded-[40px] focus:border-accent-purple focus:bg-white outline-none text-sm h-56 resize-none transition-all font-bold text-slate-900 placeholder:text-slate-300 leading-relaxed" 
                        placeholder="Detail your architectural expertise and career trajectory..." 
                        value={formData.bio} 
                        onChange={e => setFormData({...formData, bio: e.target.value})}
                      />
                    </div>
                  </div>

                  <div className="flex gap-6">
                    <button onClick={() => setStep(1)} className="px-10 py-6 rounded-3xl border-2 border-slate-50 font-black text-[10px] uppercase tracking-widest text-slate-400 hover:bg-slate-50 transition-all">Back</button>
                    <button onClick={() => setStep(3)} className="flex-grow btn-black py-6 text-sm flex items-center justify-center gap-4 transition-all hover:scale-[1.02] shadow-2xl">
                      Proceed to Blueprint
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </motion.div>
              )}

              {step === 3 && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} key="step3" className="space-y-12">
                  <div className="space-y-4 text-center">
                    <h3 className="text-4xl font-extrabold text-slate-900 uppercase tracking-tight">Neural Blueprint</h3>
                    <p className="text-slate-500 font-bold">Upload your PDF resume. Our agents will use this to generate customized applications.</p>
                  </div>

                  <div className={`p-24 border-2 border-dashed rounded-[60px] flex flex-col items-center justify-center text-center space-y-10 transition-all ${formData.resume ? 'bg-accent-purple/5 border-accent-purple/20' : 'bg-slate-50 border-slate-100 hover:border-accent-purple/30'}`}>
                    <div className={`w-28 h-28 rounded-3xl flex items-center justify-center shadow-2xl border ${formData.resume ? 'bg-accent-purple text-white border-accent-purple' : 'bg-white text-slate-300 border-slate-100'}`}>
                        <Binary className="w-12 h-12" />
                    </div>
                    <div>
                        <h4 className="text-xl font-extrabold uppercase tracking-tight text-slate-900">
                            {formData.resume ? formData.resume.name : "Binary Upload"}
                        </h4>
                        <p className="text-slate-400 font-bold mt-2 text-sm">PDF Format Only. Max 10MB.</p>
                    </div>
                    <label className="px-12 py-5 bg-black text-white rounded-2xl text-[10px] uppercase tracking-[0.4em] font-black cursor-pointer hover:bg-accent-purple transition-all shadow-xl">
                        {formData.resume ? "Replace File" : "Select Source"}
                        <input type="file" className="hidden" accept=".pdf" onChange={handleFileUpload} />
                    </label>
                  </div>

                  <div className="flex gap-6">
                    <button onClick={() => setStep(2)} className="px-10 py-6 rounded-3xl border-2 border-slate-50 font-black text-[10px] uppercase tracking-widest text-slate-400">Back</button>
                    <button onClick={() => setStep(4)} disabled={!formData.resume} className="flex-grow btn-black py-6 text-sm flex items-center justify-center gap-4 disabled:opacity-30 shadow-2xl">
                      Final Protocol
                      <ShieldCheck className="w-5 h-5" />
                    </button>
                  </div>
                </motion.div>
              )}

              {step === 4 && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} key="step4" className="space-y-12 text-center flex flex-col items-center">
                  <div className="space-y-4">
                    <h3 className="text-5xl font-extrabold text-slate-900 uppercase tracking-tight leading-none">Security Loop</h3>
                    <p className="text-slate-500 font-bold max-w-md mx-auto">Authorize your agent to communicate with job nodes. Set your encryption key.</p>
                  </div>

                  <div className="w-full space-y-8 mt-10">
                    <div className="space-y-3 text-left">
                        <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black ml-1">Access Passphrase</label>
                        <div className="relative group">
                          <Lock className="absolute left-6 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
                          <input 
                            type="password"
                            className="w-full bg-slate-50 border-2 border-slate-50 p-6 pl-16 rounded-3xl focus:border-accent-purple focus:bg-white outline-none text-sm font-bold text-slate-900 placeholder:text-slate-300" 
                            placeholder="Generate a robust key" 
                            value={formData.password} 
                            onChange={e => setFormData({...formData, password: e.target.value})}
                          />
                        </div>
                    </div>

                    <div className="bg-slate-900 rounded-[50px] p-12 text-left relative overflow-hidden group">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-accent-purple/20 blur-[60px] rounded-full" />
                        <div className="relative z-10 space-y-6">
                           <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-xl bg-accent-purple/20 flex items-center justify-center">
                                 <Rocket className="w-5 h-5 text-accent-purple" />
                              </div>
                              <span className="text-[10px] font-black uppercase tracking-[0.4em] text-accent-purple">Final Authorization</span>
                           </div>
                           <p className="text-neutral-400 text-sm font-bold leading-relaxed">
                             By initializing, you enable the DevApply Agent Hub to act as your persistent representative across global career nodes. Your binary data is encrypted at rest.
                           </p>
                        </div>
                    </div>
                  </div>

                  <div className="flex gap-6 w-full mt-10">
                    <button onClick={() => setStep(3)} className="px-10 py-6 rounded-3xl border-2 border-slate-50 font-black text-[10px] uppercase tracking-widest text-slate-400">Back</button>
                    <button 
                      onClick={handleSubmit} 
                      disabled={loading} 
                      className="flex-grow btn-purple py-8 text-sm flex items-center justify-center gap-6 shadow-[0_20px_40px_rgba(99,102,241,0.3)] hover:scale-[1.03] transition-all disabled:opacity-50"
                    >
                        {loading ? "INITIALIZING SECTOR..." : "DEPLOY MATRIX"}
                        <ArrowRight className="w-6 h-6" />
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
