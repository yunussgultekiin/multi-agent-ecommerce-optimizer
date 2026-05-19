'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, CircleDashed, Loader2, XCircle, AlertTriangle, ArrowLeft, RotateCcw } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent } from '@/components/ui/card';
import Cookies from 'js-cookie';
import { useAuthStore } from '@/store/auth';
import type { SSEProgressEvent, StepName, StepStatus } from '@/types';

const STEP_LABELS: Record<StepName, string> = {
  competitor_discovery: 'Rakip Keşfi',
  competitor_research: 'Rakip Araştırması',
  market_gap: 'Pazar Boşluğu',
  pricing_analysis: 'Fiyat Analizi',
  seo_context: 'SEO Bağlamı',
  seo_optimization: 'SEO Optimizasyonu',
  image_generation: 'Görsel Üretimi',
};

const STEP_ORDER: StepName[] = [
  'competitor_discovery',
  'competitor_research',
  'market_gap',
  'pricing_analysis',
  'seo_optimization',
  'image_generation',
];

function StepIcon({ status }: { status: StepStatus }) {
  if (status === 'completed') {
    return (
      <motion.div
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      >
        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
      </motion.div>
    );
  }
  if (status === 'running') {
    return (
      <motion.div
        animate={{ scale: [1, 1.12, 1] }}
        transition={{ repeat: Infinity, duration: 1.2, ease: 'easeInOut' }}
      >
        <Loader2 className="w-5 h-5 text-primary animate-spin" />
      </motion.div>
    );
  }
  if (status === 'failed') {
    return <XCircle className="w-5 h-5 text-destructive" />;
  }
  return <CircleDashed className="w-5 h-5 text-muted-foreground/40" />;
}

export default function ProgressPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const router = useRouter();
  const { toast } = useToast();
  const { fetchQuota } = useAuthStore();
  const [progress, setProgress] = useState<number>(0);
  const [steps, setSteps] = useState<Record<StepName, StepStatus>>({} as Record<StepName, StepStatus>);
  const [taskStatus, setTaskStatus] = useState<'pending' | 'running' | 'completed' | 'failed'>('pending');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [connectionLost, setConnectionLost] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const token = Cookies.get('access_token');
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const abortController = new AbortController();

    const fetchStream = async () => {
      let terminated = false;
      try {
        const response = await fetch(`${baseUrl}/analyze/${taskId}/status/stream`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: abortController.signal,
        });
        if (response.status === 429) {
          await new Promise(resolve => setTimeout(resolve, 3000));
          await fetchStream();
          return;
        }
        if (!response.ok) throw new Error('Network error');
        const reader = response.body?.getReader();
        if (!reader) return;
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;
            if (
              ['Task not found', 'Forbidden', 'Task service error', 'Task service unavailable'].includes(dataStr)
            ) {
              setErrorMessage(dataStr);
              setTaskStatus('failed');
              terminated = true;
              return;
            }
            try {
              const data: SSEProgressEvent = JSON.parse(dataStr);
              const pct =
                typeof data.pct === 'number' ? data.pct : parseFloat(String(data.pct)) || 0;
              setProgress(pct);

              if (data.step && data.status) {
                setSteps((prev: Record<StepName, StepStatus>) => ({
                  ...prev,
                  [data.step as StepName]: data.status as StepStatus,
                }));
              }

              if (data.status === 'failed' || data.status === 'cancelled') {
                setTaskStatus('failed');
                setErrorMessage(data.message || 'Analiz sırasında beklenmeyen bir hata oluştu.');
                terminated = true;
                return;
              }

              if (pct >= 100 && data.status === 'completed') {
                setTaskStatus('completed');
                fetchQuota();
                const navigateWhenReady = async () => {
                  for (let i = 0; i < 20; i++) {
                    if (abortController.signal.aborted) return;
                    try {
                      const res = await fetch(`${baseUrl}/analyze/${taskId}/result`, {
                        headers: token ? { Authorization: `Bearer ${token}` } : {},
                      });
                      if (res.ok) {
                        window.location.href = `/dashboard/result/${taskId}`;
                        return;
                      }
                    } catch (_) {}
                    await new Promise((r) => setTimeout(r, 800));
                  }
                  window.location.href = `/dashboard/result/${taskId}`;
                };
                navigateWhenReady();
                terminated = true;
                return;
              }

              setTaskStatus('running');
            } catch (_) {}
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
      }

      if (terminated) return;

      try {
        const taskRes = await fetch(`${baseUrl}/analyze/${taskId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: abortController.signal,
        });
        if (taskRes.ok) {
          const task = await taskRes.json();
          if (task.status === 'failed' || task.status === 'cancelled') {
            setTaskStatus('failed');
            setErrorMessage(task.error_message || 'Analiz sırasında beklenmeyen bir hata oluştu.');
            return;
          }
          if (task.status === 'completed') {
            setTaskStatus('completed');
            fetchQuota();
            window.location.href = `/dashboard/result/${taskId}`;
            return;
          }
        }
      } catch (_) {}

      if (!abortController.signal.aborted) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await fetchStream();
        return;
      }

      setConnectionLost(true);
      toast({
        variant: 'destructive',
        title: 'Bağlantı Koptu',
        description: 'Canlı akış bağlantısı kesildi. Sayfayı yenileyerek tekrar bağlanabilirsiniz.',
      });
    };

    fetchStream();
    return () => abortController.abort();
  }, [taskId, router, toast, fetchQuota]);

  if (taskStatus === 'failed') {
    return (
      <div className="max-w-2xl mx-auto py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="text-center space-y-6"
        >
          <div className="w-20 h-20 rounded-full bg-destructive/10 border border-destructive/20 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-10 h-10 text-destructive" />
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">Analiz Başarısız</h1>
            <p className="text-muted-foreground max-w-md mx-auto">{errorMessage}</p>
          </div>

          <Card className="text-left mt-8">
            <CardContent className="p-6">
              <h3 className="text-sm font-medium text-muted-foreground mb-4 uppercase tracking-wider">
                Adım Durumları
              </h3>
              <div className="space-y-2">
                {STEP_ORDER.map((stepKey) => {
                  const stepStatus = steps[stepKey] || 'pending';
                  return (
                    <div key={stepKey} className="flex items-center gap-3 py-1.5">
                      <StepIcon status={stepStatus} />
                      <span
                        className={`text-sm ${
                          stepStatus === 'failed'
                            ? 'text-destructive font-medium'
                            : stepStatus === 'completed'
                            ? 'text-foreground'
                            : 'text-muted-foreground'
                        }`}
                      >
                        {STEP_LABELS[stepKey]}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <div className="flex items-center justify-center gap-4 pt-4">
            <Link href="/dashboard">
              <Button variant="outline" className="gap-2">
                <ArrowLeft className="w-4 h-4" />
                Dashboard&apos;a Dön
              </Button>
            </Link>
            <Link href="/dashboard/analyze">
              <Button className="gap-2">
                <RotateCcw className="w-4 h-4" />
                Yeniden Dene
              </Button>
            </Link>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-12 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center space-y-4"
      >
        <div className="relative mx-auto w-fit">
          <div className="w-16 h-16 rounded-2xl gradient-bg flex items-center justify-center mx-auto">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <div className="absolute -inset-4 rounded-3xl bg-primary/10 blur-xl -z-10 animate-pulse-glow" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight">Analiz Sürüyor</h1>
        <p className="text-muted-foreground text-lg max-w-md mx-auto">
          Ürününüz ajan sistemi tarafından detaylıca inceleniyor...
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
      >
        <Card className="p-8 border-white/[0.08] bg-white/[0.02]">
          <div className="space-y-4">
            <div className="flex justify-between items-end mb-2">
              <span className="text-sm font-medium text-muted-foreground">Genel İlerleme</span>
              <AnimatePresence mode="wait">
                <motion.span
                  key={Math.round(progress)}
                  initial={{ scale: 1.2, opacity: 0.7 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.9, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="text-3xl font-bold text-primary tabular-nums"
                >
                  {Math.round(progress)}%
                </motion.span>
              </AnimatePresence>
            </div>
            <Progress value={progress} className="h-3" />
          </div>
        </Card>
      </motion.div>

      <AnimatePresence>
        {connectionLost && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200 text-sm flex items-center gap-3"
          >
            <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />
            <div>
              <p className="font-medium">Bağlantı koptu</p>
              <p className="text-amber-300/70">
                Sayfa yenilendiğinde otomatik olarak yeniden bağlanacaktır.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="ml-auto shrink-0 border-amber-500/30 text-amber-200 hover:bg-amber-500/10"
              onClick={() => window.location.reload()}
            >
              Yenile
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-3 max-w-2xl mx-auto relative">
        <div className="absolute left-[19px] top-6 bottom-6 w-0.5 bg-white/5 z-0" />

        {STEP_ORDER.map((stepKey, index) => {
          const stepStatus = steps[stepKey] || 'pending';
          return (
            <motion.div
              key={stepKey}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.08, duration: 0.3 }}
              className={`flex items-center gap-4 relative z-10 p-3 rounded-xl transition-all duration-300 ${
                stepStatus === 'running'
                  ? 'bg-primary/5 border border-primary/10 shadow-sm shadow-primary/5'
                  : stepStatus === 'completed'
                  ? 'bg-white/[0.02]'
                  : ''
              }`}
            >
              <div className="bg-background rounded-full">
                <StepIcon status={stepStatus} />
              </div>
              <div className="flex-1">
                <span
                  className={`text-base font-medium transition-colors ${
                    stepStatus === 'completed'
                      ? 'text-foreground'
                      : stepStatus === 'running'
                      ? 'text-primary'
                      : stepStatus === 'failed'
                      ? 'text-destructive'
                      : 'text-muted-foreground/60'
                  }`}
                >
                  {STEP_LABELS[stepKey]}
                </span>
              </div>
              <AnimatePresence mode="wait">
                {stepStatus === 'running' && (
                  <motion.span
                    key="running"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.2 }}
                    className="text-xs text-primary/70 font-medium"
                  >
                    İşleniyor...
                  </motion.span>
                )}
                {stepStatus === 'completed' && (
                  <motion.span
                    key="completed"
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="text-xs text-emerald-500/70 font-medium"
                  >
                    Tamam
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}