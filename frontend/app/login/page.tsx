"use client";

import { motion } from "framer-motion";
import { Mail, Lock, ArrowRight, Github, Chrome, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { useAuth } from "@/store/auth";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { toast } from "sonner";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await api.post("/auth/login", { email, password });
      setAuth(resp.data.user, resp.data.access_token);
      toast.success("Identity Matrix Synchronized.");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Authentication Failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white font-main selection:bg-accent-purple selection:text-white flex flex-col">
      <Header />

      <main className="flex-grow flex flex-col lg:flex-row">
        {/* Left: Imagery and Branding */}
        <div className="hidden lg:flex lg:w-1/2 bg-black relative overflow-hidden items-center justify-center p-20">
          <div className="absolute inset-0 opacity-40">
             <img 
               src="https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop" 
               className="w-full h-full object-cover"
               alt="Neural Network"
             />
          </div>
          <div className="absolute inset-0 bg-gradient-to-br from-accent-purple/20 via-transparent to-black/60" />
          
          <div className="relative z-10 max-w-xl">
             <div className="inline-flex items-center gap-3 px-6 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-md text-[10px] uppercase tracking-[0.6em] font-black text-white mb-10">
               Secure Auth Layer
             </div>
             <h2 className="text-7xl font-extrabold text-white leading-[0.9] tracking-tighter uppercase mb-10">
               Access Your <br /> Agent Hub.
             </h2>
             <p className="text-neutral-400 text-xl font-bold leading-relaxed mb-12">
               Synchronize with your deployment console and monitor global application cycles in high-fidelity.
             </p>
             <div className="flex items-center gap-6">
                <div className="p-4 bg-white/5 rounded-2xl border border-white/10">
                    <ShieldCheck className="w-8 h-8 text-accent-gold" />
                </div>
                <div>
                    <p className="text-white font-black text-sm uppercase tracking-widest">Operator Verified</p>
                    <p className="text-neutral-500 text-xs font-bold uppercase tracking-widest mt-1">256-bit Encryption Active</p>
                </div>
             </div>
          </div>
        </div>

        {/* Right: Auth Interface */}
        <div className="flex-grow flex items-center justify-center p-8 pt-40 pb-40 lg:w-1/2 bg-white">
          <div className="w-full max-w-md space-y-12">
            <div className="text-center lg:text-left space-y-4">
               <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 uppercase">System Login</h1>
               <p className="text-slate-500 font-bold">Authorized operators only. Enter your credentials to decrypt the hub.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-8">
              <div className="space-y-6">
                <div className="space-y-3">
                  <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black ml-1">Email Endpoint</label>
                  <div className="relative group">
                    <Mail className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
                    <input 
                      type="email" 
                      className="w-full bg-slate-50 border-2 border-slate-50 p-5 pl-14 rounded-2xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold text-slate-900 placeholder:text-slate-300"
                      placeholder="e.g. operator@devapply.io"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center px-1">
                    <label className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black">Access Key</label>
                    <Link href="#" className="text-[10px] font-black text-accent-purple uppercase tracking-widest hover:underline">Reset Key?</Link>
                  </div>
                  <div className="relative group">
                    <Lock className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
                    <input 
                      type="password" 
                      className="w-full bg-slate-50 border-2 border-slate-50 p-5 pl-14 rounded-2xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold text-slate-900 placeholder:text-slate-300"
                      placeholder="Enter your secure secret key"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>

              <button 
                type="submit" 
                disabled={loading}
                className="w-full btn-purple py-6 text-sm flex items-center justify-center gap-4 transition-all hover:scale-[1.02] shadow-xl disabled:opacity-50"
              >
                {loading ? "Authenticating..." : "Synchronize System"}
                <ArrowRight className="w-5 h-5 font-black" />
              </button>
            </form>

            <div className="space-y-8">
               <div className="relative flex items-center justify-center">
                  <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-100"></div></div>
                  <span className="relative px-6 bg-white text-[10px] uppercase tracking-[0.5em] text-slate-300 font-bold">Or Connect Via</span>
               </div>

               <div className="grid grid-cols-2 gap-4">
                  <button 
                    onClick={() => toast.info("Google Matrix Integration Pending Verification...")}
                    className="flex items-center justify-center gap-4 p-5 border-2 border-slate-50 bg-slate-50 rounded-2xl hover:bg-white hover:border-slate-200 transition-all group active:scale-95"
                   >
                     <Chrome className="w-5 h-5 text-slate-400 group-hover:text-red-500 transition-colors" />
                     <span className="text-[11px] font-black uppercase tracking-widest text-slate-600">Google</span>
                  </button>
                  <button 
                    onClick={() => toast.info("Microsoft Azure Logic Loop Initialization Pending...")}
                    className="flex items-center justify-center gap-4 p-5 border-2 border-slate-50 bg-slate-50 rounded-2xl hover:bg-white hover:border-slate-200 transition-all group active:scale-95"
                   >
                     <div className="w-5 h-5 text-slate-400 group-hover:text-blue-500 transition-colors flex items-center justify-center">
                        <svg viewBox="0 0 24 24" className="w-full h-full fill-current"><path d="M11.5 1h10.5v10.5h-10.5zM1 1h10.5v10.5h-10.5zM1 11.5h10.5v10.5h-10.5zM11.5 11.5h10.5v10.5h-10.5z"/></svg>
                     </div>
                     <span className="text-[11px] font-black uppercase tracking-widest text-slate-600">Microsoft</span>
                  </button>
               </div>
            </div>

            <p className="text-center text-sm font-bold text-slate-500 pt-8">
              No operator license yet? <Link href="/register" className="text-accent-purple hover:underline">Deploy a new agent</Link>
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
