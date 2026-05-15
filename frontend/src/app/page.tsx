'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BarChart3, LineChart, Search, Sparkles, ShoppingBag, ArrowRight, CheckCircle2, Zap, Shield } from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.12 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } },
};

export default function Home() {
  const features = [
    {
      title: 'Rakip Analizi',
      description: 'Pazardaki tüm rakiplerinizi ve fiyatlarını AI ile anında keşfedin.',
      icon: Search,
      gradient: 'from-blue-500 to-cyan-500',
      glow: 'bg-blue-500/10',
    },
    {
      title: 'SEO Optimizasyonu',
      description: 'Platform algoritmasına uygun, yüksek dönüşümlü başlık ve açıklamalar üretin.',
      icon: LineChart,
      gradient: 'from-emerald-500 to-teal-500',
      glow: 'bg-emerald-500/10',
    },
    {
      title: 'Görsel İyileştirme',
      description: 'AI ile ürün görsellerinizi analiz edin ve daha çekici hale getirin.',
      icon: Sparkles,
      gradient: 'from-violet-500 to-purple-500',
      glow: 'bg-violet-500/10',
    },
    {
      title: 'Fiyat Analizi',
      description: 'Akıllı fiyatlandırma önerileri ile kâr marjınızı maksimize edin.',
      icon: BarChart3,
      gradient: 'from-amber-500 to-orange-500',
      glow: 'bg-amber-500/10',
    },
  ];

  const platforms = [
    { name: 'Trendyol', color: 'text-orange-400 border-orange-400/30 bg-orange-400/10' },
    { name: 'Amazon', color: 'text-amber-400 border-amber-400/30 bg-amber-400/10' },
    { name: 'Hepsiburada', color: 'text-purple-400 border-purple-400/30 bg-purple-400/10' },
  ];

  const highlights = [
    'Otomatik rakip keşfi',
    'AI-destekli fiyat optimizasyonu',
    'Platforma özel SEO başlıkları',
    'Görsel üretim ve analiz',
  ];

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-indigo-500/8 blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-purple-500/8 blur-[140px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[30%] h-[30%] rounded-full bg-violet-500/5 blur-[100px] pointer-events-none" />

      {/* Navigation */}
      <nav className="border-b border-white/5 bg-background/60 backdrop-blur-xl z-50 sticky top-0">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl gradient-bg flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <ShoppingBag className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">SellerPulse AI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" className="text-muted-foreground hover:text-foreground">
                Giriş Yap
              </Button>
            </Link>
            <Link href="/register">
              <Button className="shadow-lg shadow-indigo-500/20">Ücretsiz Başla</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center container mx-auto px-6">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="text-center max-w-4xl mx-auto pt-20 md:pt-32 pb-20 z-10"
        >
          <motion.div variants={itemVariants} className="flex flex-wrap items-center justify-center gap-3 mb-10">
            <Badge variant="outline" className="px-4 py-1.5 bg-white/5 border-white/10 text-sm gap-2">
              <Zap className="w-3.5 h-3.5 text-primary" />
              Hackathon Sürümü
            </Badge>
            <div className="flex items-center gap-2">
              {platforms.map((p) => (
                <Badge key={p.name} variant="outline" className={`px-3 py-1 text-xs font-medium ${p.color}`}>
                  {p.name}
                </Badge>
              ))}
            </div>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="text-5xl md:text-7xl lg:text-8xl font-extrabold tracking-tight leading-[1.05]"
          >
            E-ticaret başarınızı{' '}
            <br className="hidden md:block" />
            <span className="gradient-text">Yapay Zeka</span> ile katlayın
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed mt-8"
          >
            Rakiplerinizi analiz edin, fiyatlandırmanızı optimize edin ve satışlarınızı 
            otomatik pilotta artırın. Saniyeler içinde aksiyona dönüştürülebilir içgörüler alın.
          </motion.p>

          {/* Highlights */}
          <motion.div
            variants={itemVariants}
            className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-8 text-sm text-muted-foreground"
          >
            {highlights.map((h, i) => (
              <div key={i} className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>{h}</span>
              </div>
            ))}
          </motion.div>

          <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-12">
            <Link href="/register">
              <Button size="lg" className="h-14 px-10 text-lg group shadow-2xl shadow-indigo-500/20">
                Hemen Analiz Başlat
                <Sparkles className="ml-2 w-5 h-5 group-hover:rotate-12 transition-transform" />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline" className="h-14 px-10 text-lg group">
                Giriş Yap
                <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </motion.div>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 w-full max-w-6xl pb-32 z-10"
        >
          {features.map((feature, i) => (
            <motion.div
              key={i}
              variants={itemVariants}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              className="glass-card p-6 rounded-2xl hover:bg-white/[0.06] transition-all duration-300 group relative overflow-hidden"
            >
              <div className={`absolute top-0 right-0 w-32 h-32 ${feature.glow} rounded-full blur-3xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-5 shadow-lg`}>
                <feature.icon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </motion.div>

        {/* Trust bar */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="w-full max-w-4xl pb-20 z-10"
        >
          <div className="glass-card p-8 rounded-2xl flex flex-col md:flex-row items-center justify-center gap-8 text-center">
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-emerald-500" />
              <span className="text-sm text-muted-foreground">SSL ile güvenli veri aktarımı</span>
            </div>
            <div className="hidden md:block w-px h-6 bg-white/10" />
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-primary" />
              <span className="text-sm text-muted-foreground">Ortalama analiz süresi: ~60 saniye</span>
            </div>
            <div className="hidden md:block w-px h-6 bg-white/10" />
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-violet-500" />
              <span className="text-sm text-muted-foreground">GPT-4 destekli analiz motoru</span>
            </div>
          </div>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-background/50 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="w-5 h-5 rounded gradient-bg flex items-center justify-center">
              <ShoppingBag className="w-3 h-3 text-white" />
            </div>
            SellerPulse AI © 2026
          </div>
          <p className="text-xs text-muted-foreground">Hackathon Demo</p>
        </div>
      </footer>
    </div>
  );
}
