'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { formatDate } from '@/lib/utils';
import {
  Check,
  Copy,
  ExternalLink,
  Target,
  TrendingUp,
  Search,
  Image as ImageIcon,
  DollarSign,
  AlertTriangle,
  Lightbulb,
  Star,
  ArrowLeft,
  Download,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import api from '@/lib/api';
import type { AnalysisResult, SeoTone } from '@/types';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

const SEO_TONE_LABELS: Record<SeoTone, string> = {
  casual: 'Samimi & Genç',
  professional: 'Profesyonel',
  premium: 'Premium & Minimal',
};

const PLATFORM_COLORS: Record<string, string> = {
  trendyol: 'text-orange-400 border-orange-400/30 bg-orange-400/10',
  amazon: 'text-amber-400 border-amber-400/30 bg-amber-400/10',
  hepsiburada: 'text-red-400 border-red-400/30 bg-red-400/10',
};

export default function ResultPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});
  const { toast } = useToast();

  useEffect(() => {
    const fetchResult = async () => {
      let resultRes;
      let taskRes;

      for (let attempt = 0; attempt < 10; attempt++) {
        try {
          [resultRes, taskRes] = await Promise.all([
            api.get(`/analyze/${taskId}/result`),
            api.get(`/analyze/${taskId}`),
          ]);
          break;
        } catch (_err: any) {
          if (attempt < 9) {
            await new Promise((r) => setTimeout(r, 1000));
            continue;
          }
          setIsLoading(false);
          return;
        }
      }

      if (!resultRes || !taskRes) {
        setIsLoading(false);
        return;
      }

      try {
        const { task_id, result: raw, created_at } = resultRes.data;
        const task = taskRes.data;
        const { rival_json, seo_output, generated_image_url } = raw || {};
        const {
          user_product,
          target_platform,
          competitor_research_results,
          gap_result,
          pricing_result,
        } = rival_json || {};

        const competitors = (competitor_research_results || []).map((cr: any) => ({
          name: cr.competitor_name || '',
          price: cr.estimated_price || 0,
          rating: cr.rating || 0,
          review_count: cr.review_count || 0,
          brand: cr.brand || cr.competitor_name || '',
          source_url: '',
        }));

        const market_gap = {
          clusters: (gap_result?.clusters || []).map((c: any, idx: number) => ({
            cluster_id: idx,
            keywords: [c.label, ...(c.competitors || [])].filter(Boolean),
            avg_price: ((c.price_range_min || 0) + (c.price_range_max || 0)) / 2,
            saturation: 0.5,
          })),
          gap_opportunities: gap_result?.gap_opportunities || [],
          positioning_rationale: gap_result?.positioning_rationale || '',
        };

        const pricing = {
          current_position: pricing_result?.positioning || 'optimal',
          suggested_min: pricing_result?.price_range_min || 0,
          suggested_max: pricing_result?.price_range_max || 0,
          optimal_price: pricing_result?.predicted_price || 0,
          confidence_score: pricing_result?.confidence_score || 0,
          competitor_prices: (competitor_research_results || [])
            .filter((cr: any) => cr.estimated_price != null)
            .map((cr: any) => ({ name: cr.competitor_name, price: cr.estimated_price })),
        };

        const seo = {
          title_suggestion: seo_output?.title_suggestion || '',
          meta_description: seo_output?.meta_description || '',
          keyword_gaps: seo_output?.keyword_gaps || [],
          content_recommendations: seo_output?.content_recommendations || [],
          platform_tips: seo_output?.platform_specific_tips || [],
          product_development_ideas: seo_output?.product_development_ideas || [],
        };

        const vision = {
          generation_prompt: seo_output?.competitor_comparison_summary || '',
          dominant_colors: [],
          improvement_suggestions: seo_output?.content_recommendations?.slice(0, 3) || [],
        };

        setResult({
          task_id,
          product_title: user_product?.title || '',
          platform: target_platform || 'trendyol',
          analyzed_at: created_at,
          status: 'completed',
          seo_tone: task?.seo_tone ?? undefined,
          competitors,
          market_gap,
          pricing,
          seo,
          vision,
          generated_image_url: generated_image_url || null,
        });
      } catch {
        toast({
          variant: 'destructive',
          title: 'Hata',
          description: 'Analiz sonuçları yüklenemedi.',
        });
      } finally {
        setIsLoading(false);
      }
    };
    fetchResult();
  }, [taskId, toast]);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedStates((prev) => ({ ...prev, [id]: true }));
    toast({ title: 'Kopyalandı', description: 'Panoya başarıyla kopyalandı.' });
    setTimeout(() => {
      setCopiedStates((prev) => ({ ...prev, [id]: false }));
    }, 2000);
  };

  const CopyButton = ({ text, id }: { text: string; id: string }) => (
    <Button
      variant="ghost"
      size="icon"
      onClick={(e) => { e.stopPropagation(); copyToClipboard(text, id); }}
      className="shrink-0 h-7 w-7"
    >
      {copiedStates[id]
        ? <Check className="h-3.5 w-3.5 text-emerald-500" />
        : <Copy className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
      }
    </Button>
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-40 w-full rounded-2xl" />
        <div className="grid lg:grid-cols-[5fr_7fr] gap-6">
          <Skeleton className="h-[480px] w-full rounded-2xl" />
          <div className="space-y-4">
            <Skeleton className="h-56 w-full rounded-2xl" />
            <Skeleton className="h-56 w-full rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle className="w-12 h-12 text-amber-500 mb-4" />
        <h2 className="text-xl font-semibold">Sonuç bulunamadı</h2>
        <p className="text-muted-foreground mt-2 mb-6">
          Analiz sonuçları henüz hazır değil veya bulunamadı.
        </p>
        <Link href="/dashboard">
          <Button variant="outline" className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Dashboard&apos;a Dön
          </Button>
        </Link>
      </div>
    );
  }

  const chartData = result.pricing.competitor_prices
    .sort((a, b) => a.price - b.price)
    .map((p) => ({
      name: p.name.length > 15 ? p.name.substring(0, 15) + '...' : p.name,
      price: p.price,
    }));

  const maxCompetitorPrice = result.competitors.length > 0
    ? Math.max(...result.competitors.map((c) => c.price))
    : 1;

  return (
    <AnimatePresence>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="space-y-8"
      >
        <motion.div variants={itemVariants}>
          <Link href="/dashboard/history">
            <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-foreground -ml-2">
              <ArrowLeft className="w-4 h-4" />
              Analizlere Dön
            </Button>
          </Link>
        </motion.div>

        <motion.div variants={itemVariants}>
          <div className="glass-card rounded-2xl overflow-hidden relative border border-white/[0.08]">
            <div className="absolute top-0 right-0 w-80 h-80 bg-primary/8 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-60 h-60 bg-violet-500/8 rounded-full blur-[100px] pointer-events-none" />
            <div className="p-6 md:p-8 relative">
              <div className="flex flex-col md:flex-row justify-between items-start gap-6">
                <div className="space-y-3 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant="outline"
                      className={`capitalize px-3 py-1 text-xs font-medium ${PLATFORM_COLORS[result.platform] ?? ''}`}
                    >
                      {result.platform}
                    </Badge>
                    <Badge variant="success" className="px-3 py-1 text-xs">
                      Analiz Tamamlandı
                    </Badge>
                    {result.seo_tone && (
                      <Badge variant="outline" className="px-3 py-1 text-xs text-violet-400 border-violet-400/30 bg-violet-400/10">
                        {SEO_TONE_LABELS[result.seo_tone]}
                      </Badge>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatDate(result.analyzed_at, 'd MMM yyyy, HH:mm')}
                    </span>
                  </div>
                  <h1 className="text-xl md:text-2xl lg:text-3xl font-bold tracking-tight leading-snug">
                    {result.product_title}
                  </h1>
                </div>

                <div className="flex flex-col items-center gap-1 bg-white/[0.04] border border-white/[0.08] px-5 py-4 rounded-2xl shrink-0 min-w-[130px]">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Optimal Fiyat</span>
                  <span className="text-3xl font-bold gradient-text">₺{result.pricing.optimal_price.toFixed(0)}</span>
                  <span className="text-[10px] text-muted-foreground">Güven %{Math.round(result.pricing.confidence_score * 100)}</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 mt-5 pt-5 border-t border-white/[0.05]">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/15 flex items-center justify-center shrink-0">
                    <Target className="w-4 h-4 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-base font-bold">{result.competitors.length}</p>
                    <p className="text-[10px] text-muted-foreground">Rakip bulundu</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center shrink-0">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-base font-bold">{result.market_gap.gap_opportunities.length}</p>
                    <p className="text-[10px] text-muted-foreground">Pazar fırsatı</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-violet-500/15 flex items-center justify-center shrink-0">
                    <Search className="w-4 h-4 text-violet-400" />
                  </div>
                  <div>
                    <p className="text-base font-bold">{result.seo.keyword_gaps.length}</p>
                    <p className="text-[10px] text-muted-foreground">Anahtar kelime</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        <div className="grid lg:grid-cols-[5fr_7fr] gap-6 items-start">

          <motion.div
            initial={{ opacity: 0, x: -40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.55, delay: 0.15 }}
            className="space-y-0"
          >
            <div className="glass-card rounded-2xl overflow-hidden border border-white/[0.08]">
              <div className="px-4 pt-4 pb-3 flex items-center justify-between border-b border-white/[0.05]">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg gradient-bg flex items-center justify-center">
                    <ImageIcon className="w-3.5 h-3.5 text-white" />
                  </div>
                  <span className="text-sm font-semibold">Ürün Görseli</span>
                </div>
                {result.generated_image_url && (
                  <a href={result.generated_image_url} target="_blank" rel="noreferrer" download>
                    <Button variant="ghost" size="sm" className="gap-1.5 text-xs h-7 text-muted-foreground hover:text-foreground">
                      <Download className="w-3 h-3" />
                      İndir
                    </Button>
                  </a>
                )}
              </div>

              {result.generated_image_url ? (
                <img
                  src={result.generated_image_url}
                  alt="Oluşturulan Ürün Görseli"
                  className="w-full h-auto object-cover"
                />
              ) : (
                <div className="aspect-square bg-gradient-to-br from-indigo-500/10 via-violet-500/10 to-purple-500/10 flex flex-col items-center justify-center relative">
                  <div className="absolute inset-0 bg-grid-sm pointer-events-none" />
                  <div className="relative z-10 flex flex-col items-center gap-4 text-center p-8">
                    <div className="w-20 h-20 rounded-2xl bg-white/[0.05] border border-white/[0.10] flex items-center justify-center">
                      <ImageIcon className="w-10 h-10 text-muted-foreground/25" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground/60">Görsel oluşturulamadı</p>
                      <p className="text-xs text-muted-foreground/35 mt-1">Ürün görseli sağlanmadı veya yükleme başarısız oldu</p>
                    </div>
                  </div>
                </div>
              )}

              {result.vision.dominant_colors.length > 0 && (
                <div className="px-4 py-3 border-t border-white/[0.05]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2.5">Renk Paleti</p>
                  <div className="flex items-center gap-2">
                    {result.vision.dominant_colors.slice(0, 6).map((color, i) => (
                      <div
                        key={i}
                        className="w-7 h-7 rounded-lg border border-white/[0.15] shadow-inner shrink-0"
                        style={{ backgroundColor: color }}
                        title={color}
                      />
                    ))}
                    <span className="text-[10px] font-mono text-muted-foreground/40 ml-1">
                      {result.vision.dominant_colors[0]}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="space-y-4"
          >

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.25 }}
              whileHover={{ y: -3, transition: { duration: 0.18 } }}
            >
              <div className="glass-card rounded-2xl overflow-hidden border border-white/[0.08]">
                <div className="h-0.5 bg-gradient-to-r from-blue-500 via-blue-400 to-cyan-400" />
                <div className="p-4 border-b border-white/[0.05]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-blue-500/15 border border-blue-500/20 flex items-center justify-center">
                        <TrendingUp className="w-4 h-4 text-blue-400" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">Rival Agent</p>
                        <p className="text-[10px] text-muted-foreground">Rekabet analizi</p>
                      </div>
                    </div>
                    <Badge variant="outline" className="text-[10px] text-blue-400 border-blue-400/30 bg-blue-400/10 font-medium">
                      {result.competitors.length} rakip
                    </Badge>
                  </div>
                </div>

                <div className="p-4 space-y-4">
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2.5">Rakipler</p>
                    <div className="space-y-2.5">
                      {result.competitors.slice(0, 4).map((comp, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.35 + i * 0.07 }}
                          className="flex items-center gap-3"
                        >
                          <div className="w-5 h-5 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
                            <span className="text-[9px] font-bold text-blue-400">{i + 1}</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium truncate mb-1">{comp.name}</p>
                            <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden">
                              <div
                                className="h-full bg-blue-400/40 rounded-full transition-all"
                                style={{ width: `${(comp.price / maxCompetitorPrice) * 100}%` }}
                              />
                            </div>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <div className="flex items-center gap-0.5">
                              <Star className="w-2.5 h-2.5 text-amber-500 fill-amber-500" />
                              <span className="text-[10px] text-muted-foreground">{comp.rating}</span>
                            </div>
                            <span className="text-xs font-bold tabular-nums">₺{comp.price.toFixed(0)}</span>
                            {comp.source_url && (
                              <a href={comp.source_url} target="_blank" rel="noreferrer">
                                <ExternalLink className="w-3 h-3 text-muted-foreground/40 hover:text-blue-400 transition-colors" />
                              </a>
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-center">
                      <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1">Min</p>
                      <p className="text-sm font-bold tabular-nums">₺{result.pricing.suggested_min.toFixed(0)}</p>
                    </div>
                    <div className="p-2.5 rounded-xl bg-primary/[0.08] border border-primary/20 text-center relative overflow-hidden">
                      <div className="absolute inset-0 bg-gradient-to-b from-primary/10 to-transparent pointer-events-none" />
                      <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1 relative">Optimal</p>
                      <p className="text-sm font-bold text-primary tabular-nums relative">₺{result.pricing.optimal_price.toFixed(0)}</p>
                    </div>
                    <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-center">
                      <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1">Max</p>
                      <p className="text-sm font-bold tabular-nums">₺{result.pricing.suggested_max.toFixed(0)}</p>
                    </div>
                  </div>

                  {result.market_gap.gap_opportunities.length > 0 && (
                    <div className="p-3 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20">
                      <div className="flex items-start gap-2.5">
                        <Lightbulb className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          <span className="text-emerald-400 font-semibold">Fırsat: </span>
                          {result.market_gap.gap_opportunities[0]}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.4 }}
              whileHover={{ y: -3, transition: { duration: 0.18 } }}
            >
              <div className="glass-card rounded-2xl overflow-hidden border border-white/[0.08]">
                <div className="h-0.5 bg-gradient-to-r from-violet-500 via-purple-400 to-pink-400" />
                <div className="p-4 border-b border-white/[0.05]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-violet-500/15 border border-violet-500/20 flex items-center justify-center">
                        <Search className="w-4 h-4 text-violet-400" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">SEO Agent</p>
                        <p className="text-[10px] text-muted-foreground">İçerik optimizasyonu</p>
                      </div>
                    </div>
                    {result.seo_tone && (
                      <Badge variant="outline" className="text-[10px] text-violet-400 border-violet-400/30 bg-violet-400/10">
                        {SEO_TONE_LABELS[result.seo_tone]}
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="p-4 space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">SEO Başlığı</p>
                      <CopyButton text={result.seo.title_suggestion} id="title-quick" />
                    </div>
                    <div className="p-3 bg-violet-500/[0.04] rounded-xl border border-violet-500/15">
                      <p className="text-sm font-semibold leading-snug">{result.seo.title_suggestion}</p>
                      <p className="text-[10px] text-muted-foreground/40 mt-1.5">{result.seo.title_suggestion.length} karakter</p>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Meta Açıklama</p>
                      <CopyButton text={result.seo.meta_description} id="meta-quick" />
                    </div>
                    <p className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.06] text-xs text-muted-foreground leading-relaxed">
                      {result.seo.meta_description}
                    </p>
                  </div>

                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2">Anahtar Kelimeler</p>
                    <div className="flex flex-wrap gap-1.5">
                      {result.seo.keyword_gaps.slice(0, 7).map((kw, i) => (
                        <Badge
                          key={i}
                          variant="outline"
                          className="text-[10px] border-violet-500/20 bg-violet-500/[0.06] text-violet-300"
                        >
                          {kw}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {result.seo.platform_tips.length > 0 && (
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2 flex items-center gap-1.5">
                        Platform Önerileri
                        <Badge
                          variant="outline"
                          className={`text-[9px] capitalize ml-0.5 ${PLATFORM_COLORS[result.platform] ?? ''}`}
                        >
                          {result.platform}
                        </Badge>
                      </p>
                      <ul className="space-y-1.5">
                        {result.seo.platform_tips.slice(0, 3).map((tip, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                            <div className="mt-1.5 w-1 h-1 rounded-full bg-violet-500 shrink-0" />
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>

        <motion.div variants={itemVariants} className="space-y-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight">Detaylı Rapor</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Rakip analizi, pazar boşlukları, fiyatlandırma ve görsel önerileri
            </p>
          </div>

          <Tabs defaultValue="competitors" className="w-full">
            <TabsList className="w-full justify-start overflow-x-auto bg-white/[0.03] border border-white/5 p-1">
              <TabsTrigger value="competitors" className="gap-2">
                <Target className="w-4 h-4" /> Rakipler
              </TabsTrigger>
              <TabsTrigger value="market" className="gap-2">
                <TrendingUp className="w-4 h-4" /> Pazar Boşluğu
              </TabsTrigger>
              <TabsTrigger value="pricing" className="gap-2">
                <DollarSign className="w-4 h-4" /> Fiyat
              </TabsTrigger>
              <TabsTrigger value="seo" className="gap-2">
                <Search className="w-4 h-4" /> SEO Detay
              </TabsTrigger>
            </TabsList>

            <TabsContent value="competitors" className="space-y-4 mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Bulunan Rakipler</CardTitle>
                  <CardDescription>
                    Pazardaki ana rakiplerinizin güncel durumu ({result.competitors.length} rakip)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="text-xs text-muted-foreground uppercase bg-white/[0.03]">
                        <tr>
                          <th className="px-6 py-4 rounded-tl-lg">Rakip Adı</th>
                          <th className="px-6 py-4">Marka</th>
                          <th className="px-6 py-4">Fiyat</th>
                          <th className="px-6 py-4">Değerlendirme</th>
                          <th className="px-6 py-4 rounded-tr-lg text-right">Link</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {result.competitors.map((comp, i) => (
                          <motion.tr
                            key={i}
                            initial={{ opacity: 0, y: 5 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="hover:bg-white/[0.02] transition-colors"
                          >
                            <td className="px-6 py-4 font-medium text-foreground max-w-xs truncate" title={comp.name}>
                              {comp.name}
                            </td>
                            <td className="px-6 py-4 text-muted-foreground">{comp.brand}</td>
                            <td className="px-6 py-4 font-semibold">₺{comp.price.toFixed(2)}</td>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-1.5">
                                <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                                <span className="font-medium">{comp.rating}</span>
                                <span className="text-muted-foreground text-xs">({comp.review_count})</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-right">
                              {comp.source_url && (
                                <a
                                  href={comp.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-primary hover:underline inline-flex items-center gap-1 text-xs font-medium"
                                >
                                  İncele <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="market" className="space-y-6 mt-6">
              <div className="grid md:grid-cols-3 gap-6">
                <Card className="md:col-span-2">
                  <CardHeader>
                    <CardTitle>Pazar Boşluğu Fırsatları</CardTitle>
                    <CardDescription>Rakiplerin odaklanmadığı alanlar</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="p-5 rounded-xl bg-gradient-to-br from-primary/10 to-violet-500/10 border border-primary/20 leading-relaxed">
                      <div className="flex items-start gap-3">
                        <Lightbulb className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                        <p className="text-sm">{result.market_gap.positioning_rationale}</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <h4 className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">
                        Fırsat Alanları
                      </h4>
                      {result.market_gap.gap_opportunities.map((gap, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.08 }}
                          className="flex items-start gap-3 p-3 rounded-lg border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
                        >
                          <Check className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                          <span className="text-sm">{gap}</span>
                        </motion.div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <div className="space-y-4">
                  {result.market_gap.clusters.map((cluster) => (
                    <Card key={cluster.cluster_id} className="hover:bg-white/[0.04] transition-colors">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-primary" />
                          Küme {cluster.cluster_id + 1}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex justify-between items-center mb-3">
                          <span className="text-xs text-muted-foreground">Ort. Fiyat:</span>
                          <span className="font-bold text-sm">₺{cluster.avg_price.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center mb-3">
                          <span className="text-xs text-muted-foreground">Doygunluk:</span>
                          <span className="font-bold text-sm">%{Math.round(cluster.saturation * 100)}</span>
                        </div>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {cluster.keywords.map((kw, i) => (
                            <Badge key={i} variant="secondary" className="text-[10px]">{kw}</Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="pricing" className="space-y-6 mt-6">
              <div className="grid md:grid-cols-3 gap-4">
                <Card className="relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-20 h-20 bg-primary/10 rounded-full blur-2xl pointer-events-none" />
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Önerilen Fiyat Aralığı</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      ₺{result.pricing.suggested_min.toFixed(2)} – ₺{result.pricing.suggested_max.toFixed(2)}
                    </div>
                  </CardContent>
                </Card>
                <Card className="relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Pazar Konumu</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold capitalize">
                      {result.pricing.current_position.replace('_', ' ')}
                    </div>
                  </CardContent>
                </Card>
                <Card className="relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-20 h-20 bg-violet-500/10 rounded-full blur-2xl pointer-events-none" />
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Güven Skoru</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-2">
                      <div className="text-2xl font-bold">
                        %{Math.round(result.pricing.confidence_score * 100)}
                      </div>
                      {result.pricing.confidence_score > 0.8 ? (
                        <Badge variant="success">Yüksek</Badge>
                      ) : result.pricing.confidence_score > 0.5 ? (
                        <Badge variant="warning">Orta</Badge>
                      ) : (
                        <Badge variant="destructive">Düşük</Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Rakip Fiyat Dağılımı</CardTitle>
                  <CardDescription>Pazardaki diğer ürünlerle fiyat karşılaştırmanız</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[400px] w-full mt-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(245, 58%, 61%)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(245, 58%, 61%)" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis
                          stroke="#888888"
                          fontSize={12}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(v) => `₺${v}`}
                        />
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(222, 47%, 8%)',
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderRadius: '12px',
                            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                          }}
                          itemStyle={{ color: 'hsl(210, 40%, 98%)' }}
                          labelStyle={{ color: 'hsl(215, 20%, 55%)' }}
                        />
                        <ReferenceLine
                          y={result.pricing.optimal_price}
                          label={{ value: 'Önerilen', fill: 'hsl(245, 58%, 61%)', fontSize: 12 }}
                          stroke="hsl(245, 58%, 61%)"
                          strokeDasharray="5 5"
                          strokeWidth={2}
                        />
                        <Area
                          type="monotone"
                          dataKey="price"
                          stroke="hsl(245, 58%, 61%)"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#colorPrice)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="seo" className="space-y-6 mt-6">
              {result.seo_tone && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>Seçili SEO Tonu:</span>
                  <Badge variant="outline" className="text-violet-400 border-violet-400/30 bg-violet-400/10">
                    {SEO_TONE_LABELS[result.seo_tone]}
                  </Badge>
                </div>
              )}

              <div className="grid md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-3">
                    <CardTitle className="text-base">SEO Başlık Önerisi</CardTitle>
                    <CopyButton text={result.seo.title_suggestion} id="title" />
                  </CardHeader>
                  <CardContent>
                    <p className="p-4 bg-white/5 rounded-xl border border-white/10 text-lg font-medium leading-relaxed">
                      {result.seo.title_suggestion}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-3">
                    <CardTitle className="text-base">Meta Açıklama</CardTitle>
                    <CopyButton text={result.seo.meta_description} id="meta" />
                  </CardHeader>
                  <CardContent>
                    <p className="p-4 bg-white/5 rounded-xl border border-white/10 text-sm leading-relaxed">
                      {result.seo.meta_description}
                    </p>
                  </CardContent>
                </Card>
              </div>

              <div className="grid md:grid-cols-3 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Anahtar Kelime Boşlukları</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {result.seo.keyword_gaps.map((kw, i) => (
                        <Badge key={i} variant="outline" className="text-xs">{kw}</Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">İçerik Önerileri</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2.5 text-sm">
                      {result.seo.content_recommendations.map((rec, i) => (
                        <li key={i} className="flex items-start gap-2.5">
                          <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                          <span className="text-muted-foreground">{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">
                      Platform İpuçları{' '}
                      <Badge variant="outline" className="ml-2 text-[10px]">{result.platform}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2.5 text-sm">
                      {result.seo.platform_tips.map((tip, i) => (
                        <li key={i} className="flex items-start gap-2.5">
                          <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-violet-500 shrink-0" />
                          <span className="text-muted-foreground">{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>

              {result.seo.product_development_ideas && result.seo.product_development_ideas.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Lightbulb className="w-4 h-4 text-amber-500" />
                      Ürün Geliştirme Fırsatları
                    </CardTitle>
                    <CardDescription>Pazarda aranan ancak ürününüzde bulunmayan özellikler</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {result.seo.product_development_ideas.map((idea, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-amber-500/20 bg-amber-500/5">
                          <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                          <p className="text-sm text-muted-foreground">
                            <span className="font-medium text-foreground">Pazarda şu özellik aranıyor ancak ürününüzde yok: </span>
                            {idea}
                          </p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

          </Tabs>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
