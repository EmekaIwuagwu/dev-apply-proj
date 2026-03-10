"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Search, 
  Filter, 
  Download, 
  ExternalLink, 
  ChevronDown,
  MoreVertical,
  CheckCircle2,
  XCircle,
  Clock,
  MinusCircle,
  FileText,
  Globe,
  Cpu
} from "lucide-react";

import useSWR from 'swr';
import api from '@/lib/api';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const StatusBadge = ({ status }: { status: string }) => {
  const s = status.toLowerCase();
  if (s === 'submitted') return <div className="flex items-center gap-2 text-green-600 bg-green-50 border border-green-100 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest"><CheckCircle2 className="w-3 h-3" /> {status}</div>;
  if (s === 'failed') return <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-100 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest"><XCircle className="w-3 h-3" /> {status}</div>;
  if (s === 'skipped') return <div className="flex items-center gap-2 text-slate-400 bg-slate-50 border border-slate-100 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest"><MinusCircle className="w-3 h-3" /> {status}</div>;
  return <div className="flex items-center gap-2 text-accent-gold bg-accent-gold/5 border border-accent-gold/10 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest"><Clock className="w-3 h-3" /> {status}</div>;
};

export default function ApplicationsPage() {
  const { data: applications, isLoading } = useSWR('/applications', fetcher, { refreshInterval: 10000 });
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="space-y-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 px-2">
        <div>
          <h1 className="text-4xl font-extrabold uppercase tracking-tight text-slate-900 mb-2">Application History</h1>
          <p className="text-slate-400 text-sm font-bold">Comprehensive audit of every action initiated by your AI agent loop.</p>
        </div>
        <div className="flex gap-4">
            <button className="px-8 py-3 bg-white border border-slate-100 rounded-full text-[11px] font-black uppercase tracking-widest text-slate-600 hover:border-slate-300 transition-all flex items-center gap-3 shadow-sm active:scale-95">
                <Download className="w-4 h-4" /> Export CSV
            </button>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-wrap gap-6 items-center bg-white p-6 rounded-[32px] border border-slate-100 shadow-sm">
        <div className="relative flex-grow max-w-md group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 group-focus-within:text-accent-purple transition-colors" />
            <input 
                className="w-full bg-slate-50 border border-slate-50 p-3.5 pl-12 rounded-2xl focus:border-accent-purple focus:bg-white outline-none text-sm transition-all font-bold placeholder:text-slate-300"
                placeholder="Filter by company, role or tech node..."
            />
        </div>
        <div className="flex gap-3">
            <button className="px-6 py-3 bg-slate-50 border border-slate-50 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] flex items-center gap-3 hover:bg-white hover:border-slate-200 transition-all text-slate-500">
                <Filter className="w-3.5 h-3.5" /> Status: All <ChevronDown className="w-3.5 h-3.5 opacity-40" />
            </button>
            <button className="px-6 py-3 bg-slate-50 border border-slate-50 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] flex items-center gap-3 hover:bg-white hover:border-slate-200 transition-all text-slate-500">
                <Clock className="w-3.5 h-3.5" /> This Week <ChevronDown className="w-3.5 h-3.5 opacity-40" />
            </button>
        </div>
      </div>

      {/* Table Interface */}
      <div className="bg-white rounded-[40px] border border-slate-100 shadow-sm overflow-hidden mb-12">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-50 bg-slate-50/20">
              <th className="p-8 text-[11px] uppercase tracking-[0.3em] text-slate-400 font-black">Company_Node</th>
              <th className="p-8 text-[11px] uppercase tracking-[0.3em] text-slate-400 font-black">Platform</th>
              <th className="p-8 text-[11px] uppercase tracking-[0.3em] text-slate-400 font-black">Match_Score</th>
              <th className="p-8 text-[11px] uppercase tracking-[0.3em] text-slate-400 font-black">Agent_Status</th>
              <th className="p-8 text-[11px] uppercase tracking-[0.3em] text-slate-400 font-black">Timestamp</th>
              <th className="p-8"></th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {isLoading ? (
                <tr>
                    <td colSpan={6} className="p-20 text-center">
                        <div className="flex flex-col items-center gap-4">
                            <div className="w-12 h-12 border-4 border-accent-purple border-t-transparent rounded-full animate-spin" />
                            <p className="text-xs font-black uppercase tracking-widest text-slate-400">Syncing Node Applications...</p>
                        </div>
                    </td>
                </tr>
            ) : (applications || []).map((app: any) => (
              <React.Fragment key={app.id}>
                <tr 
                  className={`border-b border-slate-50 hover:bg-slate-50/50 transition-all cursor-pointer group ${expandedId === app.id ? 'bg-slate-50/50' : ''}`}
                  onClick={() => setExpandedId(expandedId === app.id ? null : app.id)}
                >
                  <td className="p-8">
                    <div className="font-extrabold text-slate-900 text-lg tracking-tight mb-1">{app.company_name}</div>
                    <div className="text-xs text-slate-400 font-bold uppercase tracking-widest">{app.job_title}</div>
                  </td>
                  <td className="p-8 whitespace-nowrap">
                    <div className="flex items-center gap-3">
                        <Globe className="w-4 h-4 text-slate-100" />
                        <span className="font-black text-[10px] uppercase tracking-[0.2em] text-slate-500">{app.platform || "Direct"}</span>
                    </div>
                  </td>
                  <td className="p-8">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-[11px] font-black border group-hover:scale-110 transition-transform ${app.ai_match_score > 90 ? 'bg-green-50 border-green-100 text-green-600 shadow-[0_5px_15px_rgba(22,163,74,0.1)]' : 'bg-slate-50 border-slate-100 text-slate-500'}`}>
                            {Math.round(app.ai_match_score || 0)}%
                        </div>
                    </div>
                  </td>
                  <td className="p-8"><StatusBadge status={app.status} /></td>
                  <td className="p-8">
                    <div className="flex flex-col gap-1 items-start">
                        <span className="font-black text-[10px] uppercase tracking-[0.1em] text-slate-900">
                            {app.created_at ? new Date(app.created_at).toLocaleDateString() : 'N/A'}
                        </span>
                        <span className="text-[9px] text-slate-300 font-black tracking-widest">
                            {app.created_at ? new Date(app.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ''}
                        </span>
                    </div>
                  </td>
                  <td className="p-8 text-right">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${expandedId === app.id ? 'bg-accent-purple text-white shadow-lg rotate-180' : 'text-slate-200 group-hover:text-slate-400'}`}>
                        <ChevronDown className="w-5 h-5" />
                    </div>
                  </td>
                </tr>
                <AnimatePresence>
                    {expandedId === app.id && (
                    <motion.tr 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-slate-50/30"
                    >
                        <td colSpan={6} className="p-12 overflow-hidden border-b border-slate-100">
                        <div className="max-w-4xl space-y-10">
                            <div className="space-y-4">
                            <h4 className="text-[11px] uppercase tracking-[0.4em] text-accent-purple font-black flex items-center gap-3 mb-6">
                                <Cpu className="w-4 h-4" /> Agentic Logic & Analysis
                            </h4>
                            <div className="p-8 bg-white rounded-[32px] border border-slate-100 shadow-sm relative group overflow-hidden">
                                <div className="absolute top-0 right-0 w-32 h-32 bg-accent-purple/5 blur-3xl rounded-full" />
                                <p className="text-slate-600 text-base leading-[1.8] font-bold relative z-10">
                                    {app.ai_reasoning || "Reasoning sequence not available for this node."}
                                </p>
                            </div>
                            </div>
                            <div className="flex gap-4">
                                <a href={app.job_url} target="_blank" className="px-8 py-4 bg-black text-white rounded-full text-[11px] font-black uppercase tracking-[0.3em] flex items-center gap-3 hover:bg-neutral-800 transition-all shadow-xl active:scale-95">
                                    <ExternalLink className="w-4 h-4 text-accent-gold" /> Original Listing
                                </a>
                                <button className="px-8 py-4 bg-white border border-slate-100 text-slate-400 rounded-full text-[11px] font-black uppercase tracking-[0.3em] flex items-center gap-3 hover:border-slate-300 hover:text-slate-600 transition-all shadow-sm active:scale-95">
                                    <FileText className="w-4 h-4" /> Final Payload
                                </button>
                            </div>
                        </div>
                        </td>
                    </motion.tr>
                    )}
                </AnimatePresence>
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Corporate Pagination */}
      <div className="flex items-center justify-between px-6 pb-20">
        <p className="text-[10px] text-slate-300 font-black uppercase tracking-[0.5em]">Showing {applications?.length || 0} Nodes</p>
        <div className="flex gap-3 items-center">
            <button className="w-12 h-12 rounded-2xl bg-white border border-slate-100 flex items-center justify-center text-slate-300 hover:text-accent-purple hover:border-accent-purple transition-all shadow-sm">
                <ChevronDown className="w-5 h-5 rotate-90" />
            </button>
            <div className="px-8 py-3.5 bg-black text-white rounded-2xl text-[11px] font-black uppercase tracking-widest shadow-xl">
                 Node Page 01
            </div>
            <button className="w-12 h-12 rounded-2xl bg-white border border-slate-100 flex items-center justify-center text-slate-300 hover:text-accent-purple hover:border-accent-purple transition-all shadow-sm">
                <ChevronDown className="w-5 h-5 -rotate-90" />
            </button>
        </div>
      </div>
    </div>
  );
}


