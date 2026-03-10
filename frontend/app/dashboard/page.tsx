"use client";

import { motion } from "framer-motion";
import { 
  BarChart3, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Terminal,
  ArrowUpRight,
  TrendingUp,
  Target
} from "lucide-react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from "recharts";
import { useState, useEffect } from "react";
import useSWR from 'swr';
import api from '@/lib/api';
import { useAuth } from '@/store/auth';
import Link from "next/link";
import { toast } from "sonner";

const fetcher = (url: string) => api.get(url).then(res => res.data);

const data = [
  { name: "Mon", apps: 12 },
  { name: "Tue", apps: 18 },
  { name: "Wed", apps: 15 },
  { name: "Thu", apps: 25 },
  { name: "Fri", apps: 22 },
  { name: "Sat", apps: 8 },
  { name: "Sun", apps: 5 },
];

export default function DashboardOverview() {
  const { data: apps, mutate: mutateApps } = useSWR('/applications', fetcher);
  const { data: runs, mutate: mutateRuns } = useSWR('/applications/runs', fetcher);
  const { data: activeRun } = useSWR('/applications/runs/active', fetcher, { refreshInterval: 5000 });
  const { user } = useAuth();
  const [isRunning, setIsRunning] = useState(false);

  const handleRunAgent = async () => {
    setIsRunning(true);
    try {
      await api.post('/applications/run');
      toast.success("Agent sequence initiated");
      mutateRuns();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to start agent");
    } finally {
      setIsRunning(false);
    }
  };

  const totalApplied = apps?.length || 0;
  const todayApplied = apps?.filter((a: any) => a.applied_at?.startsWith(new Date().toISOString().split('T')[0]))?.length || 0;
  
  const stats = [
    { label: "Total Applied", val: totalApplied.toString(), icon: BarChart3, color: "text-accent-purple" },
    { label: "Submitted Today", val: todayApplied.toString(), icon: CheckCircle2, color: "text-green-500" },
    { label: "Success Rate", val: "100%", icon: TrendingUp, color: "text-blue-500" },
    { label: "Next Run", val: "06:00 UTC", icon: Clock, color: "text-accent-gold" },
  ];

  return (
    <div className="space-y-12">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        {stats.map((stat, i) => (
          <motion.div 
            key={i} 
            className="bg-white p-8 rounded-[32px] border border-slate-100 shadow-sm hover:shadow-xl hover:border-accent-purple/20 transition-all group"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <div className="flex justify-between items-start mb-6">
              <div className={`p-3 rounded-2xl bg-slate-50 border border-slate-100 ${stat.color} group-hover:scale-110 transition-transform`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <ArrowUpRight className="w-5 h-5 text-slate-200 group-hover:text-accent-purple transition-colors" />
            </div>
            <div className="space-y-1">
              <p className="text-[10px] uppercase tracking-[0.4em] text-slate-400 font-black">{stat.label}</p>
              <h3 className="text-3xl font-extrabold text-slate-900">{stat.val}</h3>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        {/* Activity Feed */}
        <div className="lg:col-span-1 space-y-8">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-[11px] font-black uppercase tracking-[0.5em] text-slate-900 flex items-center gap-3">
              <Terminal className="w-4 h-4 text-accent-purple" /> Agent Activity
            </h3>
            <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${activeRun ? 'bg-green-500 animate-pulse' : 'bg-slate-300'}`} />
                <span className={`text-[10px] font-black tracking-widest ${activeRun ? 'text-green-500' : 'text-slate-400'}`}>
                    {activeRun ? 'ACTIVE' : 'IDLE'}
                </span>
            </div>
          </div>
          
          <div className="space-y-4">
            {(runs || []).map((run: any, i: number) => (
              <div key={i} className="bg-white p-6 rounded-[24px] border border-slate-100 flex gap-4 text-xs transition-all hover:border-accent-purple/10">
                <div className="text-accent-purple font-black tracking-tighter">[{new Date(run.started_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', hour12: false})}]</div>
                <div className="space-y-1">
                  <p className="font-extrabold text-slate-800 uppercase tracking-tight">Batch {run.id.slice(0, 5)} {run.status}</p>
                  <p className="text-slate-400 font-bold">Processed {run.total_processed} applications globally</p>
                </div>
              </div>
            ))}
            {(!runs || runs.length === 0) && (
                <div className="bg-slate-50/50 p-10 rounded-[32px] border border-dashed border-slate-200 text-center">
                    <p className="text-xs text-slate-300 font-bold uppercase tracking-widest">No recent activity pulse detected</p>
                    <p className="text-[10px] text-slate-200 font-black mt-2 tracking-[0.3em]">NEXT SCHEDULE: 06:00 AM UTC</p>
                </div>
            )}
          </div>
        </div>

        {/* Chart Area */}
        <div className="lg:col-span-2 space-y-8">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-[11px] font-black uppercase tracking-[0.5em] text-slate-900 flex items-center gap-3">
              <BarChart3 className="w-4 h-4 text-accent-gold" /> Submission Trends
            </h3>
          </div>

          <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: '900' }} 
                  dy={15}
                />
                <YAxis hide />
                <Tooltip 
                  cursor={{ fill: '#f8fafc' }}
                  contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #f1f5f9', borderRadius: '16px', boxShadow: '0 10px 40px rgba(0,0,0,0.05)', fontSize: '12px', fontWeight: 'bold' }}
                />
                <Bar dataKey="apps" radius={[8, 8, 8, 8]} barSize={32}>
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#6366f1' : '#D4AF37'} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          
          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <button 
                onClick={handleRunAgent}
                disabled={isRunning || !!activeRun}
                className="bg-black p-6 rounded-[32px] flex items-center justify-between group hover:bg-neutral-800 disabled:bg-slate-100 disabled:cursor-not-allowed transition-all shadow-xl"
            >
              <div className="flex items-center gap-4 text-left">
                <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center text-white border border-white/20">
                    <Terminal className={`w-5 h-5 ${isRunning || activeRun ? 'animate-spin' : ''}`} />
                </div>
                <div>
                    <p className="text-xs font-black uppercase tracking-widest text-white">
                        {activeRun ? 'Agent Processing...' : (isRunning ? 'Initializing...' : 'Run Agent Now')}
                    </p>
                    <p className="text-[10px] text-white/40 font-bold">Manual override for daily loop</p>
                </div>
              </div>
              <ArrowUpRight className="w-5 h-5 text-white/20 group-hover:text-white transition-all" />
            </button>

            <Link href="/dashboard/preferences" className="bg-white p-6 rounded-[32px] border border-slate-100 flex items-center justify-between group hover:border-accent-purple/20 transition-all shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-accent-purple/5 flex items-center justify-center text-accent-purple border border-accent-purple/10">
                    <Target className="w-5 h-5" />
                </div>
                <div>
                    <p className="text-xs font-black uppercase tracking-widest text-slate-900">Adjust Strategy</p>
                    <p className="text-[10px] text-slate-400 font-bold">Optimize target role metrics</p>
                </div>
              </div>
              <ArrowUpRight className="w-5 h-5 text-slate-200 group-hover:text-accent-purple group-hover:translate-x-1 group-hover:-translate-y-1 transition-all" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
