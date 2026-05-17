'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { Loader2, CheckCircle2, ArrowLeft, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/store/auth';
import { registerSchema, type RegisterFormData } from '@/lib/validations';

const freeTierFeatures = [
  '5 analiz / gün — ücretsiz',
  'Görsel üretimi dahil',
  'Geçmiş analizler kaydedilir',
  'SEO ve rakip raporu',
];

export default function RegisterPage() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { register: registerUser } = useAuthStore();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setIsLoading(true);
      await registerUser(data.email, data.password);
      toast({
        variant: 'success',
        title: 'Kayıt Başarılı',
        description: 'Hesabınız oluşturuldu. Lütfen giriş yapın.',
      });
      router.push('/login');
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Kayıt Başarısız',
        description: error.response?.data?.detail || 'Bir hata oluştu.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden bg-background">

      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-32 right-0 w-[500px] h-[500px] rounded-full bg-violet-600/10 blur-[140px]" />
        <div className="absolute bottom-0 -left-32 w-[400px] h-[400px] rounded-full bg-indigo-600/8 blur-[120px]" />
        <div className="absolute inset-0 bg-grid pointer-events-none" />
      </div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="hidden lg:flex lg:w-[48%] relative flex-col justify-between p-10 border-r border-white/[0.06]"
      >
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <img src="/synapse-logo.png" alt="Synapse" className="h-9 w-auto" />
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
              className="mb-5 px-3 py-1 gap-1.5 bg-emerald-500/8 border-emerald-500/25 text-emerald-400 text-xs"
            >
              <Zap className="w-3 h-3" />
              Beta süresince tamamen ücretsiz
            </Badge>
            <h2 className="text-3xl font-bold tracking-tight leading-tight mb-4">
              Ücretsiz hesabınızla<br />hemen başlayın
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Kredi kartı gerekmez. Beta süresince tüm özellikler açık — rakiplerinizin önüne geçin.
            </p>
          </div>

          <div className="space-y-3">
            <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Beta erişiminde şunlar dahil:</p>
            <ul className="space-y-3">
              {freeTierFeatures.map((f) => (
                <li key={f} className="flex items-center gap-3 text-sm text-muted-foreground">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/15 border border-emerald-500/25 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                  </div>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 border border-white/[0.08]">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center shrink-0 mt-0.5">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-medium mb-1">Ortalama analiz süresi</p>
              <p className="text-2xl font-extrabold gradient-text">~60 saniye</p>
              <p className="text-xs text-muted-foreground mt-1">
                Trendyol, Amazon ve Hepsiburada&apos;yı destekler
              </p>
            </div>
          </div>
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
            <img src="/synapse-logo.png" alt="Synapse" className="h-8 w-auto" />
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight">Hesap Oluştur</h1>
            <p className="text-sm text-muted-foreground mt-1.5">
              Ücretsiz kaydolun, dakikalar içinde analize başlayın.
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
                autoComplete="new-password"
                {...register('password')}
                className={`h-11 ${errors.password ? 'border-destructive focus:border-destructive' : ''}`}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="confirmPassword" className="text-sm font-medium">Şifre Tekrar</Label>
              <Input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                {...register('confirmPassword')}
                className={`h-11 ${errors.confirmPassword ? 'border-destructive focus:border-destructive' : ''}`}
              />
              {errors.confirmPassword && (
                <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
              )}
            </div>

            <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
              <Button type="submit" className="w-full h-11 font-medium shadow-lg shadow-indigo-500/15" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Hesap oluşturuluyor...
                  </>
                ) : (
                  'Ücretsiz Kaydol'
                )}
              </Button>
            </motion.div>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Zaten hesabınız var mı?{' '}
            <Link href="/login" className="text-primary hover:underline font-medium">
              Giriş Yap
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
