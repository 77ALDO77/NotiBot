import { Routes } from '@angular/router';
import { AdminGuard } from './services/admin.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/news-feed/news-feed').then(m => m.NewsFeed),
  },
  {
    path: 'article/:id',
    loadComponent: () => import('./features/article-detail/article-detail').then(m => m.ArticleDetail),
  },
  {
    path: 'chat',
    loadComponent: () => import('./features/ai-chat/ai-chat').then(m => m.AiChat),
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login').then(m => m.Login),
  },
  {
    path: 'admin',
    loadComponent: () => import('./features/admin/admin').then(m => m.AdminComponent),
    canActivate: [AdminGuard],
  },
  {
    path: 'admin/analytics',
    loadComponent: () => import('./features/admin-analytics/admin-analytics').then(m => m.AdminAnalyticsComponent),
    canActivate: [AdminGuard],
  },
  {
    path: '**',
    redirectTo: '',
  },
];
