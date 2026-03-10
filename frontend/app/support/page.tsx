"use client";

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { LifeBuoy, Mail, MessageSquare, Phone, Send, Search } from "lucide-react";

export default function SupportPage() {
  const channels = [
    { icon: Mail, title: "Operator Email", detail: "support@devapply.io", desc: "Response time: < 4 hours" },
    { icon: MessageSquare, title: "Live Protocol", detail: "Active Dashbaord Chat", desc: "Real-time sync" },
    { icon: LifeBuoy, title: "Self-Serve Vault", detail: "Knowledge Base", desc: "1,200+ documented nodes" },
  ];

  return (
    <div className="min-h-screen bg-white font-main selection:bg-accent-purple selection:text-white">
      <Header />
      
      <main className="pt-40 pb-40 px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center mb-40">
            <div>
              <span className="text-[11px] uppercase tracking-[0.6em] text-accent-purple font-black mb-10 block">Operator Assistance</span>
              <h1 className="text-[clamp(2.5rem,8vw,6rem)] font-extrabold mb-10 tracking-tighter uppercase leading-[0.9]">Support <br /> Loop.</h1>
              <p className="text-slate-500 text-lg max-w-lg font-semibold leading-relaxed">Need technical calibration for your agent node? Our support team is standing by to assist with your deployment.</p>
            </div>
            <div className="p-16 bg-slate-50 rounded-[60px] relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-80 h-80 bg-accent-purple/5 blur-[100px] rounded-full translate-x-1/2 -translate-y-1/2" />
                <img 
                    src="https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?q=80&w=2072&auto=format&fit=crop" 
                    className="w-full h-96 object-cover rounded-[40px] shadow-2xl relative z-10 hover:scale-105 transition-transform duration-700"
                    alt="Customer Support"
                />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {channels.map((c, i) => (
              <div key={i} className="p-12 rounded-[50px] border border-slate-100 bg-white transition-all hover:shadow-2xl hover:border-accent-purple/20 group">
                <div className="w-16 h-16 rounded-2xl bg-slate-50 border border-slate-50 flex items-center justify-center text-accent-purple mb-10 group-hover:scale-110 transition-transform">
                  <c.icon className="w-8 h-8" />
                </div>
                <h3 className="text-[12px] font-black uppercase tracking-[0.4em] text-slate-400 mb-6">{c.title}</h3>
                <div className="text-2xl font-extrabold text-slate-900 mb-2 uppercase tracking-tight">{c.detail}</div>
                <p className="text-slate-400 font-bold uppercase tracking-widest text-[9px]">{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
