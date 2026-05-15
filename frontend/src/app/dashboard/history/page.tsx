'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { format } from 'date-fns';
import { tr } from 'date-fns/locale';
import { motion } from 'framer-motion';
import { Calendar, Tag, ArrowRight, Activity, Plus, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import api from '@/lib/api';
import type { AnalysisTask, AnalysisStatus } from '@/types';

const statusMap = {
  pending: { label: 'Bekliyor', variant: 'pending' },
  running: { label: 'Analiz Ediliyor', variant: 'info' },
  completed: { label: 'Tamamlandı', variant: 'success' },
  failed: { label: 'Başarısız', variant: 'destructive' },
  cancelled: { label: 'İptal Edildi', variant: 'outline' },
} as const;

const STATUS_FILTERS = ['all', 'completed', 'running', 'failed', 'pending'] as const;

const STATUS_LABELS: Record<(typeof STATUS_FILTERS)[number], string> = {
  all: 'Tümü',
  completed: 'Tamamlanan',
  running: 'Devam Eden',
  failed: 'Başarısız',
  pending: 'Bekleyen',
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

function getTaskLink(task: AnalysisTask): string {
  if (task.status === 'completed') return `/dashboard/result/${task.task_id}`;
  if (task.status === 'running' || task.status === 'pending')
    return `/dashboard/analyze/${task.task_id}/progress`;
  return '#';
}

export default function HistoryPage() {
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<AnalysisStatus | 'all'>('all');
  const { toast } = useToast();

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await api.get('/analyze');
        setTasks(res.data);
      } catch {
        toast({ variant: 'destructive', title: 'Hata', description: 'Geçmiş analizler yüklenemedi.' });
      } finally {
        setIsLoading(false);
      }
    };
    fetchHistory();
  }, [toast]);

  const filteredTasks = tasks.filter((task) => {
    const matchesSearch =
      task.payload.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      task.payload.platform.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'all' || task.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const statusCounts = {
    all: tasks.length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    running: tasks.filter((t) => t.status === 'running').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
    pending: tasks.filter((t) => t.status === 'pending').length,
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      <motion.div
        variants={itemVariants}
        className="flex flex-col md:flex-row md:items-end justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Geçmiş Analizler</h1>
          <p className="text-muted-foreground mt-1">Daha önce yaptığınız tüm analizlerin listesi.</p>
        </div>
        <Link href="/dashboard/analyze">
          <Button className="w-full md:w-auto gap-2">
            <Plus className="w-4 h-4" />
            Yeni Analiz
          </Button>
        </Link>
      </motion.div>

      {!isLoading && tasks.length > 0 && (
        <motion.div variants={itemVariants} className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Analiz ara (ürün adı veya platform)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-11 bg-white/[0.03]"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((status) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border ${
                  filterStatus === status
                    ? 'bg-primary/10 border-primary/30 text-primary'
                    : 'bg-white/[0.02] border-white/5 text-muted-foreground hover:bg-white/[0.05] hover:text-foreground'
                }`}
              >
                {STATUS_LABELS[status]} ({statusCounts[status]})
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <motion.div
          variants={itemVariants}
          className="flex flex-col items-center justify-center py-24 text-center"
        >
          <div className="relative mb-6">
            <div className="w-20 h-20 rounded-2xl bg-white/5 flex items-center justify-center">
              <Activity className="w-10 h-10 text-muted-foreground/50" />
            </div>
            <div className="absolute -inset-3 rounded-3xl bg-primary/5 blur-xl -z-10" />
          </div>
          <h2 className="text-2xl font-bold">Henüz analiz bulunmuyor</h2>
          <p className="text-muted-foreground mt-2 max-w-sm mb-8">
            İlk ürün analizini başlatarak pazar boşluklarını ve optimal fiyatlandırmayı hemen keşfedin.
          </p>
          <Link href="/dashboard/analyze">
            <Button size="lg" className="h-12 px-8 gap-2 shadow-lg shadow-indigo-500/10">
              <Plus className="w-4 h-4" />
              Analiz Başlat
            </Button>
          </Link>
        </motion.div>
      ) : filteredTasks.length === 0 ? (
        <motion.div variants={itemVariants} className="text-center py-16">
          <Search className="w-10 h-10 text-muted-foreground/30 mx-auto mb-4" />
          <h3 className="text-lg font-medium">Sonuç bulunamadı</h3>
          <p className="text-sm text-muted-foreground mt-1">Filtrelerinizi değiştirmeyi deneyin.</p>
        </motion.div>
      ) : (
        <motion.div variants={containerVariants} className="grid gap-3">
          {filteredTasks.map((task) => (
            <motion.div key={task.task_id} variants={itemVariants}>
              <Link href={getTaskLink(task)}>
                <Card className="hover:bg-white/[0.06] transition-all duration-200 cursor-pointer group border-white/5 hover:border-white/10">
                  <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-2 min-w-0">
                      <div className="flex items-center gap-3 flex-wrap">
                        <Badge variant={statusMap[task.status].variant as any}>
                          {statusMap[task.status].label}
                        </Badge>
                        <h3 className="font-semibold text-base group-hover:text-primary transition-colors truncate">
                          {task.payload.title}
                        </h3>
                      </div>
                      <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <Tag className="w-3.5 h-3.5" />
                          <span className="capitalize">{task.payload.platform}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5" />
                          <span>
                            {format(new Date(task.updated_at), 'd MMM yyyy, HH:mm', { locale: tr })}
                          </span>
                        </div>
                        {task.payload.brand && (
                          <span className="text-xs px-2 py-0.5 bg-white/5 rounded">
                            {task.payload.brand}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-primary font-medium opacity-0 group-hover:opacity-100 transition-all duration-200 translate-x-[-8px] group-hover:translate-x-0 shrink-0">
                      <span className="text-sm">Detaylar</span>
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}
