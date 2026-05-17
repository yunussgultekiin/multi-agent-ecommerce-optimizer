'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Plus, Trash2, Box, Store, Search, ArrowRight, ArrowLeft, Sparkles, Tag, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { analyzeSchema, type AnalyzeFormInput, type AnalyzeFormData } from '@/lib/validations';
import type { Platform, SeoTone } from '@/types';
import api from '@/lib/api';

const STEPS = [
  { id: 0, title: 'Temel Bilgiler', icon: Box, subtitle: 'Ürün adı, açıklama ve platform' },
  { id: 1, title: 'Satış Bilgileri', icon: Store, subtitle: 'Fiyat ve kategori' },
  { id: 2, title: 'Detaylar', icon: Search, subtitle: 'SEO tonu ve varyantlar' },
];

const slideVariants = {
  enter: (direction: number) => ({ x: direction > 0 ? 80 : -80, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({ x: direction > 0 ? -80 : 80, opacity: 0 }),
};

const SEO_TONE_DEFAULTS: Record<Platform, SeoTone> = {
  trendyol: 'professional',
  amazon: 'professional',
  hepsiburada: 'professional',
};

const SEO_TONE_OPTIONS: { value: SeoTone; label: string; description: string }[] = [
  { value: 'casual',       label: 'Samimi & Genç',  description: 'Sıcak, samimi ve genç bir dil' },
  { value: 'professional', label: 'Profesyonel',    description: 'Güvenilir ve bilgilendirici' },
  { value: 'premium',      label: 'Premium',        description: 'Minimal, seçkin ve prestijli' },
];

export default function AnalyzePage() {
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const router = useRouter();
  const { toast } = useToast();

  const {
    register,
    control,
    handleSubmit,
    setValue,
    watch,
    trigger,
    formState: { errors },
  } = useForm<AnalyzeFormInput, unknown, AnalyzeFormData>({
    resolver: zodResolver(analyzeSchema),
    defaultValues: {
      platform: 'trendyol',
      seo_tone: 'professional',
      variants: [],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'variants' });
  const platformValue = watch('platform');
  const seoToneValue = watch('seo_tone');

  const nextStep = async () => {
    const fieldsToValidate: (keyof AnalyzeFormInput)[] =
      step === 0
        ? ['title', 'description', 'brand', 'platform']
        : step === 1
        ? ['price', 'category']
        : [];
    const isValid = await trigger(fieldsToValidate);
    if (isValid) setStep((s) => Math.min(s + 1, 2));
  };

  const prevStep = () => setStep((s) => Math.max(s - 1, 0));

  const handleImageUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const token = (await import('js-cookie')).default.get('access_token');
      const res = await fetch(`${baseUrl}/upload/image`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Yükleme başarısız');
      }
      const { url } = await res.json();
      setUploadedImageUrl(url);
    } catch (error: any) {
      toast({ variant: 'destructive', title: 'Görsel Yüklenemedi', description: error.message });
    } finally {
      setIsUploading(false);
    }
  };

  const onSubmit = async (data: AnalyzeFormData) => {
    try {
      setIsLoading(true);
      const seoKeywords = data.seo_keywords
        ? data.seo_keywords.split(',').map((k) => k.trim()).filter(Boolean)
        : [];

      const userProduct = {
        title: data.title,
        description: data.description,
        brand: data.brand,
        price: data.price,
        category: data.category,
        seo_keywords: seoKeywords,
        image_urls: uploadedImageUrl ? [uploadedImageUrl] : [],
        variants: (data.variants || []).map((v) => ({
          ...v,
          price: data.price + v.price_diff,
        })),
      };

      const payload = {
        ...userProduct,
        platform: data.platform,
        user_product: userProduct,
        target_platform: data.platform,
      };

      const res = await api.post('/analyze', {
        payload,
        seo_tone: data.seo_tone,
      });

      const taskId = res.data.id;
      toast({ title: 'Analiz Başlatıldı', description: 'Ürününüz AI tarafından inceleniyor...' });
      router.push(`/dashboard/analyze/${taskId}/progress`);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Hata',
        description:
          error.response?.data?.detail || 'Analiz başlatılamadı. Kotanızı kontrol edin.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-3xl font-bold tracking-tight">Yeni Analiz</h1>
        <p className="text-muted-foreground mt-1">
          Ürün bilgilerinizi girin, gerisini yapay zekaya bırakın.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="flex items-center gap-3"
      >
        {STEPS.map((s, i) => (
          <div key={s.id} className="flex items-center gap-3 flex-1">
            <button
              type="button"
              onClick={() => { if (i < step) setStep(i); }}
              className={`flex items-center gap-3 flex-1 p-3 rounded-xl transition-all duration-300 ${
                i === step
                  ? 'bg-primary/10 border border-primary/20 shadow-sm shadow-primary/5'
                  : i < step
                  ? 'bg-white/[0.04] border border-white/10 cursor-pointer hover:bg-white/[0.06]'
                  : 'bg-white/[0.02] border border-white/5 opacity-50'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  i === step ? 'gradient-bg' : i < step ? 'bg-emerald-500/20' : 'bg-white/10'
                }`}
              >
                {i < step ? (
                  <span className="text-emerald-400 text-sm font-bold">✓</span>
                ) : (
                  <s.icon
                    className={`w-4 h-4 ${i === step ? 'text-white' : 'text-muted-foreground'}`}
                  />
                )}
              </div>
              <div className="hidden md:block text-left min-w-0">
                <p
                  className={`text-xs font-medium truncate ${
                    i === step ? 'text-primary' : 'text-muted-foreground'
                  }`}
                >
                  {s.title}
                </p>
                <p className="text-[10px] text-muted-foreground/60 truncate">{s.subtitle}</p>
              </div>
            </button>
            {i < STEPS.length - 1 && (
              <div
                className={`hidden sm:block w-8 h-0.5 shrink-0 rounded-full transition-colors ${
                  i < step ? 'bg-emerald-500/40' : 'bg-white/10'
                }`}
              />
            )}
          </div>
        ))}
      </motion.div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <AnimatePresence mode="wait" custom={step}>
          {step === 0 && (
            <motion.div
              key="step-0"
              custom={1}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Box className="w-5 h-5 text-primary" />
                    Temel Bilgiler
                  </CardTitle>
                  <CardDescription>Ürününüzün temel bilgilerini girin</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="title">Ürün Başlığı *</Label>
                    <Input
                      id="title"
                      placeholder="Örn: iPhone 15 Pro Max 256GB"
                      {...register('title')}
                      className={errors.title ? 'border-destructive' : ''}
                    />
                    {errors.title && (
                      <p className="text-sm text-destructive">{errors.title.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Ürün Açıklaması *</Label>
                    <Textarea
                      id="description"
                      rows={4}
                      placeholder="Ürününüzün tüm özelliklerini detaylıca yazın..."
                      {...register('description')}
                      className={errors.description ? 'border-destructive' : ''}
                    />
                    {errors.description && (
                      <p className="text-sm text-destructive">{errors.description.message}</p>
                    )}
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="brand">Marka *</Label>
                      <Input
                        id="brand"
                        placeholder="Örn: Apple"
                        {...register('brand')}
                        className={errors.brand ? 'border-destructive' : ''}
                      />
                      {errors.brand && (
                        <p className="text-sm text-destructive">{errors.brand.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label>Hedef Platform *</Label>
                      <Select
                        value={platformValue}
                        onValueChange={(v: Platform) => {
                          setValue('platform', v);
                          setValue('seo_tone', SEO_TONE_DEFAULTS[v]);
                        }}
                      >
                        <SelectTrigger className={errors.platform ? 'border-destructive' : ''}>
                          <SelectValue placeholder="Platform seçin" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="trendyol">🟠 Trendyol</SelectItem>
                          <SelectItem value="amazon">🟡 Amazon</SelectItem>
                          <SelectItem value="hepsiburada">🟣 Hepsiburada</SelectItem>
                        </SelectContent>
                      </Select>
                      {errors.platform && (
                        <p className="text-sm text-destructive">{errors.platform.message}</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {step === 1 && (
            <motion.div
              key="step-1"
              custom={1}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Store className="w-5 h-5 text-primary" />
                    Satış Bilgileri
                  </CardTitle>
                  <CardDescription>Fiyat ve kategori bilgilerini belirleyin</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="price">Mevcut Fiyat (TL) *</Label>
                    <Input
                      id="price"
                      type="number"
                      step="0.01"
                      placeholder="999.90"
                      {...register('price')}
                      className={errors.price ? 'border-destructive' : ''}
                    />
                    {errors.price && (
                      <p className="text-sm text-destructive">{errors.price.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="category">Kategori *</Label>
                    <Input
                      id="category"
                      placeholder="Elektronik > Cep Telefonu"
                      {...register('category')}
                      className={errors.category ? 'border-destructive' : ''}
                    />
                    {errors.category && (
                      <p className="text-sm text-destructive">{errors.category.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Ürün Görseli</Label>
                    {uploadedImageUrl ? (
                      <div className="relative group rounded-xl overflow-hidden border border-white/10 bg-white/[0.02]">
                        <img
                          src={uploadedImageUrl}
                          alt="Yüklenen görsel"
                          className="w-full max-h-48 object-contain p-2"
                        />
                        <button
                          type="button"
                          onClick={() => setUploadedImageUrl(null)}
                          className="absolute top-2 right-2 p-1 rounded-full bg-destructive/80 hover:bg-destructive transition-colors"
                        >
                          <X className="w-3 h-3 text-white" />
                        </button>
                        <p className="text-xs text-emerald-500 px-3 pb-2">Görsel yüklendi</p>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border border-dashed border-white/10 bg-white/[0.01] hover:bg-white/[0.03] hover:border-white/20 cursor-pointer transition-all">
                        {isUploading ? (
                          <>
                            <Loader2 className="w-8 h-8 text-primary animate-spin" />
                            <span className="text-sm text-muted-foreground">Yükleniyor...</span>
                          </>
                        ) : (
                          <>
                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                              <Upload className="w-5 h-5 text-primary" />
                            </div>
                            <div className="text-center">
                              <p className="text-sm font-medium">Görsel yükle</p>
                              <p className="text-xs text-muted-foreground mt-0.5">JPEG, PNG veya WebP · Maks 10 MB</p>
                            </div>
                          </>
                        )}
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          className="hidden"
                          disabled={isUploading}
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleImageUpload(file);
                            e.target.value = '';
                          }}
                        />
                      </label>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Opsiyonel — görsel yoksa AI arka plan temizleme adımı atlanır
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step-2"
              custom={1}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3 }}
              className="space-y-6"
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Search className="w-5 h-5 text-primary" />
                    SEO & Anahtar Kelimeler
                  </CardTitle>
                  <CardDescription>Daha iyi analiz için opsiyonel detayları ekleyin</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="space-y-3">
                    <Label>SEO Tonu</Label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {SEO_TONE_OPTIONS.map((opt) => {
                        const isSelected = seoToneValue === opt.value;
                        return (
                          <button
                            key={opt.value}
                            type="button"
                            onClick={() => setValue('seo_tone', opt.value)}
                            className={`flex flex-col gap-1.5 p-4 rounded-xl border text-left transition-all duration-150 ${
                              isSelected
                                ? 'border-primary/40 bg-primary/[0.07] shadow-sm shadow-primary/10'
                                : 'border-white/[0.07] bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/[0.12]'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className={`text-sm font-semibold leading-tight ${isSelected ? 'text-primary' : ''}`}>
                                {opt.label}
                              </span>
                              <div className={`shrink-0 w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors ${
                                isSelected ? 'border-primary' : 'border-white/20'
                              }`}>
                                {isSelected && <div className="w-2 h-2 rounded-full bg-primary" />}
                              </div>
                            </div>
                            <p className="text-xs text-muted-foreground leading-snug">{opt.description}</p>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="seo_keywords">SEO Anahtar Kelimeler</Label>
                    <Input
                      id="seo_keywords"
                      placeholder="virgülle ayırın (örn: telefon, akıllı, 5g)"
                      {...register('seo_keywords')}
                    />
                    <p className="text-xs text-muted-foreground">
                      Birden fazla kelime virgül ile ayrılmalıdır
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Tag className="w-5 h-5 text-primary" />
                      Varyantlar
                    </CardTitle>
                    <CardDescription>Renk veya beden seçenekleri ekleyin (opsiyonel)</CardDescription>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => append({ name: '', color: '', price_diff: '' })}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Ekle
                  </Button>
                </CardHeader>
                <CardContent>
                  {fields.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground border border-dashed border-white/10 rounded-lg bg-white/[0.01]">
                      <Tag className="w-6 h-6 mx-auto mb-2 opacity-40" />
                      <p className="text-sm">Eklenmiş varyant yok.</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {fields.map((field, index) => (
                        <motion.div
                          key={field.id}
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="flex items-end gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/5"
                        >
                          <div className="flex-1 space-y-1">
                            <Label className="text-xs">Ad</Label>
                            <Input
                              {...register(`variants.${index}.name`)}
                              placeholder="L Beden"
                              className="h-9"
                            />
                          </div>
                          <div className="flex-1 space-y-1">
                            <Label className="text-xs">Renk</Label>
                            <Input
                              {...register(`variants.${index}.color`)}
                              placeholder="Siyah"
                              className="h-9"
                            />
                          </div>
                          <div className="flex-1 space-y-1">
                            <Label className="text-xs">Fiyat Farkı</Label>
                            <Input
                              type="number"
                              {...register(`variants.${index}.price_diff`)}
                              placeholder="0"
                              className="h-9"
                            />
                          </div>
                          <Button
                            type="button"
                            variant="destructive"
                            size="icon"
                            onClick={() => remove(index)}
                            className="h-9 w-9 shrink-0"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="flex items-center justify-between pt-8"
        >
          <div>
            {step > 0 && (
              <Button type="button" variant="outline" onClick={prevStep} className="gap-2">
                <ArrowLeft className="w-4 h-4" />
                Geri
              </Button>
            )}
          </div>
          <div>
            {step < 2 ? (
              <Button type="button" onClick={nextStep} className="gap-2 h-11 px-8">
                Devam Et
                <ArrowRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                type="submit"
                size="lg"
                disabled={isLoading}
                className="h-12 px-10 text-base shadow-xl gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Analiz Başlatılıyor...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Analizi Başlat
                  </>
                )}
              </Button>
            )}
          </div>
        </motion.div>
      </form>
    </div>
  );
}
