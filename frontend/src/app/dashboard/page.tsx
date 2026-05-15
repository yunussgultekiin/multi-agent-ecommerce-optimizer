'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { tr } from 'date-fns/locale';
import { Plus, ArrowRight, BarChart3, Activity, TrendingUp, Zap, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import type { AnalysisTask } from '@/types';

const statusMap = {
  pending: { label: 'Bekliyor', variant: 'pending' },
  running: { label: 'Analiz Ediliyor', variant: 'info' },
  completed: { label: 'Tamamlandı', variant: 'success' },
  failed: { label: 'Başarısız', variant: 'destructive' },
  cancelled: { label: 'İptal Edildi', variant: 'outline' },
} as const;

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

function getTaskLink(task: AnalysisTask): string {
  if (task.status === 'completed') return `/dashboard/result/${task.task_id}`;
  if (task.status === 'running' || task.status === 'pending')
    return `/dashboard/analyze/${task.task_id}/progress`;
  return '#';
}

export default function DashboardPage() {
  const { user, quota } = useAuthStore();
  const [recentTasks, setRecentTasks] = useState<AnalysisTask[]>([]);
  const [allTasks, setAllTasks] = useState<AnalysisTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        const res = await api.get('/analyze');
        setAllTasks(res.data);
        setRecentTasks(res.data.slice(0, 5));
      } catch (error) {
        console.error('Failed to fetch history:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchRecent();
  }, []);

  const completedCount = allTasks.filter((t) => t.status === 'completed').length;
  const runningCount = allTasks.filter((t) => t.status === 'running').length;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      <motion.div
        variants={itemVariants}
        className="flex flex-col md:flex-row md:items-end justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Hoş geldin, <span className="gradient-text">{user?.email.split('@')[0]}</span>
          </h1>
          <p className="text-muted-foreground mt-1">Ürün analizlerinize genel bir bakış.</p>
        </div>
        <Link href="/dashboard/analyze">
          <Button className="w-full md:w-auto h-11 gap-2 shadow-lg shadow-indigo-500/10">
            <Plus className="w-4 h-4" />
            Yeni Analiz Başlat
          </Button>
        </Link>
      </motion.div>

      <motion.div
        variants={itemVariants}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <Card className="relative overflow-hidden group hover:bg-white/[0.06] transition-colors">
          <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-2xl pointer-events-none group-hover:bg-primary/10 transition-colors" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Toplam Analiz</CardTitle>
            <BarChart3 className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {isLoading ? <Skeleton className="h-9 w-12" /> : allTasks.length}
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden group hover:bg-white/[0.06] transition-colors">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none group-hover:bg-emerald-500/10 transition-colors" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Tamamlanan</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-500">
              {isLoading ? <Skeleton className="h-9 w-12" /> : completedCount}
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden group hover:bg-white/[0.06] transition-colors">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full blur-2xl pointer-events-none group-hover:bg-blue-500/10 transition-colors" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Devam Eden</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-500">
              {isLoading ? <Skeleton className="h-9 w-12" /> : runningCount}
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden group hover:bg-white/[0.06] transition-colors">
          <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/5 rounded-full blur-2xl pointer-events-none group-hover:bg-violet-500/10 transition-colors" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Kalan Kota</CardTitle>
            <Zap className="h-4 w-4 text-violet-500" />
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold text-violet-500">
                {quota ? quota.remaining : <Skeleton className="h-9 w-12 inline-block" />}
              </span>
              {quota && <span className="text-sm text-muted-foreground">/ {quota.limit}</span>}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div variants={itemVariants} className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold tracking-tight">Son Analizler</h2>
          <Link
            href="/dashboard/history"
            className="text-sm text-primary hover:underline flex items-center gap-1 group"
          >
            Tümünü Gör
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 w-full rounded-xl" />
            ))}
          </div>
        ) : recentTasks.length === 0 ? (
          <Card className="flex flex-col items-center justify-center py-16 text-center bg-white/[0.02] border-dashed border-white/10">
            <div className="relative mb-6">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-primary" />
              </div>
              <div className="absolute -inset-3 rounded-3xl bg-primary/5 blur-xl -z-10" />
            </div>
            <h3 className="text-xl font-semibold">Henüz analiz bulunmuyor</h3>
            <p className="text-sm text-muted-foreground mt-2 mb-6 max-w-sm">
              İlk ürününüzü analiz ederek rakiplerinizin önüne geçin.
            </p>
            <Link href="/dashboard/analyze">
              <Button className="gap-2">
                <Plus className="w-4 h-4" />
                Hemen Başla
              </Button>
            </Link>
          </Card>
        ) : (
          <div className="grid gap-3">
            {recentTasks.map((task, index) => (
              <motion.div
                key={task.task_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.06 }}
              >
                <Link href={getTaskLink(task)}>
                  <Card className="hover:bg-white/[0.06] transition-all duration-200 cursor-pointer group border-white/5 hover:border-white/10">
                    <CardContent className="p-4 flex items-center justify-between">
                      <div className="flex flex-col gap-1.5 min-w-0">
                        <div className="font-medium text-base group-hover:text-primary transition-colors truncate">
                          {task.payload.title}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span className="capitalize px-2 py-0.5 rounded bg-white/5">
                            {task.payload.platform}
                          </span>
                          <span>
                            {format(new Date(task.updated_at), 'd MMM yyyy, HH:mm', { locale: tr })}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 ml-4">
                        <Badge variant={statusMap[task.status].variant as any}>
                          {statusMap[task.status].label}
                        </Badge>
                        <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
