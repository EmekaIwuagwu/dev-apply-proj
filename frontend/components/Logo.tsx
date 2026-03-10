import Link from "next/link";
import { Briefcase, Cpu, ShieldCheck } from "lucide-react";

export const Logo = ({ className = "", theme = "light" }: { className?: string; theme?: "dark" | "light" }) => (
  <Link href="/" className={`flex items-center gap-4 group ${className}`}>
    <div className="relative w-14 h-14 flex items-center justify-center">
      {/* Background Frame - Now with complex industrial layers */}
      <div className={`absolute inset-0 rounded-2xl transition-all duration-700 ease-out border-2 overflow-hidden ${
        theme === "dark" 
          ? "bg-accent-purple/5 border-accent-purple/30 group-hover:bg-accent-purple/10" 
          : "bg-black border-black group-hover:bg-neutral-800"
      }`}>
        {/* Tech grid overlay */}
        <div className="absolute inset-0 opacity-10 group-hover:opacity-20 transition-opacity" 
             style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)', backgroundSize: '6px 6px' }} />
      </div>
      
      {/* Core Logic Icon Area */}
      <div className="relative z-10 flex items-center justify-center">
        <Cpu className={`w-7 h-7 transition-all duration-500 ${
          theme === "dark" ? "text-accent-gold group-hover:rotate-90" : "text-white group-hover:rotate-90"
        }`} />
        
        {/* Verification pulse */}
        <div className="absolute top-[-2px] right-[-2px]">
           <span className="relative flex h-3 w-3">
             <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-purple opacity-75"></span>
             <span className="relative inline-flex rounded-full h-3 w-3 bg-accent-purple border-2 border-white"></span>
           </span>
        </div>
      </div>
    </div>
    
    <div className="flex flex-col">
      <div className="flex items-center gap-1">
        <span className={`text-2xl font-black tracking-tighter leading-none uppercase ${
            theme === "dark" ? "text-white" : "text-black"
        }`}>
            Dev<span className="text-accent-purple">Apply</span>
        </span>
        <ShieldCheck className={`w-3 h-3 ${theme === "dark" ? "text-accent-gold" : "text-accent-purple"}`} />
      </div>
      <div className="flex items-center gap-2 pt-1.5 opacity-80 group-hover:opacity-100 transition-opacity">
        <div className={`h-[1px] w-4 ${theme === "dark" ? "bg-accent-gold" : "bg-neutral-200"}`} />
        <span className={`text-[9px] font-black uppercase tracking-[0.5em] ${
            theme === "dark" ? "text-accent-gold/80" : "text-slate-400"
        }`}>
            Autonomous Agent Console
        </span>
      </div>
    </div>
  </Link>
);
