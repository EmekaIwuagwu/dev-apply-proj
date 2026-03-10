"use client";

import { motion } from "framer-motion";
import { Search, Briefcase, Send, ArrowRight, CheckCircle2, Target, Rocket, Activity, ShieldCheck, Globe } from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";
import { Logo } from "@/components/Logo";

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-x-hidden selection:bg-accent-purple selection:text-white bg-white text-slate-900 font-main">
      <Header />

      {/* Hero Section */}
      <section className="relative min-h-[92vh] flex flex-col items-center justify-center px-8 pt-20 bg-mesh overflow-hidden">
        {/* Abstract Background Orbs */}
        <div className="absolute top-[10%] right-[-5%] w-[500px] h-[500px] bg-accent-purple/5 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute bottom-[10%] left-[-5%] w-[500px] h-[500px] bg-accent-gold/5 blur-[120px] rounded-full pointer-events-none" />
        
        <div className="relative z-10 text-center max-w-7xl mx-auto flex flex-col items-center">
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }} 
            animate={{ opacity: 1, scale: 1 }} 
            className="inline-flex items-center gap-3 px-6 py-2 rounded-full border border-slate-100 bg-white/50 backdrop-blur-sm text-[10px] uppercase tracking-[0.4em] font-black text-accent-purple mb-10 shadow-sm"
          >
            <Rocket className="w-4 h-4" />
            Empowering Next-Gen Careers
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, y: 30 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.1, duration: 0.8 }}
            className="text-[clamp(3rem,11vw,10.5rem)] font-extrabold mb-8 leading-[0.88] tracking-[-0.04em] uppercase text-slate-900"
          >
            Your Career. <br />
            <span className="text-accent-purple">Automated.</span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.2, duration: 0.8 }}
            className="text-lg md:text-xl text-slate-500 mb-14 max-w-3xl mx-auto font-semibold leading-[1.6] tracking-tight"
          >
            DevApply is the world's most sophisticated agentic job concierge. 
            We orchestrate the complete application loop—scanning global listings, certifying compatibility, 
            and delivering high-fidelity applications—while you sleep.
          </motion.p>
          
          <motion.div 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.3, duration: 0.8 }}
            className="flex flex-col sm:flex-row gap-6 justify-center items-center"
          >
            <Link href="/register" className="btn-black flex items-center gap-4 group px-14 py-6 text-sm hover:scale-105 active:scale-95 transition-all shadow-xl">
              Deploy Your Agent
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link href="/login" className="px-12 py-5 border-2 border-slate-100 rounded-full text-[11px] uppercase tracking-[0.4em] font-black hover:border-accent-purple hover:text-accent-purple transition-all bg-white shadow-sm active:scale-95">
              Operator Portal
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Corporate Marquee */}
      <section className="py-14 border-y border-slate-100 overflow-hidden w-full relative bg-white">
        <div className="mask-fade w-full relative">
          <div className="marquee flex gap-24 items-center">
            {/* Double set for seamless loop */}
            {[...Array(16)].map((_, i) => (
              <div key={i} className="flex items-center gap-6 font-black text-[11px] tracking-[0.5em] uppercase text-slate-300 whitespace-nowrap shrink-0">
                <div className="w-2 h-2 rounded-full bg-accent-purple shadow-[0_0_10px_rgba(99,102,241,0.5)]" />
                <span>Job Node Applied: {['NY', 'SF', 'LON', 'TOK'][i%4]}_0{i}</span>
                <span className="text-accent-gold">Verification_OK</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section id="strategy" className="py-40 px-8 max-w-[1400px] mx-auto bg-white">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-24 items-start">
          <div className="lg:sticky lg:top-40">
            <span className="text-[11px] uppercase tracking-[0.6em] text-accent-purple font-black mb-8 block">Market Protocol</span>
            <h2 className="text-6xl md:text-8xl font-extrabold mb-10 tracking-tight uppercase leading-[0.85] text-slate-900">Mission <br /> Critical.</h2>
            <p className="text-slate-500 text-lg leading-relaxed max-w-sm font-semibold">
              DevApply leverages persistent neural agents to handle the massive volume of outreach required to scale your engineering career globally.
            </p>
          </div>
          
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-10">
            {[
              { 
                title: "Target Discovery", 
                desc: "Our agents crawl beyond public boards, accessing hidden company APIs, niche hiring lists, and verified recruiter channels.", 
                icon: Search, 
                accent: "gold" 
              },
              { 
                title: "Neural Matching", 
                desc: "Every opportunity is analyzed by our LLM processor, scoring it against your tech stack, goals, and cultural alignment.", 
                icon: Target, 
                accent: "purple" 
              },
              { 
                title: "Human Pulse", 
                desc: "We simulate human interaction patterns to fulfill every application requirement, bypassing automated filters with precision.", 
                icon: Send, 
                accent: "black" 
              },
              { 
                title: "Agent Console", 
                desc: "Monitor your deployment in real-time through a dedicated command center showing exact metrics and application logs.", 
                icon: Activity, 
                accent: "gold" 
              }
            ].map((item, i) => (
              <div key={i} className="p-14 rounded-[48px] border border-slate-100 bg-slate-50/30 transition-all hover:bg-white hover:shadow-2xl hover:border-accent-purple/20 flex flex-col items-start gap-10 group">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-sm border border-slate-100 group-hover:scale-110 group-hover:bg-white transition-all bg-white`}>
                  <item.icon className="w-8 h-8 text-accent-purple" />
                </div>
                <div>
                  <h3 className="text-3xl font-extrabold mb-5 tracking-tight uppercase text-slate-900">{item.title}</h3>
                  <p className="text-slate-500 leading-relaxed text-sm font-semibold">
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-40 px-8 text-center bg-slate-50 lg:rounded-[100px] mb-[-100px] relative z-20 overflow-hidden border-t border-slate-100">
        <div className="max-w-[1200px] mx-auto p-24 md:p-32 rounded-[60px] border border-slate-200 bg-white shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-80 h-80 bg-accent-purple/5 blur-[100px] rounded-full translate-x-1/2 -translate-y-1/2" />
          
          <div className="relative z-10 flex flex-col items-center">
            <div className="badge-purple px-6 py-2 rounded-full border border-accent-purple/10 text-[10px] uppercase tracking-[0.6em] font-black text-accent-purple mb-12">System Readiness_OK</div>
            <h2 className="text-5xl md:text-9xl font-extrabold mb-14 tracking-tighter leading-[0.84] uppercase text-slate-900">Land Your <br /> Future Role.</h2>
            <div className="flex flex-col sm:flex-row gap-6 justify-center w-full max-w-md">
              <Link href="/register" className="btn-purple w-full px-16 py-6 text-sm">
                Get Started
              </Link>
              <Link href="/login" className="px-14 py-6 border-2 border-slate-100 rounded-full text-[11px] uppercase tracking-[0.5em] font-black hover:bg-slate-50 transition-all bg-white shadow-sm active:scale-95">
                Login
              </Link>
            </div>
            <p className="mt-16 text-slate-400 text-[11px] uppercase font-black tracking-[0.5em] opacity-50">
              Processing Starts daily at 06:00 UTC. Global Node: Operational.
            </p>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
