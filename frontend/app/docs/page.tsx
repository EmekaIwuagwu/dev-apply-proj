"use client";

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Terminal, Cpu, FileJson, Shield, Search, Book } from "lucide-react";

export default function DocsPage() {
  const docs = [
    { title: "Agent Initialization", desc: "Setting up your first career node with the optimal weighting for engineering roles." },
    { title: "Protocol Constraints", desc: "Understanding the daily application caps and neural safety mechanisms." },
    { title: "Blueprint Standards", desc: "Guidance on PDF structure and data extraction for high-fidelity applications." },
    { title: "Dashboard CLI", desc: "Monitoring agent logs and real-time execution flows from the command center." },
  ];

  return (
    <div className="min-h-screen bg-white font-main selection:bg-accent-purple selection:text-white">
      <Header />
      
      <main className="pt-40 pb-40 px-8">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-24">
            {/* Sidebar (simplified) */}
            <div className="lg:w-1/4 space-y-12">
                <div className="relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
                    <input className="w-full bg-slate-50 border border-slate-50 p-4 pl-12 rounded-2xl outline-none focus:border-accent-purple transition-all font-bold text-sm" placeholder="Search Docs..." />
                </div>
                
                <div className="space-y-4">
                    <span className="text-[10px] uppercase font-black text-slate-300 tracking-[0.4em] mb-4 block">Quick Start</span>
                    {[
                        "Introduction", "Node Deployment", "Blueprint Setup", "Billing Tiers", "Safety Standards"
                    ].map(link => (
                        <div key={link} className="flex items-center gap-3 transition-all hover:translate-x-2 cursor-pointer group">
                             <div className="w-1.5 h-1.5 rounded-full bg-slate-100 group-hover:bg-accent-purple" />
                             <span className="text-xs font-bold text-slate-500 hover:text-accent-purple transition-colors">{link}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-grow">
                <div className="mb-24 px-4 lg:px-0">
                    <span className="text-[11px] uppercase tracking-[0.6em] text-accent-purple font-black mb-10 block">Operator Documentation</span>
                    <h1 className="text-[clamp(2.5rem,8vw,5.5rem)] font-extrabold mb-10 tracking-tighter uppercase leading-[0.9]">Knowledge Base.</h1>
                    <p className="text-slate-500 text-lg max-w-xl font-semibold leading-relaxed">Detailed protocols for maximizing your career agent's performance loop and ensuring seamless node synchronization.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                    {docs.map((doc, i) => (
                        <div key={i} className="p-12 rounded-[50px] border border-slate-100 bg-white hover:bg-slate-50 hover:border-accent-purple/10 transition-all hover:shadow-xl group flex flex-col group items-start gap-8">
                            <div className="w-16 h-16 rounded-2xl bg-slate-50 border border-slate-50 flex items-center justify-center text-accent-purple group-hover:scale-110 transition-transform">
                                <Book className="w-8 h-8" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-extrabold uppercase tracking-tight text-slate-900 mb-4">{doc.title}</h3>
                                <p className="text-slate-500 font-bold leading-relaxed text-sm">{doc.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="mt-20 p-16 bg-slate-50 rounded-[60px] border border-slate-100 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-80 h-80 bg-accent-purple/5 blur-[100px] rounded-full translate-x-1/2 -translate-y-1/2" />
                    <div className="relative z-10 space-y-8 flex flex-col items-center text-center">
                        <Terminal className="w-20 h-20 text-accent-purple opacity-30 group-hover:scale-110 transition-transform duration-700" />
                        <div className="space-y-4">
                            <h3 className="text-3xl font-extrabold uppercase tracking-tight text-slate-900">Operator Lab</h3>
                            <p className="text-slate-500 font-bold max-w-lg mb-8">Access our advanced CLI tools and developer SDK for custom agent behavior orchestration.</p>
                            <button className="btn-black px-12 py-5 text-sm uppercase tracking-widest font-black transition-all hover:scale-105 active:scale-95 shadow-xl">Contact Engineering Lab</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
