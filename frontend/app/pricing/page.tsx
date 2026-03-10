"use client";

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Check } from "lucide-react";
import Link from "next/link";

export default function PricingPage() {
  const plans = [
    {
      name: "TRIAL NODE",
      price: "0",
      features: ["2 Applications / Day", "Basic LLM Analysis", "LinkedIn Integration", "Email Support"],
      button: "Start Free",
      color: "border-slate-100",
      accent: "text-slate-400"
    },
    {
      name: "ENTERPRISE PRO",
      price: "19",
      features: ["25 Applications / Day", "Neural Compatibility Scoring", "Multi-Platform Scraping", "Priority Execution Loop", "24/7 Operator Support"],
      button: "Deploy Pro",
      featured: true,
      color: "border-accent-purple shadow-2xl",
      accent: "text-accent-purple"
    },
    {
      name: "MAX PROTOCOL",
      price: "49",
      features: ["Unlimited Applications", "Custom Agent Fine-tuning", "Dedicated Proxy Pool", "API Direct Access", "Personal Success Manager"],
      button: "Contact Sales",
      color: "border-slate-100",
      accent: "text-accent-gold"
    }
  ];

  return (
    <div className="min-h-screen bg-white font-main selection:bg-accent-purple selection:text-white">
      <Header />
      
      <main className="pt-40 pb-40 px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-24">
            <span className="text-[11px] uppercase tracking-[0.6em] text-accent-purple font-black mb-8 block">Subscription Management</span>
            <h1 className="text-[clamp(2.5rem,8vw,6rem)] font-extrabold mb-8 tracking-tighter uppercase leading-[0.9]">Select Your <br /> Deployment Tier.</h1>
            <p className="text-slate-500 text-lg max-w-2xl mx-auto font-semibold">Scale your career search with high-precision agentic protocols designed for every stage of your journey.</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            {plans.map((plan, i) => (
              <div key={i} className={`p-14 rounded-[50px] border relative overflow-hidden bg-white flex flex-col ${plan.color}`}>
                {plan.featured && <div className="absolute top-0 right-0 bg-accent-purple text-white px-8 py-2 text-[10px] uppercase font-black tracking-widest rounded-bl-3xl">Most Deployed</div>}
                
                <div className="mb-12">
                  <h3 className={`text-[12px] font-black uppercase tracking-[0.4em] mb-8 ${plan.accent}`}>{plan.name}</h3>
                  <div className="flex items-baseline gap-2">
                    <span className="text-6xl font-extrabold tracking-tighter text-slate-900">${plan.price}</span>
                    <span className="text-slate-400 font-bold text-sm uppercase">/ Month</span>
                  </div>
                </div>

                <div className="space-y-6 flex-grow mb-12">
                  {plan.features.map(feat => (
                    <div key={feat} className="flex gap-4 items-center">
                      <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${plan.featured ? 'bg-accent-purple/10 text-accent-purple' : 'bg-slate-50 text-slate-300'}`}>
                        <Check className="w-3 h-3" />
                      </div>
                      <span className="text-sm font-semibold text-slate-600">{feat}</span>
                    </div>
                  ))}
                </div>

                <Link href="/register" className={`w-full py-5 rounded-full text-center text-[11px] uppercase tracking-[0.3em] font-black transition-all ${plan.featured ? 'bg-accent-purple text-white shadow-xl hover:bg-indigo-700' : 'bg-slate-50 text-slate-900 hover:bg-slate-100'}`}>
                  {plan.button}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
