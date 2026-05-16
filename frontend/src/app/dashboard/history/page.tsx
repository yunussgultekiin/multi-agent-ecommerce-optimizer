'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { format } from 'date-fns';
import { tr } from 'date-fns/locale';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calendar,
  Tag,
  ArrowRight,
  Activity,
  Plus,
  Search,
  Trash2,
  ImageOff,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Ban,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import api from '@/lib/api';
import type { AnalysisTask, AnalysisStatus, SeoTone } from '@/types';

/* ── Variants ──────────────────────────────────────────────── */
const page = {
  hidden:  { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const row = {
  hidden:  { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

const cardList = {
  hidden:  { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const cardItem = {
  hidden:  { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  exit:    { opacity: 0, scale: 0.97, transition: { duration: 0.2 } },
};

/* ── Static maps ─────────────────────────────────────────────── */
const SEO_TONE_LABELS: Record<SeoTone, string> = {
  casual:       'Samimi & Genç',
  professional: 'Profesyonel',
  premium:      'Premium & Minimal',
};

/* Status config with icon + colors */
const statusConfig = {
  completed: {
    label:    'Tamamlandı',
    icon:     CheckCircle2,
    classes:  'text-emerald-400 border-emerald-500/25 bg-emerald-500/10',
    dot:      'bg-emerald-400',
  },
  running: {
    label:    'Analiz Ediliyor',
    icon:     Loader2,
    classes:  'text-blue-400 border-blue-500/25 bg-blue-500/10',
    dot:      'bg-blue-400',
    spin:     true,
  },
  failed: {
    label:    'Başarısız',
    icon:     XCircle,
    classes:  'text-red-400 border-red-500/25 bg-red-500/10',
    dot:      'bg-red-400',
  },
  pending: {
    label:    'Bekliyor',
    icon:     Clock,
    classes:  'text-amber-400 border-amber-500/25 bg-amber-500/10',
    dot:      'bg-amber-400',
  },
  cancelled: {
    label:    'İptal Edildi',
    icon:     Ban,
    classes:  'text-muted-foreground border-white/[0.09] bg-white/[0.04]',
    dot:      'bg-muted-foreground',
  },
} as const;

const STATUS_FILTERS = ['all', 'completed', 'running', 'failed', 'pending'] as const;
type Filter = (typeof STATUS_FILTERS)[number];

const FILTER_LABELS: Record<Filter, string> = {
  all:       'Tümü',
  completed: 'Tamamlanan',
  running:   'Aktif',
  failed:    'Başarısız',
  pending:   'Bekleyen',
};

function getTaskLink(task: AnalysisTask): string {
  if (task.status === 'completed') return `/dashboard/result/${task.task_id}`;
  if (task.status === 'running' || task.status === 'pending')
    return `/dashboard/analyze/${task.task_id}/progress`;
  return '#';
}

/* ── Status badge component ─────────────────────────────────── */
function StatusBadge({ status }: { status: AnalysisTask['status'] }) {
  const cfg = statusConfig[status];
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${cfg.classes}`}
    >
      <Icon className={`w-3 h-3 ${'spin' in cfg && cfg.spin ? 'animate-spin' : ''}`} />
      {cfg.label}
    </span>
  );
}

/* ── Page ───────────────────────────────────────────────────── */
export default function HistoryPage() {
  const [tasks,           setTasks]           = useState<AnalysisTask[]>([]);
  const [isLoading,       setIsLoading]       = useState(true);
  const [searchQuery,     setSearchQuery]     = useState('');
  const [filterStatus,    setFilterStatus]    = useState<AnalysisStatus | 'all'>('all');
  const [deleteDialogOpen,setDeleteDialogOpen]= useState(false);
  const [isDeleting,      setIsDeleting]      = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await api.get('/analyze');
        setTasks(res.data);
      } catch {
        toast({ variant: 'destructive', title: 'Hata', description: 'Geçmiş analizler yüklenemedi.' });
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
  }, [toast]);

  const handleDeleteAll = async () => {
    setIsDeleting(true);
    try {
      await api.delete('/analyze');
      setTasks([]);
      setDeleteDialogOpen(false);
      toast({ title: 'Geçmiş Silindi', description: 'Tüm analizler başarıyla silindi.' });
    } catch {
      toast({ variant: 'destructive', title: 'Hata', description: 'Geçmiş silinemedi.' });
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredTasks = tasks.filter((t) => {
    const q = searchQuery.toLowerCase();
    const matchSearch = t.payload.title.toLowerCase().includes(q) || t.payload.platform.toLowerCase().includes(q);
    const matchStatus = filterStatus === 'all' || t.status === filterStatus;
    return matchSearch && matchStatus;
  });

  const counts: Record<Filter, number> = {
    all:       tasks.length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    running:   tasks.filter((t) => t.status === 'running').length,
    failed:    tasks.filter((t) => t.status === 'failed').length,
    pending:   tasks.filter((t) => t.status === 'pending').length,
  };

  return (
    <motion.div variants={page} initial="hidden" animate="visible" className="space-y-6">

      {/* ── Header ──────────────────────────────────────── */}
      <motion.div variants={row} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium mb-1">Geçmiş</p>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight">Geçmiş Analizler</h1>
            {!isLoading && (
              <Badge variant="outline" className="text-[10px] border-white/[0.09] bg-white/[0.03] text-muted-foreground">
                {tasks.length}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">Tüm analiz geçmişiniz ve sonuçları</p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {tasks.length > 0 && (
            <motion.div whileTap={{ scale: 0.97 }}>
              <Button
                variant="outline"
                size="sm"
                className="h-9 gap-1.5 text-destructive border-destructive/25 hover:bg-destructive/10 hover:text-destructive"
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Trash2 className="w-3.5 h-3.5" />
                Geçmişi Temizle
              </Button>
            </motion.div>
          )}
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

      {/* ── Search + filter (only when data exists) ──────── */}
      {!isLoading && tasks.length > 0 && (
        <motion.div variants={row} className="space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Ürün adı veya platform ara…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-10"
            />
          </div>

          {/* Filter chips */}
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((s) => {
              const active = filterStatus === s;
              const dot = s !== 'all' ? statusConfig[s as Exclude<Filter,'all'>].dot : null;
              return (
                <motion.button
                  key={s}
                  whileTap={{ scale: 0.96 }}
                  onClick={() => setFilterStatus(s)}
                  className={`
                    flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border cursor-pointer
                    transition-all duration-150
                    ${active
                      ? 'bg-primary/10 border-primary/30 text-primary'
                      : 'bg-white/[0.02] border-white/[0.07] text-muted-foreground hover:bg-white/[0.05] hover:text-foreground'
                    }
                  `}
                >
                  {dot && (
                    <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-primary' : dot}`} />
                  )}
                  {FILTER_LABELS[s]}
                  <span className={`ml-0.5 ${active ? 'text-primary/70' : 'text-muted-foreground/60'}`}>
                    {counts[s]}
                  </span>
                </motion.button>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* ── States ──────────────────────────────────────── */}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-[82px] w-full rounded-xl" />
          ))}
        </div>
      )}

      {/* Empty — no tasks at all */}
      {!isLoading && tasks.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex flex-col items-center justify-center py-24 text-center"
        >
          <div className="relative mb-6">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
              <Activity className="w-8 h-8 text-muted-foreground/30" />
            </div>
            <div className="absolute -inset-3 rounded-3xl bg-primary/5 blur-xl -z-10" />
          </div>
          <h2 className="text-xl font-bold">Henüz analiz yok</h2>
          <p className="text-sm text-muted-foreground mt-2 max-w-xs mb-7">
            İlk analizini başlat, ürününün pazar konumunu keşfet.
          </p>
          <Link href="/dashboard/analyze">
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Button size="sm" className="gap-2">
                <Plus className="w-3.5 h-3.5" />
                Analiz Başlat
              </Button>
            </motion.div>
          </Link>
        </motion.div>
      )}

      {/* Empty — no search results */}
      {!isLoading && tasks.length > 0 && filteredTasks.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16"
        >
          <Search className="w-9 h-9 text-muted-foreground/25 mx-auto mb-3" />
          <p className="font-medium">Sonuç bulunamadı</p>
          <p className="text-sm text-muted-foreground mt-1">Arama veya filtre kriterlerini değiştirin.</p>
        </motion.div>
      )}

      {/* Card list */}
      {!isLoading && filteredTasks.length > 0 && (
        <motion.div variants={cardList} initial="hidden" animate="visible" className="space-y-2.5">
          <AnimatePresence mode="popLayout">
            {filteredTasks.map((task) => (
              <motion.div
                key={task.task_id}
                variants={cardItem}
                layout
                exit="exit"
                whileHover={{ y: -3, transition: { duration: 0.16 } }}
              >
                <Link href={getTaskLink(task)}>
                  <div className="group relative flex items-center gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 hover:bg-white/[0.06] hover:border-white/[0.11] hover:shadow-xl hover:shadow-black/20 transition-all duration-200 cursor-pointer">

                    {/* Thumbnail */}
                    <div className="shrink-0 w-14 h-14 rounded-xl overflow-hidden border border-white/[0.09] bg-white/[0.04] flex items-center justify-center">
                      {task.generated_image_url ? (
                        <img
                          src={task.generated_image_url}
                          alt={task.payload.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <ImageOff className="w-5 h-5 text-muted-foreground/25" />
                      )}
                    </div>

                    {/* Body */}
                    <div className="flex-1 min-w-0 space-y-1.5">
                      {/* Title row */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <StatusBadge status={task.status} />
                        <span className="font-semibold text-sm truncate group-hover:text-primary transition-colors">
                          {task.payload.title}
                        </span>
                      </div>

                      {/* Meta row */}
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Tag className="w-3 h-3" />
                          <span className="capitalize">{task.payload.platform}</span>
                        </span>

                        {task.payload.seo_tone && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md border border-violet-500/20 bg-violet-500/8 text-violet-400 text-[10px]">
                            {SEO_TONE_LABELS[task.payload.seo_tone]}
                          </span>
                        )}

                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {format(new Date(task.updated_at), 'd MMM yyyy, HH:mm', { locale: tr })}
                        </span>
                      </div>
                    </div>

                    {/* Arrow */}
                    <div className="shrink-0 flex items-center gap-1.5 text-primary text-xs font-medium opacity-0 group-hover:opacity-100 transition-all duration-200 -translate-x-2 group-hover:translate-x-0">
                      <span className="hidden sm:inline">Detaylar</span>
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      {/* ── Delete dialog ─────────────────────────────── */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Geçmişi Temizle</DialogTitle>
            <DialogDescription>
              Tüm analizleriniz kalıcı olarak silinecek. Bu işlem geri alınamaz.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 mt-2">
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={isDeleting}
            >
              Vazgeç
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteAll}
              disabled={isDeleting}
              className="gap-2"
            >
              <Trash2 className="w-4 h-4" />
              {isDeleting ? 'Siliniyor…' : 'Evet, Sil'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </motion.div>
  );
}
