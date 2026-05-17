'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { formatDate } from '@/lib/utils';
import {
  Plus,
  ArrowRight,
  BarChart3,
  Activity,
  TrendingUp,
  Zap,
  Sparkles,
  History,
  Clock,
  ImageOff,
  Target,
  DollarSign,
  Search,
  Lightbulb,
  MessageSquare,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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

const DEMO_COMPETITORS = [
  { name: 'Mug Art "Stay Calm" Seramik Kupa', brand: 'Mug Art', price: 139.90, rating: 4.6, reviews: 312 },
  { name: 'Siyah Slogan Baskılı Seramik Kupa', brand: 'HomeStyle', price: 119.90, rating: 4.3, reviews: 187 },
  { name: 'Renkli Keep Calm Kupa 330ml', brand: 'CeramicPlus', price: 164.90, rating: 4.7, reviews: 524 },
  { name: 'Ofis Kupası Slogan Baskılı', brand: 'DekoPark', price: 129.90, rating: 4.1, reviews: 98 },
];

const DEMO_GAP_OPPORTUNITIES = [
  'Kişiselleştirilebilir baskı seçeneği sunan rakip yok — özel isim/mesaj fırsatı',
  'Hediye paketi ile sunulan kupa segmentinde boşluk tespit edildi',
  'Organik/BPA-free sertifikalı ürün talep edilmesine rağmen karşılanmıyor',
];

const DEMO_STRATEGIC_ACTIONS = [
  'Hediye paketi seçeneği ekleyerek ortalama sipariş değerini artır',
  'Ürün başlığına "330ml" ve "bulaşık makinesinde yıkanabilir" gibi teknik detaylar ekle',
  'Trendyol mağaza bannerında öne çıkar, sponsorlu ürün kampanyası değerlendir',
];

const DEMO_SEO_TITLE = 'Keep Calm Seramik Kupa 330ml | Kırmızı Slogan Baskılı | Hediye Ambalaj Seçeneği';

const DEMO_META = 'Keep Calm baskılı kırmızı seramik kupa. 330ml kapasiteli, bulaşık makinesinde yıkanabilir, ofis ve ev kullanımına uygun. Hediye ambalaj seçeneğiyle sipariş verin.';

const DEMO_KEYWORD_GAPS = ['seramik kupa hediye', 'slogan baskılı kupa', 'kırmızı ofis kupası', 'kupa 330ml', 'özel baskılı kupa'];

const DEMO_PLATFORM_TIPS = [
  'Trendyol\'da ilk görseli beyaz arka planla yükle, detay görseline ürün ölçülerini ekle',
  'Kargo süresini 1-2 iş günü olarak belirt — bu segment için dönüşüm etkisi yüksek',
  'Soru-Cevap bölümüne ön cevap yaz: "Bulaşık makinesinde yıkanabilir mi?" sorusunu yanıtla',
];

const DEMO_PRODUCT_DEV_IDEAS = [
  'İsme özel baskı seçeneği ekle — kupa segmentinde en çok aranan kişiselleştirme özelliği',
  'İkili set (2\'li kupa) paketi oluştur, çift hediye için talep var',
  'Farklı renk varyantı (siyah, beyaz, lacivert) ekle; kırmızı dışındaki renkler rakiplerde yok',
  'Ürüne özel kutu ambalaj + tatlı tarifi kartı eklenerek hediye seti olarak sunulabilir',
];

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

  const titleLen = DEMO_SEO_TITLE.length;
  const titleCounterColor = titleLen < 60 ? 'text-emerald-400' : titleLen <= 75 ? 'text-amber-400' : 'text-red-400';
  const maxDemoPrice = Math.max(...DEMO_COMPETITORS.map((c) => c.price));

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

      <motion.div variants={row} className="space-y-4">
        <div className="flex items-center gap-3">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium mb-0.5">Örnek</p>
            <h2 className="text-base font-semibold tracking-tight">Demo Analiz Çıktısı</h2>
          </div>
          <Badge variant="outline" className="text-[10px] border-amber-500/25 bg-amber-500/[0.06] text-amber-400 ml-1">
            Örnek analiz taslağı
          </Badge>
        </div>

        <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] overflow-hidden">
          <div className="flex flex-col sm:flex-row gap-5 p-5 border-b border-white/[0.06]">
            <div className="shrink-0 w-20 h-20 sm:w-24 sm:h-24 rounded-xl overflow-hidden border border-white/[0.09] bg-white/[0.04]">
              <Image
                src="/demo-kupa.jpg"
                alt="Keep Calm Seramik Kupa"
                width={96}
                height={96}
                className="w-full h-full object-cover"
              />
            </div>

            <div className="flex-1 min-w-0 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="text-[10px] text-orange-400 border-orange-400/30 bg-orange-400/10">
                  trendyol
                </Badge>
                <Badge variant="outline" className="text-[10px] text-violet-400 border-violet-400/30 bg-violet-400/10">
                  Profesyonel
                </Badge>
              </div>
              <p className="font-semibold text-sm leading-snug">
                Kırmızı Keep Calm Baskılı Seramik Kupa
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                Kırmızı dış yüzeye ve beyaz iç hacme sahip, "Keep Calm and Carry On" baskılı seramik kupa.
              </p>
              <div className="flex flex-wrap gap-3 pt-0.5">
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Marka</p>
                  <p className="text-xs font-semibold">Keep Calm</p>
                </div>
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Fiyat</p>
                  <p className="text-xs font-semibold tabular-nums">₺149,90</p>
                </div>
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Kategori</p>
                  <p className="text-xs font-semibold">Kupa / Bardak</p>
                </div>
              </div>
            </div>
          </div>

          <div className="p-5">
            <Tabs defaultValue="competitors" className="w-full">
              <TabsList className="w-full justify-start overflow-x-auto bg-white/[0.02] border border-white/[0.05] p-1">
                <TabsTrigger value="competitors" className="gap-1.5 text-xs">
                  <Target className="w-3.5 h-3.5" /> Rakipler
                </TabsTrigger>
                <TabsTrigger value="market" className="gap-1.5 text-xs">
                  <TrendingUp className="w-3.5 h-3.5" /> Pazar Boşluğu
                </TabsTrigger>
                <TabsTrigger value="pricing" className="gap-1.5 text-xs">
                  <DollarSign className="w-3.5 h-3.5" /> Fiyat
                </TabsTrigger>
                <TabsTrigger value="seo" className="gap-1.5 text-xs">
                  <Search className="w-3.5 h-3.5" /> SEO Detay
                </TabsTrigger>
                <TabsTrigger value="product-dev" className="gap-1.5 text-xs">
                  <Lightbulb className="w-3.5 h-3.5" /> Ürün Geliştirme
                </TabsTrigger>
              </TabsList>

              <TabsContent value="competitors" className="mt-5">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-3">
                  Tespit Edilen Rakipler ({DEMO_COMPETITORS.length})
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-[10px] text-muted-foreground uppercase bg-white/[0.03]">
                      <tr>
                        <th className="px-4 py-3 rounded-tl-lg">Rakip / Ürün Adı</th>
                        <th className="px-4 py-3">Marka</th>
                        <th className="px-4 py-3">Tahmini Fiyat</th>
                        <th className="px-4 py-3">Puan</th>
                        <th className="px-4 py-3 rounded-tr-lg">Yorum</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {DEMO_COMPETITORS.map((comp, i) => (
                        <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                          <td className="px-4 py-3 font-medium text-xs max-w-[180px] truncate" title={comp.name}>
                            {comp.name}
                          </td>
                          <td className="px-4 py-3 text-xs text-muted-foreground">{comp.brand}</td>
                          <td className="px-4 py-3 text-xs font-semibold tabular-nums">₺{comp.price.toFixed(2)}</td>
                          <td className="px-4 py-3 text-xs font-medium">{comp.rating}</td>
                          <td className="px-4 py-3 text-xs text-muted-foreground">{comp.reviews}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </TabsContent>

              <TabsContent value="market" className="mt-5 space-y-5">
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-3">Fırsat Alanları</p>
                  <div className="space-y-2">
                    {DEMO_GAP_OPPORTUNITIES.map((gap, i) => (
                      <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg border border-white/[0.05] bg-white/[0.02]">
                        <Activity className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span className="text-xs text-muted-foreground">{gap}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-3">Stratejik Adımlar</p>
                  <div className="space-y-2">
                    {DEMO_STRATEGIC_ACTIONS.map((action, i) => (
                      <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg border border-violet-500/15 bg-violet-500/[0.04]">
                        <TrendingUp className="w-4 h-4 text-violet-400 shrink-0 mt-0.5" />
                        <span className="text-xs text-muted-foreground">{action}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02]">
                  <div className="flex items-center gap-2 mb-3">
                    <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Müşteri Sinyalleri</p>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <div>
                      <p className="text-[10px] text-red-400 font-semibold mb-1.5">Şikayetler</p>
                      <ul className="space-y-1 text-xs text-muted-foreground">
                        <li className="flex gap-1.5"><span className="text-red-400 mt-0.5">·</span>Kulp ince ve kaygan hissettiriyor</li>
                        <li className="flex gap-1.5"><span className="text-red-400 mt-0.5">·</span>Baskı solması şikayeti mevcut</li>
                      </ul>
                    </div>
                    <div>
                      <p className="text-[10px] text-emerald-400 font-semibold mb-1.5">Övgüler</p>
                      <ul className="space-y-1 text-xs text-muted-foreground">
                        <li className="flex gap-1.5"><span className="text-emerald-400 mt-0.5">·</span>Tasarım beğenisi yüksek</li>
                        <li className="flex gap-1.5"><span className="text-emerald-400 mt-0.5">·</span>Hediye için tercih ediliyor</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="pricing" className="mt-5 space-y-5">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">Mevcut Fiyat</p>
                    <p className="text-base font-bold tabular-nums">₺149,90</p>
                  </div>
                  <div className="p-3.5 rounded-xl bg-primary/[0.07] border border-primary/25 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-b from-primary/10 to-transparent pointer-events-none" />
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5 relative">Önerilen Fiyat</p>
                    <p className="text-base font-bold text-primary tabular-nums relative">₺154,90</p>
                  </div>
                  <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06] col-span-2 sm:col-span-1">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">Pazar Konumu</p>
                    <p className="text-sm font-semibold">Optimal</p>
                  </div>
                </div>

                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-3">Rakip Fiyat Dağılımı</p>
                  <div className="space-y-2.5">
                    {[...DEMO_COMPETITORS].sort((a, b) => a.price - b.price).map((comp, i) => (
                      <div key={i} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground truncate max-w-[55%]">{comp.name}</span>
                          <span className="font-semibold tabular-nums">₺{comp.price.toFixed(2)}</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary/50 transition-all duration-700"
                            style={{ width: `${Math.round((comp.price / maxDemoPrice) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="seo" className="mt-5 space-y-5">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>SEO Tonu:</span>
                  <Badge variant="outline" className="text-[10px] text-violet-400 border-violet-400/30 bg-violet-400/10">
                    Profesyonel
                  </Badge>
                </div>

                <div className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02]">
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">SEO Başlık Önerisi</p>
                    <p className={`text-[10px] font-medium ${titleCounterColor}`}>{titleLen} karakter</p>
                  </div>
                  <p className="text-sm font-medium leading-relaxed">{DEMO_SEO_TITLE}</p>
                </div>

                <div className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02]">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">Meta Açıklama</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{DEMO_META}</p>
                </div>

                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2">Anahtar Kelime Boşlukları</p>
                  <div className="flex flex-wrap gap-1.5">
                    {DEMO_KEYWORD_GAPS.map((kw, i) => (
                      <Badge key={i} variant="outline" className="text-[10px] border-violet-500/20 bg-violet-500/[0.05] text-violet-300">
                        {kw}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-2">Platform İpuçları</p>
                  <ul className="space-y-2">
                    {DEMO_PLATFORM_TIPS.map((tip, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                        <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-violet-500 shrink-0" />
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              </TabsContent>

              <TabsContent value="product-dev" className="mt-5">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-3">Geliştirme Fırsatları</p>
                <div className="space-y-2.5">
                  {DEMO_PRODUCT_DEV_IDEAS.map((idea, i) => (
                    <div key={i} className="flex items-start gap-3 p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/[0.04]">
                      <div className="w-5 h-5 rounded-full bg-amber-500/15 border border-amber-500/30 flex items-center justify-center shrink-0 mt-0.5">
                        <span className="text-amber-400 text-[9px] font-bold">{i + 1}</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{idea}</p>
                    </div>
                  ))}
                </div>
              </TabsContent>

            </Tabs>
          </div>
        </div>
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
