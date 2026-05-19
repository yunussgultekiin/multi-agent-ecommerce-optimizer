'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { formatDate } from '@/lib/utils';
import {
  Check,
  Copy,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  Star,
  ArrowLeft,
  Download,
  MessageSquare,
  ImageIcon,
  Loader2,
} from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
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
  premium: 'Premium & Prestij',
};

const PLATFORM_COLORS: Record<string, string> = {
  trendyol: 'text-orange-400 border-orange-400/30 bg-orange-400/10',
  amazon: 'text-amber-400 border-amber-400/30 bg-amber-400/10',
  hepsiburada: 'text-red-400 border-red-400/30 bg-red-400/10',
};

const POSITIONING_LABELS: Record<string, string> = {
  underpriced: 'Piyasanın Altında',
  optimal: 'Optimal',
  overpriced: 'Piyasanın Üstünde',
};

export default function ResultPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
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
          sentiment_result,
          trend_result,
        } = rival_json || {};

        setOriginalImageUrl(user_product?.image_urls?.[0] || null);

        const competitors = (competitor_research_results || []).map((cr: any) => ({
          name: cr.data?.competitor_name || '',
          price: cr.data?.estimated_price ?? 0,
          rating: cr.data?.rating ?? 0,
          review_count: cr.data?.review_count ?? 0,
          brand: cr.data?.brand || '',
          source_url: '',
        }));

        const market_gap = {
          clusters:                      gap_result?.clusters || [],
          gap_opportunities:             gap_result?.gap_opportunities || [],
          strategic_actions:             gap_result?.strategic_actions || [],
          positioning_rationale:         gap_result?.positioning_rationale || '',
          user_product_cluster:          gap_result?.user_product_cluster || '',
          sentiment_based_opportunities: gap_result?.sentiment_based_opportunities || [],
          trend_based_opportunities:     gap_result?.trend_based_opportunities || [],
          brand_landscape:               gap_result?.brand_landscape || {
            premium_brands: [],
            budget_brands: [],
            user_brand_position: '',
          },
          positioning_score:             gap_result?.positioning_score ?? 0,
          variant_gap_opportunities:     gap_result?.variant_gap_opportunities || [],
        };

        const pricing = {
          current_position: pricing_result?.positioning || 'optimal',
          suggested_min: pricing_result?.price_range_min || 0,
          suggested_max: pricing_result?.price_range_max || 0,
          optimal_price: pricing_result?.predicted_price || 0,
          confidence_score: pricing_result?.confidence_score || 0,
          fallback_used: pricing_result?.fallback_used ?? false,
          price_median:     pricing_result?.price_median ?? 0,
          price_q1:         pricing_result?.price_q1 ?? 0,
          price_q3:         pricing_result?.price_q3 ?? 0,
          market_power_gap: pricing_result?.market_power_gap || '',
          variant_pricing: (pricing_result?.variant_pricing || []).map((vp: any) => ({
            variant_name:   vp.variant_name || '',
            suggested_price: vp.suggested_price ?? 0,
            positioning:    vp.positioning || '',
            base_price:     vp.base_price ?? 0,
            price_delta:    vp.price_delta ?? 0,
          })),
          competitor_prices: (competitor_research_results || [])
            .filter((cr: any) => cr.data?.estimated_price != null)
            .map((cr: any) => ({
              name: cr.data?.competitor_name || '',
              price: cr.data?.estimated_price || 0,
            })),
        };

        const seo = {
          title_suggestion: seo_output?.title_suggestion || '',
          meta_description: seo_output?.meta_description || '',
          keyword_gaps: seo_output?.keyword_gaps || [],
          content_recommendations: seo_output?.content_recommendations || [],
          platform_tips: seo_output?.platform_specific_tips || [],
          variant_seo: (seo_output?.variant_seo || []).map((vs: any) => ({
            variant_name: vs.variant_name || '',
            title_suggestion: vs.title_suggestion || '',
            keyword_additions: vs.keyword_additions || [],
          })),
          product_development_ideas: seo_output?.product_development_ideas || [],
          competitor_comparison_summary: seo_output?.competitor_comparison_summary || '',
        };

        const sentiment = {
          pain_points: sentiment_result?.pain_points || [],
          praised_features: sentiment_result?.praised_features || [],
          marketing_angles: sentiment_result?.marketing_angles || [],
          risk_warnings: sentiment_result?.risk_warnings || [],
        };

        const trend = {
          category_trend_summary: trend_result?.category_trend_summary || '',
          demand_signals: trend_result?.demand_signals || [],
          platform_trends: trend_result?.platform_trends || [],
          trending_features: trend_result?.trending_features || [],
        };

        setResult({
          task_id,
          product_title: user_product?.title || '',
          product_brand: user_product?.brand || '',
          product_category: user_product?.category || '',
          product_description: user_product?.description || '',
          product_price: user_product?.price ?? 0,
          platform: target_platform || 'trendyol',
          analyzed_at: created_at,
          status: 'completed',
          seo_tone: task?.seo_tone ?? undefined,
          competitors,
          market_gap,
          pricing,
          seo,
          sentiment,
          trend,
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
        <Skeleton className="h-72 w-full rounded-2xl" />
        <Skeleton className="h-12 w-full rounded-xl" />
        <Skeleton className="h-[440px] w-full rounded-2xl" />
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

  const maxCompPrice = Math.max(...result.pricing.competitor_prices.map((p) => p.price), 1);
  const titleLen = result.seo.title_suggestion.length;
  const titleCounterColor =
    titleLen < 60 ? 'text-emerald-400' : titleLen <= 75 ? 'text-amber-400' : 'text-red-400';

  return (
    <AnimatePresence>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="space-y-8"
      >
        {/* Back button */}
        <motion.div variants={itemVariants}>
          <Link href="/dashboard/history">
            <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-foreground -ml-2">
              <ArrowLeft className="w-4 h-4" />
              Analizlere Dön
            </Button>
          </Link>
        </motion.div>

        {/* ── Analiz Özeti ── */}
        <motion.div variants={itemVariants}>
          <div className="glass-card rounded-2xl overflow-hidden relative border border-white/[0.08]">
            <div className="absolute top-0 right-0 w-80 h-80 bg-primary/8 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-60 h-60 bg-violet-500/8 rounded-full blur-[100px] pointer-events-none" />

            <div className="p-6 md:p-8 relative">
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold mb-5">
                Analiz Özeti
              </p>

              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-5 mb-6">
                <div className="space-y-2.5 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant="outline"
                      className={`capitalize px-3 py-1 text-xs font-medium ${PLATFORM_COLORS[result.platform] ?? ''}`}
                    >
                      {result.platform}
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
                    {result.product_title || 'Ürün başlığı bulunamadı'}
                  </h1>
                </div>

                <div className="shrink-0 self-start">
                  {result.generated_image_url ? (
                    <a href={result.generated_image_url} download target="_blank" rel="noreferrer">
                      <Button variant="outline" size="sm" className="gap-2">
                        <Download className="w-4 h-4" />
                        Görseli İndir
                      </Button>
                    </a>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 opacity-50 cursor-default pointer-events-none"
                      tabIndex={-1}
                    >
                      <Download className="w-4 h-4" />
                      Görseli İndir
                    </Button>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">Marka</p>
                  <p className="text-sm font-semibold truncate" title={result.product_brand}>
                    {result.product_brand || '—'}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">Hedef Platform</p>
                  <p className={`text-sm font-semibold capitalize ${(PLATFORM_COLORS[result.platform] ?? '').split(' ')[0]}`}>
                    {result.platform || '—'}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">Mevcut Fiyat</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {result.product_price && result.product_price > 0
                      ? `₺${result.product_price.toFixed(2)}`
                      : '—'}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-primary/[0.06] border border-primary/20 relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-b from-primary/8 to-transparent pointer-events-none" />
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5 relative">
                    Önerilen Fiyat
                  </p>
                  <p className="text-sm font-bold text-primary tabular-nums relative">
                    {result.pricing.optimal_price > 0
                      ? `₺${result.pricing.optimal_price.toFixed(2)}`
                      : '—'}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06] col-span-2">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">Kategori</p>
                  <p className="text-sm font-semibold truncate" title={result.product_category}>
                    {result.product_category || '—'}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">Fiyat Pozisyonu</p>
                  <p className="text-sm font-semibold">
                    {POSITIONING_LABELS[result.pricing.current_position] ?? '—'}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">SEO Tonu</p>
                  <p className="text-sm font-semibold text-violet-400">
                    {result.seo_tone ? SEO_TONE_LABELS[result.seo_tone] : '—'}
                  </p>
                </div>
              </div>

              {result.seo.keyword_gaps.length > 0 && (
                <div className="mt-4 pt-4 border-t border-white/[0.05]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2.5">
                    Anahtar Kelime Fırsatları
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {result.seo.keyword_gaps.slice(0, 3).map((kw, i) => (
                      <Badge
                        key={i}
                        variant="outline"
                        className="text-xs border-violet-500/20 bg-violet-500/[0.06] text-violet-300"
                      >
                        {kw}
                      </Badge>
                    ))}
                    {result.seo.keyword_gaps.length > 3 && (
                      <span className="text-xs text-muted-foreground/50">
                        +{result.seo.keyword_gaps.length - 3} daha
                      </span>
                    )}
                  </div>
                </div>
              )}

              {result.market_gap.gap_opportunities[0] && (
                <div className="mt-3 p-3.5 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20">
                  <div className="flex items-start gap-2.5">
                    <Lightbulb className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      <span className="font-semibold text-emerald-400">Öne Çıkan Fırsat: </span>
                      {result.market_gap.gap_opportunities[0]}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* ── SEO Optimizasyonu ── */}
        <motion.div variants={itemVariants} className="space-y-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight">SEO Optimizasyonu</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Platform için optimize edilmiş içerik ve görsel öneriler
            </p>
          </div>

          <div className="space-y-4">
            {/* SEO Başlık Önerisi */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-base">SEO Başlık Önerisi</CardTitle>
                  {result.seo.title_suggestion && (
                    <p className={`text-xs mt-1 font-medium ${titleCounterColor}`}>
                      {titleLen} karakter
                    </p>
                  )}
                </div>
                <CopyButton text={result.seo.title_suggestion} id="title" />
              </CardHeader>
              <CardContent>
                <p className="p-4 bg-white/5 rounded-xl border border-white/10 text-lg font-medium leading-relaxed">
                  {result.seo.title_suggestion || 'Başlık önerisi bulunamadı.'}
                </p>
              </CardContent>
            </Card>

            {/* Meta Açıklama */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-base">Meta Açıklama</CardTitle>
                  {result.seo_tone && (
                    <Badge variant="outline" className="mt-1.5 text-violet-400 border-violet-400/30 bg-violet-400/10">
                      {SEO_TONE_LABELS[result.seo_tone]}
                    </Badge>
                  )}
                </div>
                <CopyButton text={result.seo.meta_description} id="meta" />
              </CardHeader>
              <CardContent>
                <p className="p-4 bg-white/5 rounded-xl border border-white/10 text-sm leading-relaxed">
                  {result.seo.meta_description || 'Meta açıklama bulunamadı.'}
                </p>
              </CardContent>
            </Card>

            {/* SEO Anahtar Kelimeleri */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">SEO Anahtar Kelimeleri</CardTitle>
              </CardHeader>
              <CardContent>
                {result.seo.keyword_gaps.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {result.seo.keyword_gaps.map((kw, i) => (
                      <Badge
                        key={i}
                        variant="outline"
                        className="text-xs border-violet-500/20 bg-violet-500/[0.06] text-violet-300"
                      >
                        {kw}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Anahtar kelime fırsatı bulunamadı.</p>
                )}
              </CardContent>
            </Card>

            {/* Collapsible SEO cards */}
            <Accordion type="multiple" className="space-y-3">
              <AccordionItem value="content-recs" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                <AccordionTrigger className="px-6 py-4 text-sm font-semibold hover:no-underline">
                  İçerik Önerileri
                </AccordionTrigger>
                <AccordionContent className="px-6 pb-5">
                  {result.seo.content_recommendations.length > 0 ? (
                    <ul className="space-y-2.5 text-sm">
                      {result.seo.content_recommendations.map((rec, i) => (
                        <li key={i} className="flex items-start gap-2.5">
                          <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                          <span className="text-muted-foreground">{rec}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">İçerik önerisi bulunamadı.</p>
                  )}
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="platform-tips" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                <AccordionTrigger className="px-6 py-4 text-sm font-semibold hover:no-underline">
                  <span className="flex items-center gap-2">
                    Platform İpuçları
                    <Badge variant="outline" className={`text-[10px] capitalize ${PLATFORM_COLORS[result.platform] ?? ''}`}>
                      {result.platform}
                    </Badge>
                  </span>
                </AccordionTrigger>
                <AccordionContent className="px-6 pb-5">
                  {result.seo.platform_tips.length > 0 ? (
                    <ul className="space-y-2.5 text-sm">
                      {result.seo.platform_tips.map((tip, i) => (
                        <li key={i} className="flex items-start gap-2.5">
                          <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-violet-500 shrink-0" />
                          <span className="text-muted-foreground">{tip}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">Platform ipucu bulunamadı.</p>
                  )}
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="product-dev" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                <AccordionTrigger className="px-6 py-4 text-sm font-semibold hover:no-underline">
                  <span className="flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-500" />
                    Ürün Geliştirme Önerileri
                  </span>
                </AccordionTrigger>
                <AccordionContent className="px-6 pb-5">
                  {result.seo.product_development_ideas && result.seo.product_development_ideas.length > 0 ? (
                    <div className="space-y-3">
                      {result.seo.product_development_ideas.map((idea, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.07 }}
                          className="flex items-start gap-3 p-4 rounded-xl border border-amber-500/20 bg-amber-500/[0.04] hover:bg-amber-500/[0.08] transition-colors"
                        >
                          <div className="w-6 h-6 rounded-full bg-amber-500/15 border border-amber-500/30 flex items-center justify-center shrink-0 mt-0.5">
                            <span className="text-amber-400 text-[10px] font-bold">{i + 1}</span>
                          </div>
                          <p className="text-sm text-muted-foreground leading-relaxed">{idea}</p>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Stratejik gelişim önerisi bulunamadı.</p>
                  )}
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            {/* Görsel Optimizasyonu */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Görsel Optimizasyonu</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col sm:flex-row gap-6">
                  <div className="flex-1 space-y-3">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Mevcut Görsel
                    </p>
                    {originalImageUrl ? (
                      <div className="rounded-xl overflow-hidden border border-white/[0.08] bg-white/[0.02] flex items-center justify-center min-h-[200px]">
                        <img
                          src={originalImageUrl}
                          alt="Mevcut ürün görseli"
                          className="object-contain max-h-[300px] w-full"
                        />
                      </div>
                    ) : (
                      <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] flex flex-col items-center justify-center gap-3 text-muted-foreground min-h-[200px]">
                        <ImageIcon className="w-8 h-8 opacity-30" />
                        <p className="text-sm">Görsel bulunamadı</p>
                      </div>
                    )}
                  </div>

                  <div className="flex-1 space-y-3">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Optimize Edilmiş Görsel
                    </p>
                    {result.generated_image_url ? (
                      <div className="space-y-3">
                        <div className="rounded-xl overflow-hidden border border-white/[0.08] bg-white/[0.02] flex items-center justify-center min-h-[200px]">
                          <img
                            src={result.generated_image_url}
                            alt="Optimize edilmiş ürün görseli"
                            className="object-contain max-h-[300px] w-full"
                          />
                        </div>
                        <a href={result.generated_image_url} download target="_blank" rel="noreferrer" className="block">
                          <Button variant="outline" size="sm" className="w-full gap-2">
                            <Download className="w-4 h-4" />
                            Görseli İndir
                          </Button>
                        </a>
                      </div>
                    ) : (
                      <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] flex flex-col items-center justify-center gap-3 text-muted-foreground min-h-[200px]">
                        <Loader2 className="w-8 h-8 opacity-30 animate-spin" />
                        <p className="text-sm">Görsel oluşturuluyor...</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </motion.div>

        {/* ── Pazar Araştırması ── */}
        <motion.div variants={itemVariants} className="space-y-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight">Pazar Araştırması</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Rakip analizi, fiyatlandırma ve pazar boşluğu çıktıları
            </p>
          </div>

          <div className="space-y-6">
            {/* Rakipler */}
            <Card>
              <CardHeader>
                <CardTitle>Bulunan Rakipler</CardTitle>
                <CardDescription>
                  Pazardaki ana rakiplerinizin güncel durumu ({result.competitors.length} rakip)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {result.competitors.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="text-xs text-muted-foreground uppercase bg-white/[0.03]">
                        <tr>
                          <th className="px-6 py-4 rounded-tl-lg">Rakip / Ürün Adı</th>
                          <th className="px-6 py-4">Marka</th>
                          <th className="px-6 py-4">Tahmini Fiyat</th>
                          <th className="px-6 py-4">Puan</th>
                          <th className="px-6 py-4 rounded-tr-lg">Yorum Sayısı</th>
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
                              {comp.name || '—'}
                            </td>
                            <td className="px-6 py-4 text-muted-foreground">{comp.brand || '—'}</td>
                            <td className="px-6 py-4 font-semibold tabular-nums">
                              {comp.price > 0 ? `₺${comp.price.toFixed(2)}` : '—'}
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-1.5">
                                <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                                <span className="font-medium">{comp.rating > 0 ? comp.rating : '—'}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-muted-foreground">
                              {comp.review_count > 0 ? comp.review_count.toLocaleString('tr-TR') : '—'}
                            </td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-4">Rakip verisi bulunamadı.</p>
                )}
              </CardContent>
            </Card>

            {/* Fiyat Analizi */}
            <div className="space-y-4">
              {result.pricing.fallback_used && (
                <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl border border-amber-500/25 bg-amber-500/[0.06] text-sm text-amber-400">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  Fiyat verisi tahminlere dayanıyor
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2">Mevcut Fiyat</p>
                  <p className="text-lg font-bold tabular-nums">
                    {result.product_price && result.product_price > 0
                      ? `₺${result.product_price.toFixed(2)}`
                      : '—'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-primary/[0.07] border border-primary/25 relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-b from-primary/10 to-transparent pointer-events-none" />
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2 relative">Önerilen Fiyat</p>
                  <p className="text-lg font-bold text-primary tabular-nums relative">
                    {result.pricing.optimal_price > 0 ? `₺${result.pricing.optimal_price.toFixed(2)}` : '—'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2">Fiyat Aralığı</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {result.pricing.suggested_min > 0 || result.pricing.suggested_max > 0
                      ? `₺${result.pricing.suggested_min > 0 ? result.pricing.suggested_min.toFixed(2) : '—'} – ₺${result.pricing.suggested_max > 0 ? result.pricing.suggested_max.toFixed(2) : '—'}`
                      : '—'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2">Pazar Konumu</p>
                  <p className="text-sm font-semibold">
                    {POSITIONING_LABELS[result.pricing.current_position] ?? '—'}
                  </p>
                  {result.market_gap.user_product_cluster && (
                    <Badge variant="outline" className="mt-1.5 text-[10px] text-muted-foreground capitalize">
                      Segment: {result.market_gap.user_product_cluster}
                    </Badge>
                  )}
                </div>
              </div>

              {/* Price stats Q1 / Median / Q3 */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] text-center">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1">Medyan Fiyat</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {result.pricing.price_median > 0 ? `₺${result.pricing.price_median.toFixed(2)}` : '—'}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] text-center">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1">Alt Çeyrek (Q1)</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {result.pricing.price_q1 > 0 ? `₺${result.pricing.price_q1.toFixed(2)}` : '—'}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] text-center">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1">Üst Çeyrek (Q3)</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {result.pricing.price_q3 > 0 ? `₺${result.pricing.price_q3.toFixed(2)}` : '—'}
                  </p>
                </div>
              </div>

              {/* Competitor price bar chart */}
              <Card>
                <CardHeader>
                  <CardTitle>Rakip Fiyat Dağılımı</CardTitle>
                  <CardDescription>Pazardaki diğer ürünlerle fiyat karşılaştırmanız</CardDescription>
                </CardHeader>
                <CardContent>
                  {result.pricing.competitor_prices.length > 0 ? (
                    <div className="space-y-3">
                      {result.pricing.competitor_prices
                        .slice()
                        .sort((a, b) => a.price - b.price)
                        .map((p, i) => (
                          <div key={i} className="space-y-1.5">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-muted-foreground truncate max-w-[60%]" title={p.name}>
                                {p.name || '—'}
                              </span>
                              <span className="font-semibold tabular-nums shrink-0">
                                {p.price > 0 ? `₺${p.price.toFixed(2)}` : '—'}
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.round((p.price / maxCompPrice) * 100)}%` }}
                                transition={{ duration: 0.6, delay: i * 0.06 }}
                                className="h-full rounded-full bg-primary/60"
                              />
                            </div>
                          </div>
                        ))}
                      {result.pricing.market_power_gap && (
                        <p className="text-xs text-muted-foreground pt-1">{result.pricing.market_power_gap}</p>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground py-2">Rakip fiyat verisi bulunamadı.</p>
                  )}
                </CardContent>
              </Card>

              {result.pricing.variant_pricing.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Varyant Fiyatlandırması</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left">
                        <thead className="text-xs text-muted-foreground uppercase bg-white/[0.03]">
                          <tr>
                            <th className="px-4 py-3 rounded-tl-lg">Varyant</th>
                            <th className="px-4 py-3">Önerilen Fiyat</th>
                            <th className="px-4 py-3 rounded-tr-lg">Konum</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {result.pricing.variant_pricing.map((vp, i) => (
                            <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                              <td className="px-4 py-3 font-medium">{vp.variant_name || '—'}</td>
                              <td className="px-4 py-3 font-semibold text-primary tabular-nums">
                                {vp.suggested_price > 0 ? `₺${vp.suggested_price.toFixed(2)}` : '—'}
                              </td>
                              <td className="px-4 py-3 text-muted-foreground">
                                {(POSITIONING_LABELS[vp.positioning] ?? vp.positioning) || '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Pazar Boşluğu */}
            <Card>
              <CardHeader>
                <CardTitle>Pazar Boşluğu</CardTitle>
                <CardDescription>Rakiplerin odaklanmadığı fırsat alanları</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {result.market_gap.gap_opportunities[0] && (
                  <div className="p-4 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20">
                    <div className="flex items-start gap-2.5">
                      <Lightbulb className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <p className="text-sm leading-relaxed">
                        <span className="font-semibold text-emerald-400">Öne Çıkan Fırsat: </span>
                        {result.market_gap.gap_opportunities[0]}
                      </p>
                    </div>
                  </div>
                )}

                {result.market_gap.gap_opportunities.length > 0 && (
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
                )}

                {(result.market_gap.brand_landscape.premium_brands.length > 0 ||
                  result.market_gap.brand_landscape.budget_brands.length > 0 ||
                  result.market_gap.brand_landscape.user_brand_position) && (
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                    <h4 className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">
                      Marka Konumu
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">
                          Premium Markalar
                        </p>
                        {result.market_gap.brand_landscape.premium_brands.length > 0 ? (
                          <ul className="space-y-1">
                            {result.market_gap.brand_landscape.premium_brands.map((b, i) => (
                              <li key={i} className="text-sm text-muted-foreground">{b}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-muted-foreground">—</p>
                        )}
                      </div>
                      <div>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">
                          Bütçe Dostu Markalar
                        </p>
                        {result.market_gap.brand_landscape.budget_brands.length > 0 ? (
                          <ul className="space-y-1">
                            {result.market_gap.brand_landscape.budget_brands.map((b, i) => (
                              <li key={i} className="text-sm text-muted-foreground">{b}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-muted-foreground">—</p>
                        )}
                      </div>
                    </div>
                    {result.market_gap.brand_landscape.user_brand_position && (
                      <p className="text-sm text-muted-foreground">
                        <span className="font-medium text-foreground">Konumunuz: </span>
                        {result.market_gap.brand_landscape.user_brand_position}
                      </p>
                    )}
                  </div>
                )}

                <Accordion type="multiple" className="space-y-2">
                  {result.market_gap.strategic_actions.length > 0 && (
                    <AccordionItem value="strategic" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                      <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                        Stratejik Adımlar
                      </AccordionTrigger>
                      <AccordionContent className="px-5 pb-4">
                        <div className="space-y-2">
                          {result.market_gap.strategic_actions.map((action, i) => (
                            <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-violet-500/15 bg-violet-500/[0.04]">
                              <TrendingUp className="w-4 h-4 text-violet-400 shrink-0 mt-0.5" />
                              <span className="text-sm text-muted-foreground">{action}</span>
                            </div>
                          ))}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  )}

                  {result.market_gap.sentiment_based_opportunities.length > 0 && (
                    <AccordionItem value="sentiment-opp" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                      <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                        Müşteri Kaynaklı Fırsatlar
                      </AccordionTrigger>
                      <AccordionContent className="px-5 pb-4">
                        <ul className="space-y-2">
                          {result.market_gap.sentiment_based_opportunities.map((item, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                              <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </AccordionContent>
                    </AccordionItem>
                  )}

                  {result.market_gap.trend_based_opportunities.length > 0 && (
                    <AccordionItem value="trend-opp" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                      <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                        Trend Kaynaklı Fırsatlar
                      </AccordionTrigger>
                      <AccordionContent className="px-5 pb-4">
                        <ul className="space-y-2">
                          {result.market_gap.trend_based_opportunities.map((item, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                              <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </AccordionContent>
                    </AccordionItem>
                  )}
                </Accordion>

                {!result.market_gap.gap_opportunities.length &&
                  !result.market_gap.strategic_actions.length &&
                  !result.market_gap.sentiment_based_opportunities.length &&
                  !result.market_gap.trend_based_opportunities.length && (
                    <p className="text-sm text-muted-foreground">Pazar boşluğu verisi bulunamadı.</p>
                  )}
              </CardContent>
            </Card>

            {/* Müşteri Sinyalleri */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-blue-400" />
                  Müşteri Sinyalleri
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.sentiment.pain_points.length === 0 &&
                result.sentiment.praised_features.length === 0 &&
                result.sentiment.marketing_angles.length === 0 &&
                result.sentiment.risk_warnings.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Müşteri sinyali verisi bulunamadı.</p>
                ) : (
                  <Accordion type="multiple" className="space-y-2">
                    {result.sentiment.pain_points.length > 0 && (
                      <AccordionItem value="pain" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                        <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                          Şikayet Noktaları
                        </AccordionTrigger>
                        <AccordionContent className="px-5 pb-4">
                          <ul className="space-y-1.5">
                            {result.sentiment.pain_points.map((item, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                                {item}
                              </li>
                            ))}
                          </ul>
                        </AccordionContent>
                      </AccordionItem>
                    )}

                    {result.sentiment.praised_features.length > 0 && (
                      <AccordionItem value="praised" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                        <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                          Övülen Özellikler
                        </AccordionTrigger>
                        <AccordionContent className="px-5 pb-4">
                          <ul className="space-y-1.5">
                            {result.sentiment.praised_features.map((item, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                                {item}
                              </li>
                            ))}
                          </ul>
                        </AccordionContent>
                      </AccordionItem>
                    )}

                    {result.sentiment.marketing_angles.length > 0 && (
                      <AccordionItem value="marketing" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                        <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                          Pazarlama Açıları
                        </AccordionTrigger>
                        <AccordionContent className="px-5 pb-4">
                          <ul className="space-y-1.5">
                            {result.sentiment.marketing_angles.map((item, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                                {item}
                              </li>
                            ))}
                          </ul>
                        </AccordionContent>
                      </AccordionItem>
                    )}

                    {result.sentiment.risk_warnings.length > 0 && (
                      <AccordionItem value="risks" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                        <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                          Risk Uyarıları
                        </AccordionTrigger>
                        <AccordionContent className="px-5 pb-4">
                          <ul className="space-y-1.5">
                            {result.sentiment.risk_warnings.map((item, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                                {item}
                              </li>
                            ))}
                          </ul>
                        </AccordionContent>
                      </AccordionItem>
                    )}
                  </Accordion>
                )}
              </CardContent>
            </Card>

            {/* Trend Analizi */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-emerald-400" />
                  Trend Analizi
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {result.trend.category_trend_summary ? (
                  <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {result.trend.category_trend_summary}
                    </p>
                  </div>
                ) : null}

                {!result.trend.category_trend_summary &&
                  result.trend.trending_features.length === 0 &&
                  result.trend.demand_signals.length === 0 &&
                  result.trend.platform_trends.length === 0 && (
                    <p className="text-sm text-muted-foreground">Trend verisi bulunamadı.</p>
                  )}

                <Accordion type="multiple" className="space-y-2">
                  {result.trend.trending_features.length > 0 && (
                    <AccordionItem value="trending" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                      <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                        Yükselen Özellikler
                      </AccordionTrigger>
                      <AccordionContent className="px-5 pb-4">
                        <ul className="space-y-1.5">
                          {result.trend.trending_features.map((item, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                              <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </AccordionContent>
                    </AccordionItem>
                  )}

                  {result.trend.demand_signals.length > 0 && (
                    <AccordionItem value="demand" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                      <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                        Talep Sinyalleri
                      </AccordionTrigger>
                      <AccordionContent className="px-5 pb-4">
                        <ul className="space-y-1.5">
                          {result.trend.demand_signals.map((item, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                              <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </AccordionContent>
                    </AccordionItem>
                  )}

                  {result.trend.platform_trends.length > 0 && (
                    <AccordionItem value="platform-trends" className="border border-white/[0.08] rounded-xl overflow-hidden bg-card/50">
                      <AccordionTrigger className="px-5 py-3.5 text-sm font-semibold hover:no-underline">
                        Platform Trendleri
                      </AccordionTrigger>
                      <AccordionContent className="px-5 pb-4">
                        <ul className="space-y-1.5">
                          {result.trend.platform_trends.map((item, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                              <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-violet-400 shrink-0" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </AccordionContent>
                    </AccordionItem>
                  )}
                </Accordion>
              </CardContent>
            </Card>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}