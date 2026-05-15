'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, PlusCircle, History, LogOut, ShoppingBag, Menu, X, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { useAuthStore } from '@/store/auth';
import { Skeleton } from '@/components/ui/skeleton';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Yeni Analiz', href: '/dashboard/analyze', icon: PlusCircle },
  { name: 'Geçmiş', href: '/dashboard/history', icon: History },
];

function SidebarContent({
  user,
  quota,
  pathname,
  quotaPercentage,
  logout,
}: {
  user: { email: string } | null;
  quota: { used: number; limit: number; remaining: number } | null;
  pathname: string;
  quotaPercentage: number;
  logout: () => void;
}) {
  return (
    <>
      <div className="flex h-16 shrink-0 items-center px-6 border-b border-white/5">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center">
            <ShoppingBag className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold tracking-tight">SellerPulse</span>
        </Link>
      </div>

      <nav className="flex-1 flex flex-col gap-1 px-4 py-6">
        {navigation.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== '/dashboard' && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-primary/10 text-primary shadow-sm shadow-primary/5'
                  : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {quota && (
        <div className="px-4 pb-4">
          <div className="glass-card p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                <span className="text-xs font-medium text-muted-foreground">Analiz Kotası</span>
              </div>
              <span className="text-xs font-bold text-primary">{quota.remaining} kalan</span>
            </div>
            <Progress value={quotaPercentage} className="h-1.5" />
            <p className="text-[10px] text-muted-foreground">
              {quota.used} / {quota.limit} kullanıldı
            </p>
          </div>
        </div>
      )}

      <div className="p-4 border-t border-white/5">
        <div className="flex items-center gap-3 mb-4 px-3">
          <Avatar className="h-9 w-9 border border-white/10">
            <AvatarFallback className="bg-primary/20 text-primary text-sm font-semibold">
              {user?.email.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex flex-col overflow-hidden">
            <span className="text-sm font-medium truncate">{user?.email}</span>
            <span className="text-xs text-muted-foreground">Kullanıcı</span>
          </div>
        </div>
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground hover:text-destructive hover:bg-destructive/10"
          onClick={logout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Çıkış Yap
        </Button>
      </div>
    </>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, quota, isLoading, isAuthenticated, fetchUser, fetchQuota, logout } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    fetchUser();
    fetchQuota();
  }, [fetchUser, fetchQuota]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-xl gradient-bg flex items-center justify-center animate-pulse">
            <ShoppingBag className="w-6 h-6 text-white" />
          </div>
          <Skeleton className="w-32 h-4 rounded" />
        </div>
      </div>
    );
  }

  const quotaPercentage = quota ? (quota.used / quota.limit) * 100 : 0;
  const sidebarProps = { user, quota, pathname, quotaPercentage, logout };

  return (
    <div className="min-h-screen flex bg-background">
      <div className="hidden md:flex w-64 flex-col fixed inset-y-0 border-r border-white/5 bg-card/50 backdrop-blur-xl z-20">
        <SidebarContent {...sidebarProps} />
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed inset-y-0 left-0 w-72 flex flex-col bg-card border-r border-white/5 z-50 md:hidden"
            >
              <div className="absolute right-3 top-4">
                <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)}>
                  <X className="w-5 h-5" />
                </Button>
              </div>
              <SidebarContent {...sidebarProps} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <div className="flex-1 flex flex-col md:pl-64">
        <div className="md:hidden sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/5 bg-background/80 backdrop-blur-xl px-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => setMobileOpen(true)}>
              <Menu className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg gradient-bg flex items-center justify-center">
                <ShoppingBag className="w-4 h-4 text-white" />
              </div>
              <span className="font-semibold text-sm">SellerPulse</span>
            </div>
          </div>
          {quota && (
            <div className="flex items-center gap-2 glass px-3 py-1 rounded-full text-xs">
              <Zap className="w-3 h-3 text-primary" />
              <span className="font-semibold text-primary">{quota.remaining}</span>
              <span className="text-muted-foreground">/ {quota.limit}</span>
            </div>
          )}
        </div>

        <header className="hidden md:flex h-14 items-center justify-end px-8 border-b border-white/5 bg-background/50 backdrop-blur-xl sticky top-0 z-10">
          {quota && (
            <div className="flex items-center gap-3 glass px-4 py-1.5 rounded-full text-sm">
              <Zap className="w-4 h-4 text-primary" />
              <span className="text-muted-foreground">Kalan Kota:</span>
              <span className="font-semibold text-primary">{quota.remaining}</span>
              <span className="text-muted-foreground">/ {quota.limit}</span>
            </div>
          )}
        </header>

        <main className="flex-1 p-4 md:p-8 overflow-x-hidden">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
