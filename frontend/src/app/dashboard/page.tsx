'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { formatDate } from '@/lib/utils';
import {
  Plus,
  ArrowRight,
  BarChart3,
  TrendingUp,
  Zap,
  Sparkles,
  History,
  Clock,
  ImageOff,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import api from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import type { AnalysisTask } from '@/types';

const page = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.07 } },
};

const row = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.38 } },
};

const statusMap = {
  pending:   { label: 'Bekliyor',       variant: 'pending'     },
  running:   { label: 'Analiz Ediliyor', variant: 'info'       },
  completed: { label: 'Tamamlandı',     variant: 'success'     },
  failed:    { label: 'Başarısız',      variant: 'destructive' },
  cancelled: { label: 'İptal Edildi',   variant: 'outline'     },
} as const;


function getTaskLink(task: AnalysisTask): string {
  if (task.status === 'completed') return `/dashboard/result/${task.id}`;
  if (task.status === 'running' || task.status === 'pending')
    return `/dashboard/analyze/${task.id}/progress`;
  return '#';
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  glow,
  loading,
}: {
  label: string;
  value: React.ReactNode;
  icon: React.ElementType;
  color: string;
  glow: string;
  loading: boolean;
}) {
  return (
    <motion.div
      variants={row}
      whileHover={{ y: -3, transition: { duration: 0.18 } }}
      className="group relative overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.03] p-5 cursor-default"
    >
      <div className={`absolute top-0 right-0 w-24 h-24 ${glow} rounded-full blur-2xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${glow} border border-white/[0.07]`}>
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
      </div>
      <div className={`text-3xl font-bold tracking-tight ${color}`}>
        {loading ? <Skeleton className="h-9 w-10 rounded-lg" /> : value}
      </div>
    </motion.div>
  );
}

export default function DashboardPage() {
  const { user, quota } = useAuthStore();
  const { toast } = useToast();
  const [recentTasks, setRecentTasks] = useState<AnalysisTask[]>([]);
  const [allTasks, setAllTasks] = useState<AnalysisTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        const res = await api.get('/analyze');
        const tasks: AnalysisTask[] = res.data?.items ?? [];
        setAllTasks(tasks);
        setRecentTasks(tasks.slice(0, 5));
      } catch {
        toast({ variant: 'destructive', title: 'Hata', description: 'Analizler yüklenemedi.' });
      } finally {
        setIsLoading(false);
      }
    };
    fetchRecent();
  }, [toast]);

  const completedCount = allTasks.filter((t) => t.status === 'completed').length;
  const runningCount   = allTasks.filter((t) => t.status === 'running').length;
  const quotaPct       = quota ? (quota.used / quota.limit) * 100 : 0;

  return (
    <motion.div variants={page} initial="hidden" animate="visible" className="space-y-7">

      <motion.div variants={row} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium mb-1">Dashboard</p>
          <h1 className="text-2xl font-bold tracking-tight">
            Hoş geldin,{' '}
            <span className="gradient-text">{user?.email.split('@')[0]}</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Ürün analizlerinizin genel görünümü
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Link href="/dashboard/history">
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Button variant="outline" size="sm" className="h-9 gap-1.5 border-white/[0.09] bg-white/[0.03]">
                <History className="w-3.5 h-3.5" />
                Geçmiş
              </Button>
            </motion.div>
          </Link>
          <Link href="/dashboard/analyze">
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Button size="sm" className="h-9 gap-1.5 shadow-md shadow-indigo-500/15">
                <Plus className="w-3.5 h-3.5" />
                Yeni Analiz
              </Button>
            </motion.div>
          </Link>
        </div>
      </motion.div>

      <motion.div variants={row} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

        <motion.div
          whileHover={{ y: -3, transition: { duration: 0.18 } }}
          className="lg:col-span-2 relative overflow-hidden rounded-2xl border border-primary/20 bg-primary/[0.04] p-5 cursor-default group"
        >
          <div className="absolute top-0 right-0 w-40 h-40 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -top-px left-8 right-8 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

          <div className="flex items-start justify-between mb-4 relative">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">Günlük Limit</p>
              <div className="flex items-baseline gap-1.5">
                {quota ? (
                  <>
                    <span className="text-3xl font-bold gradient-text">{quota.used}</span>
                    <span className="text-lg text-muted-foreground font-medium">/ {quota.limit}</span>
                  </>
                ) : (
                  <Skeleton className="h-9 w-20 rounded-lg" />
                )}
              </div>
            </div>
            <div className="w-9 h-9 rounded-xl gradient-bg flex items-center justify-center shadow-lg shadow-indigo-500/20 shrink-0">
              <Zap className="w-[18px] h-[18px] text-white" />
            </div>
          </div>

          <div className="relative space-y-2">
            {quota ? (
              <>
                <Progress value={quotaPct} className="h-2 rounded-full" />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    24 saat içinde yenilenir
                  </span>
                  <span className="text-xs font-medium text-primary">{quota.remaining} kalan</span>
                </div>
              </>
            ) : (
              <Skeleton className="h-2 w-full rounded-full" />
            )}
          </div>
        </motion.div>

        <StatCard
          label="Toplam Analiz"
          value={allTasks.length}
          icon={BarChart3}
          color="text-foreground"
          glow="bg-white/5"
          loading={isLoading}
        />
        <StatCard
          label="Tamamlanan"
          value={completedCount}
          icon={TrendingUp}
          color="text-emerald-400"
          glow="bg-emerald-500/10"
          loading={isLoading}
        />
      </motion.div>

      <motion.div variants={row} className="grid grid-cols-1 sm:grid-cols-2 gap-4">

        <Link href="/dashboard/analyze" className="block group">
          <motion.div
            whileHover={{ y: -3, scale: 1.005, transition: { duration: 0.18 } }}
            whileTap={{ scale: 0.99 }}
            className="relative overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.03] p-5 h-full transition-colors duration-200 group-hover:bg-white/[0.06] group-hover:border-white/[0.12]"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/8 rounded-full blur-2xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center shadow-md shadow-indigo-500/15 shrink-0">
                <Plus className="w-5 h-5 text-white" />
              </div>
              <div className="min-w-0">
                <h3 className="font-semibold text-base group-hover:text-primary transition-colors">
                  Yeni Analiz Başlat
                </h3>
                <p className="text-sm text-muted-foreground mt-0.5 leading-relaxed">
                  Ürününüzü rakip, SEO ve fiyat açısından analiz edin.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1 text-xs text-primary font-medium mt-4 opacity-0 group-hover:opacity-100 transition-all duration-200 translate-y-1 group-hover:translate-y-0">
              Başla <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </motion.div>
        </Link>

        <Link href="/dashboard/history" className="block group">
          <motion.div
            whileHover={{ y: -3, scale: 1.005, transition: { duration: 0.18 } }}
            whileTap={{ scale: 0.99 }}
            className="relative overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.03] p-5 h-full transition-colors duration-200 group-hover:bg-white/[0.06] group-hover:border-white/[0.12]"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-violet-500/8 rounded-full blur-2xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-violet-500/15 border border-violet-500/20 flex items-center justify-center shrink-0">
                <History className="w-5 h-5 text-violet-400" />
              </div>
              <div className="min-w-0">
                <h3 className="font-semibold text-base group-hover:text-violet-400 transition-colors">
                  Geçmiş Analizler
                </h3>
                <p className="text-sm text-muted-foreground mt-0.5 leading-relaxed">
                  {isLoading ? 'Yükleniyor…' : `${allTasks.length} analizinizin tamamını görüntüleyin.`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1 text-xs text-violet-400 font-medium mt-4 opacity-0 group-hover:opacity-100 transition-all duration-200 translate-y-1 group-hover:translate-y-0">
              Tümünü Gör <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </motion.div>
        </Link>
      </motion.div>

      <motion.div variants={row} className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-semibold tracking-tight">Son Analizler</h2>
            {!isLoading && allTasks.length > 0 && (
              <Badge variant="outline" className="text-[10px] border-white/[0.09] bg-white/[0.03] text-muted-foreground">
                {recentTasks.length} / {allTasks.length}
              </Badge>
            )}
            {runningCount > 0 && (
              <Badge variant="info" className="text-[10px] gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                {runningCount} aktif
              </Badge>
            )}
          </div>
          {allTasks.length > 0 && (
            <Link
              href="/dashboard/history"
              className="text-xs text-primary hover:underline flex items-center gap-1 group"
            >
              Tüm Geçmiş
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          )}
        </div>

        {isLoading && (
          <div className="space-y-2.5">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[72px] w-full rounded-xl" />
            ))}
          </div>
        )}

        {!isLoading && recentTasks.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="flex flex-col items-center justify-center py-14 text-center rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.02]"
          >
            <div className="relative mb-5">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/15 flex items-center justify-center">
                <Sparkles className="w-7 h-7 text-primary" />
              </div>
              <div className="absolute -inset-2 rounded-3xl bg-primary/5 blur-xl -z-10" />
            </div>
            <h3 className="font-semibold text-base">Henüz analiz yok</h3>
            <p className="text-sm text-muted-foreground mt-1.5 mb-5 max-w-[240px]">
              İlk analizinizi başlatarak rakiplerinizin önüne geçin.
            </p>
            <Link href="/dashboard/analyze">
              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <Button size="sm" className="gap-2">
                  <Plus className="w-3.5 h-3.5" />
                  Hemen Başla
                </Button>
              </motion.div>
            </Link>
          </motion.div>
        )}

        {!isLoading && recentTasks.length > 0 && (
          <div className="space-y-2">
            {recentTasks.map((task, index) => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.055 }}
                whileHover={{ y: -2, transition: { duration: 0.16 } }}
              >
                <Link href={getTaskLink(task)}>
                  <div className="group flex items-center gap-3.5 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 hover:bg-white/[0.06] hover:border-white/[0.11] hover:shadow-lg hover:shadow-black/20 transition-all duration-200 cursor-pointer">

                    <div className="shrink-0 w-11 h-11 rounded-lg overflow-hidden border border-white/[0.09] bg-white/[0.04] flex items-center justify-center">
                      {task.generated_image_url ? (
                        <img
                          src={task.generated_image_url}
                          alt={task.payload.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <ImageOff className="w-4 h-4 text-muted-foreground/25" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate group-hover:text-primary transition-colors">
                        {task.payload.title}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] capitalize text-muted-foreground bg-white/[0.04] px-1.5 py-0.5 rounded">
                          {task.payload.platform}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {formatDate(task.updated_at, 'd MMM, HH:mm')}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5 shrink-0">
                      <Badge variant={statusMap[task.status].variant as any} className="text-[10px]">
                        {statusMap[task.status].label}
                      </Badge>
                      <ArrowRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

    </motion.div>
  );
}
