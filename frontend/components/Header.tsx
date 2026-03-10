"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Logo } from "./Logo";
import { LogIn, UserPlus } from "lucide-react";

export const Header = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 30);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 w-full z-50 transition-all duration-500 ${
        scrolled 
          ? 'bg-white/70 backdrop-blur-2xl py-5 border-b border-slate-100 shadow-xl shadow-black/5' 
          : 'bg-transparent py-10'
    }`}>
      <div className="max-w-[1400px] mx-auto px-8 flex items-center justify-between">
        <Logo theme="light" />
        
        {/* Simple Navigation */}
        <div className="hidden lg:flex items-center gap-12 bg-white/50 backdrop-blur-md px-10 py-3 rounded-full border border-slate-100/50 shadow-sm transition-all hover:shadow-md">
          {['Strategy', 'Technology', 'Pricing'].map((item) => (
            <Link key={item} href={item === 'Strategy' ? '/#strategy' : `/${item.toLowerCase()}`} className="text-[10px] uppercase tracking-[0.4em] font-black text-slate-400 hover:text-accent-purple transition-all">
              {item}
            </Link>
          ))}
        </div>

        {/* Clear Logic for Access */}
        <div className="flex items-center gap-4">
          <Link 
            href="/login" 
            className="group flex items-center gap-3 px-8 py-3.5 rounded-full border border-neutral-100 text-[10px] uppercase tracking-[0.4em] font-black text-neutral-500 hover:border-accent-purple hover:text-accent-purple hover:bg-white transition-all active:scale-95"
          >
            <LogIn className="w-4 h-4 text-neutral-300 group-hover:text-accent-purple transition-colors" />
            Login
          </Link>
          <Link 
            href="/register" 
            className="group flex items-center gap-3 btn-purple px-10 py-3.5 text-[10px] hover:scale-105"
          >
            <UserPlus className="w-4 h-4 text-white/50 group-hover:text-white transition-colors" />
            Register
          </Link>
        </div>
      </div>
    </nav>
  );
};
