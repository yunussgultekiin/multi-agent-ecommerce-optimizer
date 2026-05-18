'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle2, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/store/auth';
import { loginSchema, type LoginFormData } from '@/lib/validations';

const panelFeatures = [
  'Saniyeler içinde rakip analizi',
  'Platforma özel SEO önerileri',
  'Optimize ürün görseli üretimi',
  'Akıllı fiyat stratejisi',
];

const testimonials = [
  {
    text: 'Rakip analizini manuel yapmak saatler alıyordu. Synapse ile bunu dakikalar içinde yapıyorum.',
    name: 'Ahmet Y.',
    title: 'Trendyol Satıcısı',
    initial: 'A',
  },
  {
    text: 'SEO önerilerini uyguladıktan sonra ürünlerim arama sonuçlarında çok daha üst sıralara çıktı.',
    name: 'Merve K.',
    title: 'Amazon TR Satıcısı',
    initial: 'M',
  },
  {
    text: 'Fiyat stratejisi önerileri sayesinde kâr marjımı düşürmeden rakiplerimle rekabet edebiliyorum.',
    name: 'Emre S.',
    title: 'Hepsiburada Satıcısı',
    initial: 'E',
  },
];

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [testimonialIdx, setTestimonialIdx] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setTestimonialIdx((prev) => (prev + 1) % testimonials.length);
    }, 20000);
    return () => clearInterval(timer);
  }, []);
  const router = useRouter();
  const { login } = useAuthStore();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      setIsLoading(true);
      await login(data.email, data.password);
      router.push('/dashboard');
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Giriş Başarısız',
        description: error.response?.data?.detail || 'Lütfen bilgilerinizi kontrol edin.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden bg-background">

      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full bg-indigo-600/10 blur-[140px]" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-violet-600/8 blur-[120px]" />
        <div className="absolute inset-0 bg-grid pointer-events-none" />
      </div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="hidden lg:flex lg:w-[48%] relative flex-col justify-between p-10 border-r border-white/[0.06]"
      >
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <span className="text-2xl font-extrabold tracking-tight gradient-text">Synapse</span>
          </Link>
          <Link href="/">
            <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-3.5 h-3.5" />
              Ana Sayfa
            </Button>
          </Link>
        </div>

        <div className="space-y-8">
          <div>
            <Badge
              variant="outline"
              className="mb-5 px-3 py-1 gap-1.5 bg-primary/5 border-primary/20 text-primary text-xs"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              Beta Sürüm · Ücretsiz
            </Badge>
            <h2 className="text-3xl font-bold tracking-tight leading-tight mb-4">
              E-ticaret başarınızı<br />veri ile büyütün
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Ürünlerinizi rakipler, fiyat ve SEO açısından analiz edin. Daha güçlü listelemelerle satışlarınızı artırın.
            </p>
          </div>

          <ul className="space-y-3">
            {panelFeatures.map((f) => (
              <li key={f} className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="w-5 h-5 rounded-full bg-emerald-500/15 border border-emerald-500/25 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                </div>
                {f}
              </li>
            ))}
          </ul>
        </div>

        <div className="glass-card rounded-2xl p-5 border border-white/[0.08] overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={testimonialIdx}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.4 }}
            >
              <p className="text-sm text-muted-foreground leading-relaxed italic">
                &ldquo;{testimonials[testimonialIdx].text}&rdquo;
              </p>
              <div className="flex items-center gap-2.5 mt-4">
                <div className="w-7 h-7 rounded-full gradient-bg flex items-center justify-center text-xs font-bold text-white">
                  {testimonials[testimonialIdx].initial}
                </div>
                <div>
                  <p className="text-xs font-medium">{testimonials[testimonialIdx].name}</p>
                  <p className="text-[10px] text-muted-foreground">{testimonials[testimonialIdx].title}</p>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </motion.div>

      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="w-full max-w-sm"
        >
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <span className="text-2xl font-extrabold tracking-tight gradient-text">Synapse</span>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight">Tekrar hoş geldiniz</h1>
            <p className="text-sm text-muted-foreground mt-1.5">
              Hesabınıza giriş yaparak analizlere devam edin.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium">E-posta</Label>
              <Input
                id="email"
                type="email"
                placeholder="ornek@sirket.com"
                autoComplete="email"
                {...register('email')}
                className={`h-11 ${errors.email ? 'border-destructive focus:border-destructive' : ''}`}
              />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium">Şifre</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
                className={`h-11 ${errors.password ? 'border-destructive focus:border-destructive' : ''}`}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
              <Button type="submit" className="w-full h-11 font-medium shadow-lg shadow-indigo-500/15" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Giriş yapılıyor...
                  </>
                ) : (
                  'Giriş Yap'
                )}
              </Button>
            </motion.div>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Hesabınız yok mu?{' '}
            <Link href="/register" className="text-primary hover:underline font-medium">
              Ücretsiz Kaydol
            </Link>
          </p>

          <div className="mt-6 text-center lg:hidden">
            <Link href="/" className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center gap-1">
              <ArrowLeft className="w-3 h-3" />
              Ana sayfaya dön
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
