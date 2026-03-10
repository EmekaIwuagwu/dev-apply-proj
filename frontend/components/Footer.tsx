"use client";

import Link from "next/link";
import { Logo } from "./Logo";
import { Globe } from "lucide-react";

export const Footer = () => {
  return (
    <footer className="bg-black text-white pt-60 pb-20 border-t border-white/5 px-8 relative z-10">
      <div className="max-w-[1400px] mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-24 mb-40">
          <div className="lg:col-span-2 space-y-14">
            <Logo theme="dark" />
            <p className="text-neutral-500 text-2xl max-w-lg leading-relaxed font-bold tracking-tight">
              Engineering the future of career acceleration with persistent, high-fidelity agentic protocols.
            </p>
          </div>
          
          <div className="space-y-10">
            <h5 className="text-[12px] font-black uppercase tracking-[0.6em] text-neutral-800">Platform</h5>
            <div className="space-y-6">
              {[
                { name: 'Protocols', href: '/#strategy' },
                { name: 'Scaling', href: '/#strategy' },
                { name: 'Pricing', href: '/pricing' },
                { name: 'Infrastructure', href: '/technology' }
              ].map(link => (
                <Link key={link.name} href={link.href} className="block text-sm font-bold text-neutral-500 hover:text-accent-gold transition-all">{link.name}</Link>
              ))}
            </div>
          </div>
          
          <div className="space-y-10">
            <h5 className="text-[12px] font-black uppercase tracking-[0.6em] text-neutral-800">Connection</h5>
            <div className="space-y-6">
              {[
                { name: 'Login', href: '/login' },
                { name: 'Register', href: '/register' },
                { name: 'Support', href: '/support' },
                { name: 'Operator Lab', href: '/docs' }
              ].map(link => (
                <Link key={link.name} href={link.href} className="block text-sm font-bold text-neutral-500 hover:text-accent-gold transition-all">{link.name}</Link>
              ))}
            </div>
          </div>
        </div>
        
        <div className="pt-24 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-16 font-display text-[10px] tracking-[0.5em] text-neutral-800 font-bold uppercase">
          <div className="flex items-center gap-12">
              <span>&copy; 2026 DevApply Corporation</span>
              <span className="flex items-center gap-3"><Globe className="w-3 h-3 text-accent-purple" /> System_Live</span>
          </div>
          <div className="flex items-center gap-16 text-neutral-600">
              <Link href="/privacy" className="hover:text-white transition-colors">Security Protocol</Link>
              <Link href="/terms" className="hover:text-white transition-colors">Term_Terms</Link>
              <div className="px-5 py-2 border border-white/5 rounded-full font-black text-[9px]">Build v2.0.4.R1</div>
          </div>
        </div>
      </div>
    </footer>
  );
};
