'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  BarChart3,
  LineChart,
  Search,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Zap,
  Shield,
  Star,
  TrendingUp,
  Check,
  Package,
} from 'lucide-react';

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.55 } },
};

const stagger = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const cardIn = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45 } },
};

const features = [
  {
    title: 'Rakip Analizi',
    description: 'Pazardaki rakiplerinizi ve fiyatlarını gerçek zamanlı keşfedin.',
    icon: Search,
    gradient: 'from-blue-500 to-cyan-500',
    glow: 'group-hover:bg-blue-500/10',
    border: 'group-hover:border-blue-500/20',
  },
  {
    title: 'SEO Optimizasyonu',
    description: 'Platform algoritmasına uygun yüksek dönüşümlü başlıklar üretin.',
    icon: LineChart,
    gradient: 'from-emerald-500 to-teal-500',
    glow: 'group-hover:bg-emerald-500/10',
    border: 'group-hover:border-emerald-500/20',
  },
  {
    title: 'Görsel Üretimi',
    description: 'Ürün görsellerinizi analiz edin, optimize görseller oluşturun.',
    icon: Sparkles,
    gradient: 'from-violet-500 to-purple-500',
    glow: 'group-hover:bg-violet-500/10',
    border: 'group-hover:border-violet-500/20',
  },
  {
    title: 'Fiyat Stratejisi',
    description: 'Akıllı fiyatlandırma önerileriyle kâr marjınızı artırın.',
    icon: BarChart3,
    gradient: 'from-amber-500 to-orange-500',
    glow: 'group-hover:bg-amber-500/10',
    border: 'group-hover:border-amber-500/20',
  },
];

const mockRivals = [
  { name: 'Mug Art "Stay Calm" Seramik Kupa', price: '₺139,90', rating: 4.6, brand: 'Mug Art' },
  { name: 'Siyah Slogan Baskılı Seramik Kupa', price: '₺119,90', rating: 4.3, brand: 'HomeStyle' },
  { name: 'Renkli Keep Calm Kupa 330ml', price: '₺164,90', rating: 4.7, brand: 'CeramicPlus' },
];

const plans = [
  {
    name: 'Başlangıç',
    badge: 'Beta Erişim',
    badgeClass: 'text-emerald-400 border-emerald-400/30 bg-emerald-400/10',
    price: 'Ücretsiz',
    sub: 'Beta süresince',
    features: ['5 analiz / gün', 'Görsel üretimi', 'Geçmiş analizler', 'SEO önerileri', 'Rakip keşfi'],
    cta: 'Hemen Başla',
    href: '/register',
    highlight: true,
  },
  {
    name: 'Orta',
    badge: 'Yakında',
    badgeClass: 'text-blue-400 border-blue-400/30 bg-blue-400/10',
    price: 'Yakında',
    sub: '',
    features: ['20 analiz / gün', 'Gelişmiş raporlar', 'Öncelikli destek', 'Tüm platformlar', 'Dışa aktarma'],
    cta: 'Listeye Katıl',
    href: '/register',
    highlight: false,
  },
  {
    name: 'Yüksek',
    badge: 'Yakında',
    badgeClass: 'text-violet-400 border-violet-400/30 bg-violet-400/10',
    price: 'Yakında',
    sub: '',
    features: ['Sınırsız analiz', 'API erişimi', 'Özel entegrasyon', 'Takım hesabı', 'SLA desteği'],
    cta: 'Listeye Katıl',
    href: '/register',
    highlight: false,
  },
];

const highlights = [
  'Otomatik rakip keşfi',
  'Platforma özel SEO',
  'Görsel üretim & analiz',
  'Fiyat optimizasyonu',
  'AI Destekli SEO & İçerik Analizi',
];

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">

      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute -top-40 -left-40 w-[700px] h-[700px] rounded-full bg-indigo-600/10 blur-[160px]" />
        <div className="absolute top-1/2 right-0 w-[500px] h-[500px] rounded-full bg-violet-600/8 blur-[140px]" />
        <div className="absolute -bottom-40 left-1/3 w-[600px] h-[600px] rounded-full bg-purple-600/8 blur-[140px]" />
        <div className="absolute inset-0 bg-grid pointer-events-none" />
      </div>

      <nav className="relative z-50 border-b border-white/[0.06] bg-background/70 backdrop-blur-2xl sticky top-0">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex flex-col leading-none">
            <span className="text-xl font-extrabold tracking-tight gradient-text">Synapse</span>
            <span className="text-[9px] text-muted-foreground/60 tracking-widest uppercase mt-0.5">
              Akıllı Pazar Analitiği
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Badge
              variant="outline"
              className="hidden sm:flex items-center gap-1.5 px-3 py-1 bg-primary/5 border-primary/20 text-xs text-primary"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              Beta Sürüm
            </Badge>
            <Link href="/login">
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                Giriş Yap
              </Button>
            </Link>
            <Link href="/register">
              <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }}>
                <Button size="sm" className="shadow-lg shadow-indigo-500/20">
                  Ücretsiz Başla
                </Button>
              </motion.div>
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10 flex-1 flex flex-col">

        <motion.section
          variants={stagger}
          initial="hidden"
          animate="visible"
          className="container mx-auto px-6 pt-6 sm:pt-12 pb-10 sm:pb-20 text-center max-w-5xl flex flex-col items-center justify-center min-h-[100svh]"
        >
          <motion.div variants={fadeUp} custom={0} className="flex justify-center mb-4 sm:mb-6">
            <Badge
              variant="outline"
              className="px-4 py-1.5 gap-2 bg-white/[0.04] border-white/10 text-sm backdrop-blur"
            >
              <Zap className="w-3.5 h-3.5 text-primary" />
              <span>Beta Sürüm</span>
              <span className="w-px h-3.5 bg-white/15" />
              <span className="text-muted-foreground text-xs">Ücretsiz erken erişim</span>
            </Badge>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            custom={0.05}
            className="text-4xl sm:text-5xl md:text-7xl lg:text-[82px] font-extrabold tracking-tight leading-[1.06] mb-4 sm:mb-6"
          >
            E-ticaretinizi{' '}
            <span className="relative inline-block">
              <span className="gradient-text">saniyeler içinde</span>
              <svg
                className="absolute -bottom-2 left-0 w-full"
                viewBox="0 0 300 8"
                fill="none"
                preserveAspectRatio="none"
              >
                <path
                  d="M2 6 Q75 2 150 5 Q225 8 298 4"
                  stroke="url(#heroLine)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
                <defs>
                  <linearGradient id="heroLine" x1="0" y1="0" x2="300" y2="0">
                    <stop offset="0%" stopColor="hsl(245,58%,61%)" />
                    <stop offset="100%" stopColor="hsl(265,60%,60%)" />
                  </linearGradient>
                </defs>
              </svg>
            </span>{' '}
            <br className="hidden sm:block" />
            daha rekabetçi hale getirin
          </motion.h1>

          <motion.p
            variants={fadeUp}
            custom={0.1}
            className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed"
          >
            Ürünlerinizi rakipler, fiyat, SEO ve görsel kalite açısından analiz edin. Daha güçlü listelemelerle satış potansiyelinizi artırın.
          </motion.p>

          <motion.div
            variants={fadeUp}
            custom={0.15}
            className="flex flex-wrap justify-center gap-x-6 gap-y-2 mt-3 sm:mt-5 text-sm text-muted-foreground"
          >
            {highlights.map((h) => (
              <span key={h} className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                {h}
              </span>
            ))}
          </motion.div>

          <motion.div
            variants={fadeUp}
            custom={0.2}
            className="flex flex-col sm:flex-row sm:items-center justify-center gap-3 mt-5 sm:mt-8"
          >
            <Link href="/register" className="w-full sm:w-auto">
              <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                <Button
                  size="lg"
                  className="w-full sm:w-auto h-14 px-8 text-base font-semibold shadow-2xl shadow-indigo-500/25 gap-2"
                >
                  Analiz Başlat
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </motion.div>
            </Link>
            <a href="#preview" className="w-full sm:w-auto">
              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <Button
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto h-14 px-8 text-base border-white/10 bg-white/[0.03] hover:bg-white/[0.07]"
                >
                  Örnek Sonucu Gör
                </Button>
              </motion.div>
            </a>
          </motion.div>

          <motion.div
            variants={fadeUp}
            custom={0.25}
            className="flex items-center justify-center gap-2 mt-4 sm:mt-6"
          >
            <span className="text-xs text-muted-foreground/50 mr-1">Desteklenen platformlar:</span>
            {[
              { name: 'Trendyol', cls: 'text-orange-400 border-orange-400/25 bg-orange-400/8' },
              { name: 'Amazon', cls: 'text-amber-400 border-amber-400/25 bg-amber-400/8' },
              { name: 'Hepsiburada', cls: 'text-purple-400 border-purple-400/25 bg-purple-400/8' },
            ].map((p) => (
              <Badge key={p.name} variant="outline" className={`text-[11px] px-2.5 py-0.5 ${p.cls}`}>
                {p.name}
              </Badge>
            ))}
          </motion.div>
        </motion.section>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="container mx-auto px-6 max-w-4xl mb-24"
        >
          <div className="glass-card rounded-2xl px-8 py-5 flex flex-col md:flex-row items-center justify-center gap-6 md:gap-12 text-center">
            {[
              { icon: Shield, color: 'text-emerald-500', label: 'SSL ile şifreli veri aktarımı' },
              { icon: Zap, color: 'text-primary', label: 'Ortalama analiz: ~60 saniye' },
              { icon: Sparkles, color: 'text-violet-400', label: 'Çok-ajan analiz sistemi' },
            ].map(({ icon: Icon, color, label }) => (
              <div key={label} className="flex items-center gap-2.5">
                <Icon className={`w-4 h-4 shrink-0 ${color}`} />
                <span className="text-sm text-muted-foreground">{label}</span>
              </div>
            ))}
          </div>
        </motion.div>

        <section className="container mx-auto px-6 max-w-6xl mb-28">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-12"
          >
            <p className="text-xs uppercase tracking-widest text-primary font-semibold mb-3">Özellikler</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              Her şey tek bir platformda
            </h2>
          </motion.div>

          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-60px' }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          >
            {features.map((f, i) => (
              <motion.div
                key={i}
                variants={cardIn}
                whileHover={{ y: -5, transition: { duration: 0.2 } }}
                className={`group glass-card rounded-2xl p-6 border border-white/[0.07] transition-all duration-300 relative overflow-hidden cursor-default ${f.border}`}
              >
                <div className={`absolute inset-0 transition-colors duration-500 ${f.glow} pointer-events-none`} />
                <div
                  className={`w-11 h-11 rounded-xl bg-gradient-to-br ${f.gradient} flex items-center justify-center mb-5 shadow-lg relative`}
                >
                  <f.icon className="w-5 h-5 text-white" />
                </div>
                <h3 className="font-semibold text-base mb-2 relative">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed relative">{f.description}</p>
              </motion.div>
            ))}
          </motion.div>
        </section>

        <motion.section
          id="preview"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.4 }}
          className="container mx-auto px-6 max-w-6xl mb-28 scroll-mt-20"
        >
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-12"
          >
            <Badge variant="outline" className="mb-4 px-3 py-1 bg-white/[0.04] border-white/10 text-xs text-muted-foreground">
              Örnek Analiz Çıktısı
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              Gerçek bir analiz böyle görünür
            </h2>
            <p className="text-muted-foreground mt-3 max-w-lg mx-auto text-base">
              Ürününüzü girdikten sonra ajan sistemi devreye girer ve kapsamlı rapor hazırlar.
            </p>
          </motion.div>

          <div className="grid lg:grid-cols-[5fr_7fr] gap-5 items-stretch">

            <motion.div
              initial={{ opacity: 0, x: -28 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="glass-card rounded-2xl overflow-hidden border border-white/[0.07] flex flex-col"
            >
              <div className="px-4 py-3 border-b border-white/[0.06] flex items-center gap-2 shrink-0">
                <div className="flex gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500/50" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/50" />
                </div>
                <span className="text-xs text-muted-foreground/60 ml-1.5 flex items-center gap-1.5">
                  <Package className="w-3 h-3" /> Ürün Görseli
                </span>
              </div>

              <div className="flex-1 relative bg-gradient-to-br from-indigo-500/[0.08] via-violet-500/[0.06] to-purple-500/[0.08] flex flex-col justify-center min-h-[300px]">
                <div className="absolute inset-0 bg-grid-sm pointer-events-none" />
                <div className="relative z-10 p-5 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium text-center">Mevcut Görsel</p>
                      <div className="rounded-xl overflow-hidden border border-white/[0.12] bg-white/[0.03]">
                        <img src="/demo-kupa.jpg" alt="Mevcut görsel" className="w-full h-28 object-cover" />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <p className="text-[10px] text-emerald-400 uppercase tracking-wider font-medium text-center">Optimize Görsel</p>
                      <div className="rounded-xl overflow-hidden border border-emerald-500/25 bg-white/[0.03]">
                        <img src="/demo-kupa.jpg" alt="Optimize görsel" className="w-full h-28 object-cover" />
                      </div>
                    </div>
                  </div>
                  <div className="glass-card rounded-xl p-3 backdrop-blur-xl border border-white/[0.09]">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-medium">Keep Calm Kupa 330ml</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5">Trendyol · Kupa / Bardak</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-primary">₺154,90</p>
                        <p className="text-[10px] text-emerald-500">Önerilen fiyat</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 28 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.08 }}
              className="flex flex-col gap-4"
            >
              <motion.div
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: 0.14 }}
                className="glass-card rounded-2xl border border-white/[0.07] overflow-hidden flex-1"
              >
                <div className="px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-blue-500/15 border border-blue-500/20 flex items-center justify-center">
                      <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
                    </div>
                    <span className="text-sm font-semibold">Rakip Analizi Çıktısı</span>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/25 bg-emerald-500/8 py-0.5">
                    3 rakip bulundu
                  </Badge>
                </div>

                <div className="p-5 space-y-4">
                  <div className="space-y-0 divide-y divide-white/[0.05]">
                    {mockRivals.slice(0, 2).map((r, i) => (
                      <div key={i} className="flex items-center justify-between py-2.5">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="w-6 h-6 rounded-md bg-white/[0.05] border border-white/[0.08] flex items-center justify-center shrink-0">
                            <span className="text-[9px] font-bold text-muted-foreground">{i + 1}</span>
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm truncate">{r.name}</p>
                            <p className="text-[10px] text-muted-foreground">{r.brand}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 shrink-0 ml-3">
                          <div className="flex items-center gap-0.5">
                            <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                            <span className="text-xs text-muted-foreground">{r.rating}</span>
                          </div>
                          <span className="text-sm font-semibold text-foreground">{r.price}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-start gap-2 p-3 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/15">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-px" />
                    <p className="text-xs text-muted-foreground leading-snug">
                      <span className="text-foreground font-medium">Fırsat: </span>
                      Hediye paketi ve kişiselleştirme sunan rakip az.
                    </p>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: 0.22 }}
                className="glass-card rounded-2xl border border-white/[0.07] overflow-hidden flex-1"
              >
                <div className="px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-violet-500/15 border border-violet-500/20 flex items-center justify-center">
                      <Search className="w-3.5 h-3.5 text-violet-400" />
                    </div>
                    <span className="text-sm font-semibold">SEO Optimizasyon Çıktısı</span>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-violet-400 border-violet-500/25 bg-violet-500/8 py-0.5">
                    Profesyonel Ton
                  </Badge>
                </div>

                <div className="p-5 space-y-4">
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium mb-1.5">SEO Başlığı</p>
                    <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.08]">
                      <p className="text-sm font-medium leading-snug">
                        Keep Calm Seramik Kupa 330ml | Kırmızı Slogan Baskılı | Hediye Ambalaj Seçeneği
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium mb-1.5">Anahtar Kelimeler</p>
                    <div className="flex flex-wrap gap-1.5">
                      {['seramik kupa hediye', 'slogan baskılı kupa', 'kırmızı ofis kupası'].map((kw) => (
                        <Badge key={kw} variant="outline" className="text-[10px] bg-white/[0.03] border-white/[0.09]">
                          {kw}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          </div>
          <p className="text-center text-sm text-muted-foreground mt-8 max-w-lg mx-auto">
            Detaylı rakip analizi, SEO önerileri ve görsel optimizasyon için ücretsiz hesap oluşturun.
          </p>
        </motion.section>

        <section className="container mx-auto px-6 max-w-6xl mb-28">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-12"
          >
            <p className="text-xs uppercase tracking-widest text-primary font-semibold mb-3">Planlar</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Doğru planı seçin</h2>
            <p className="text-muted-foreground mt-3 max-w-lg mx-auto">
              Beta sürecinde tüm özellikler ücretsiz. İlerideki planlar için erken erişim listesine katılın.
            </p>
          </motion.div>

          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid md:grid-cols-3 gap-5"
          >
            {plans.map((plan, i) => (
              <motion.div
                key={i}
                variants={cardIn}
                whileHover={{ y: -6, transition: { duration: 0.2 } }}
                className={`glass-card rounded-2xl p-6 flex flex-col relative overflow-hidden ${
                  plan.highlight
                    ? 'border-primary/25 bg-primary/[0.025]'
                    : 'border-white/[0.07]'
                }`}
              >
                {plan.highlight && (
                  <>
                    <div className="absolute top-0 right-0 w-48 h-48 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
                    <div className="absolute -top-px left-6 right-6 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent" />
                  </>
                )}

                <div className="flex items-start justify-between mb-5 relative">
                  <h3 className="text-lg font-bold">{plan.name}</h3>
                  <Badge variant="outline" className={`text-[10px] ${plan.badgeClass}`}>
                    {plan.badge}
                  </Badge>
                </div>

                <div className="mb-6 relative">
                  <span className="text-3xl font-extrabold">{plan.price}</span>
                  <span className="text-sm text-muted-foreground ml-2">{plan.sub}</span>
                </div>

                <ul className="space-y-2.5 flex-1 mb-6 relative">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2.5 text-sm text-muted-foreground">
                      <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link href={plan.href} className="relative">
                  <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    <Button
                      className="w-full"
                      variant={plan.highlight ? 'default' : 'outline'}
                      size="lg"
                    >
                      {plan.cta}
                    </Button>
                  </motion.div>
                </Link>
              </motion.div>
            ))}
          </motion.div>
        </section>

      </main>

      <footer className="relative z-10 border-t border-white/[0.06] bg-background/60 backdrop-blur-xl">
        <div className="container mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <span className="text-base font-extrabold tracking-tight gradient-text">Synapse</span>
              <span className="text-muted-foreground text-sm">© 2026</span>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-1.5 sm:gap-5 text-sm text-center">
              <span className="font-semibold text-foreground tracking-wide">BİRİNCİYİZ Team</span>
              <span className="hidden sm:block text-white/20">·</span>
              <span className="text-muted-foreground">2026 BTK Hackhaton İçin Tasarlanmıştır</span>
            </div>

            <Badge variant="outline" className="text-[10px] text-muted-foreground border-white/10 bg-white/[0.03] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              Beta Sürüm
            </Badge>
          </div>
        </div>
      </footer>
    </div>
  );
}