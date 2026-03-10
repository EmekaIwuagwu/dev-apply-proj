"use client";

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Cpu, Zap, Shield, Database, Globe, Layers } from "lucide-react";

export default function TechPage() {
  const features = [
    { icon: Cpu, title: "Neural Processing", desc: "LLM-driven job compatibility analysis with high-fidelity matching." },
    { icon: Zap, title: "Persistence Loop", desc: "Continuous 24/7 scanning of global job nodes and API endpoints." },
    { icon: Shield, title: "Auth Protocol", desc: "Bank-grade encryption for your professional identity matrix." },
    { icon: Database, title: "Vector Storage", desc: "Your professional experience stored in optimized vector embeddings." },
    { icon: Globe, title: "Global Mesh", desc: "Access to hidden job markets and direct recruiter APIs worldwide." },
    { icon: Layers, title: "Agentic Orchestration", desc: "Autonomous decision making for application selection and submission." },
  ];

  return (
    <div className="min-h-screen bg-white font-main selection:bg-accent-purple selection:text-white">
      <Header />
      
      <main className="pt-40 pb-40 px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-32">
            <span className="text-[11px] uppercase tracking-[0.6em] text-accent-purple font-black mb-8 block">Architecture & Infrastructure</span>
            <h1 className="text-[clamp(2.5rem,8vw,6rem)] font-extrabold mb-8 tracking-tighter uppercase leading-[0.9]">High Fidelity <br /> Career Stack.</h1>
            <p className="text-slate-500 text-lg max-w-2xl mx-auto font-semibold">DevApply is built on a distributed mesh of autonomous agents designed to outpace the traditional job market.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-16">
            {features.map((f, i) => (
              <div key={i} className="group p-12 rounded-[50px] border border-slate-50 bg-slate-50/20 hover:bg-white hover:border-accent-purple/20 transition-all hover:shadow-2xl">
                <div className="w-16 h-16 rounded-2xl bg-white border border-slate-100 flex items-center justify-center text-accent-purple mb-10 group-hover:scale-110 transition-transform shadow-sm">
                  <f.icon className="w-8 h-8" />
                </div>
                <h3 className="text-2xl font-extrabold text-slate-900 uppercase tracking-tight mb-4">{f.title}</h3>
                <p className="text-slate-500 font-semibold leading-relaxed text-sm">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-40 p-20 bg-black rounded-[60px] text-white overflow-hidden relative group">
            <div className="absolute top-0 right-0 w-96 h-96 bg-accent-purple/10 blur-[100px] rounded-full translate-x-1/2 -translate-y-1/2 group-hover:bg-accent-purple/20 transition-all" />
            <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
                <div>
                    <h2 className="text-5xl font-extrabold tracking-tighter uppercase mb-8">Performance <br /> Node Alpha.</h2>
                    <p className="text-neutral-400 font-bold text-lg mb-10">
                        Our core engine processes over 1,000,000 data points per hour to identify the most compatible career nodes for your profile.
                    </p>
                    <div className="flex gap-4">
                        <div className="px-6 py-3 rounded-full border border-white/10 bg-white/5 text-[10px] uppercase tracking-widest font-black">Build 2026.03.09_OK</div>
                        <div className="px-6 py-3 rounded-full border border-white/10 bg-white/5 text-[10px] uppercase tracking-widest font-black text-accent-gold">Uptime 99.99%</div>
                    </div>
                </div>
                <div className="p-10 bg-white/5 border border-white/10 rounded-[40px] backdrop-blur-xl">
                    <img 
                      src="https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=2070&auto=format&fit=crop" 
                      className="w-full h-80 object-cover rounded-[30px] opacity-80"
                      alt="Tech Microchip"
                    />
                </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
