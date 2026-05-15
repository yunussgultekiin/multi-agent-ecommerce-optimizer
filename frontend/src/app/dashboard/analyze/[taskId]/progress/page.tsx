'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { CheckCircle2, CircleDashed, Loader2, XCircle, AlertTriangle, ArrowLeft, RotateCcw } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent } from '@/components/ui/card';
import Cookies from 'js-cookie';
import type { SSEProgressEvent, StepName, StepStatus } from '@/types';

const STEP_LABELS: Record<StepName, string> = {
  competitor_discovery: 'Rakip Keşfi',
  competitor_research: 'Rakip Araştırması',
  vision_synthesis: 'Görsel Sentezi',
  market_gap: 'Pazar Boşluğu Analizi',
  pricing_analysis: 'Fiyat Analizi',
  seo_context: 'SEO Bağlamı',
  seo_optimization: 'SEO Optimizasyonu',
  image_generation: 'Görsel Üretimi',
};

const STEP_ORDER: StepName[] = [
  'competitor_discovery',
  'competitor_research',
  'vision_synthesis',
  'market_gap',
  'pricing_analysis',
  'seo_context',
  'seo_optimization',
  'image_generation',
];

function StepIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
    case 'running':
      return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
    case 'failed':
      return <XCircle className="w-5 h-5 text-destructive" />;
    default:
      return <CircleDashed className="w-5 h-5 text-muted-foreground/40" />;
  }
}

export default function ProgressPage({ params }: { params: { taskId: string } }) {
  const router = useRouter();
  const { toast } = useToast();
  const [progress, setProgress] = useState<number>(0);
  const [steps, setSteps] = useState<Record<StepName, StepStatus>>({} as Record<StepName, StepStatus>);
  const [taskStatus, setTaskStatus] = useState<'pending' | 'running' | 'completed' | 'failed'>('pending');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [connectionLost, setConnectionLost] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const token = Cookies.get('access_token');
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${baseUrl}/analyze/${params.taskId}/status/stream${token ? `?token=${token}` : ''}`;

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data: SSEProgressEvent = JSON.parse(event.data);
        setProgress(data.pct);
        setSteps(data.steps);
        setTaskStatus(data.status as typeof taskStatus);
        setConnectionLost(false);

        if (data.status === 'completed') {
          eventSource.close();
          toast({ title: 'Analiz Tamamlandı!', description: 'Sonuçlarınız hazır.', variant: 'success' as any });
          setTimeout(() => {
            router.push(`/dashboard/result/${params.taskId}`);
          }, 1500);
        } else if (data.status === 'failed') {
          eventSource.close();
          setErrorMessage(data.message || 'Analiz sırasında beklenmeyen bir hata oluştu.');
        }
      } catch (err) {
        console.error('Failed to parse SSE event', err);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setConnectionLost(true);
      toast({
        variant: 'destructive',
        title: 'Bağlantı Koptu',
        description: 'Canlı akış bağlantısı kesildi. Sayfayı yenileyerek tekrar bağlanabilirsiniz.',
      });
    };

    return () => {
      eventSource.close();
    };
  }, [params.taskId, router, toast]);

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
        <h1 className="text-4xl font-bold tracking-tight">AI Analizi Sürüyor</h1>
        <p className="text-muted-foreground text-lg max-w-md mx-auto">
          Ürününüz yapay zeka ajanları tarafından detaylıca inceleniyor...
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
      >
        <Card className="glass-card p-8 border-white/10 bg-white/[0.02]">
          <div className="space-y-4">
            <div className="flex justify-between items-end mb-2">
              <span className="text-sm font-medium text-muted-foreground">Genel İlerleme</span>
              <motion.span
                key={Math.round(progress)}
                initial={{ scale: 1.2, opacity: 0.7 }}
                animate={{ scale: 1, opacity: 1 }}
                className="text-3xl font-bold text-primary tabular-nums"
              >
                {Math.round(progress)}%
              </motion.span>
            </div>
            <Progress value={progress} className="h-3" />
          </div>
        </Card>
      </motion.div>

      {connectionLost && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
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
              {stepStatus === 'running' && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-xs text-primary/70 font-medium"
                >
                  İşleniyor...
                </motion.span>
              )}
              {stepStatus === 'completed' && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.5 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-xs text-emerald-500/70 font-medium"
                >
                  Tamam
                </motion.span>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
