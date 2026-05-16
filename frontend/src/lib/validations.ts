import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Geçerli bir e-posta adresi giriniz'),
  password: z.string().min(1, 'Şifre gereklidir'),
});

export const registerSchema = z
  .object({
    email: z.string().email('Geçerli bir e-posta adresi giriniz'),
    password: z.string().min(8, 'Şifre en az 8 karakter olmalıdır'),
    confirmPassword: z.string().min(8, 'Şifre tekrarı gereklidir'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Şifreler eşleşmiyor',
    path: ['confirmPassword'],
  });

export const analyzeSchema = z.object({
  title: z.string().min(3, 'Ürün başlığı en az 3 karakter olmalıdır'),
  description: z.string().min(10, 'Açıklama en az 10 karakter olmalıdır'),
  brand: z.string().min(1, 'Marka zorunludur'),
  price: z
    .string()
    .min(1, 'Fiyat gereklidir')
    .transform((v) => Number(v))
    .pipe(z.number().positive('Fiyat pozitif olmalıdır')),
  category: z.string().min(1, 'Kategori zorunludur'),
  stock: z
    .string()
    .min(1, 'Stok gereklidir')
    .transform((v) => Number(v))
    .pipe(z.number().int().nonnegative('Stok negatif olamaz')),
  weight: z
    .string()
    .optional()
    .transform((v) => (v === '' || v === undefined ? undefined : Number(v)))
    .pipe(z.number().positive().optional()),
  dimensions: z.string().optional(),
  seo_keywords: z.string().optional(),
  image_urls: z.string().optional(),
  platform: z.enum(['trendyol', 'amazon', 'hepsiburada']),
  seo_tone: z.enum(['casual', 'professional', 'premium']),
  variants: z
    .array(
      z.object({
        name: z.string().min(1, 'Varyant adı gerekli'),
        color: z.string().min(1, 'Renk gerekli'),
        price_diff: z
          .string()
          .transform((v) => Number(v))
          .pipe(z.number()),
      }),
    )
    .optional()
    .default([]),
});

export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;

export type AnalyzeFormInput = z.input<typeof analyzeSchema>;
export type AnalyzeFormData = z.output<typeof analyzeSchema>;
