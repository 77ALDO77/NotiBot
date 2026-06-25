import {Component,signal,ElementRef,viewChild,afterNextRender,inject,effect,} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { DecimalPipe } from '@angular/common';
import { SearchService } from '../../services/search.service';

interface NewsItem {
  id: number;
  titulo: string;
  subtitulo: string | null;
  autor: string | null;
  url_original: string;
  url_imagen: string | null;
  scope_geografico: string;
  provincia: string | null;
  distrito: string | null;
  fecha_publicacion: string | null;
  slug_fuente: string;
  fuente_nombre: string | null;
  seccion_fuente: string | null;
  categoria_principal: string | null;
}

interface NewsResponse {
  items: NewsItem[];
  total: number;
  limit: number;
  offset: number;
}

const SOURCE_LABELS: Record<string, string> = {
  larepublica: 'La República',
  elcomercio: 'El Comercio',
  peru21: 'Peru21',
  correo: 'Correo',
  gestion: 'Gestión',
  trome: 'Trome',
  ojo: 'Ojo',
  larazon: 'La Razón',
};

const CATEGORIES = [
  'Todas', 'Política', 'Sociedad', 'Deportes', 'Economía',
  'Mundo', 'Espectáculos', 'Opinión', 'Nacional', 'Tecnología',
];

function randomReactions() {
  return {
    likes: Math.floor(Math.random() * 50) + 1,
    sleep: Math.floor(Math.random() * 10),
    sad: Math.floor(Math.random() * 8),
    surprise: Math.floor(Math.random() * 20) + 1,
    interested: Math.floor(Math.random() * 30) + 1,
  };
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d`;
  return d.toLocaleDateString('es-PE', { day: 'numeric', month: 'short' });
}

@Component({
  selector: 'app-news-feed',
  imports: [RouterLink, DecimalPipe],
  templateUrl: './news-feed.html',
  styleUrl: './news-feed.scss',
})
export class NewsFeed {
  private http = inject(HttpClient);
  private searchService = inject(SearchService);

  protected readonly articles = signal<(NewsItem & { reactions: ReturnType<typeof randomReactions>; timeAgo: string; sourceLabel: string })[]>([]);
  protected readonly total = signal(0);
  protected readonly loading = signal(false);
  protected readonly hasMore = signal(true);
  protected readonly currentCategory = signal('Todas');
  protected readonly categories = signal(CATEGORIES);

  private offset = 0;
  private readonly pageSize = 10;
  private sentinel = viewChild<ElementRef>('sentinel');

  constructor() {
    // Carga inicial
    afterNextRender(() => this.loadMore());

    // Reacciona a cambios del buscador: resetea el feed y recarga
    effect(() => {
      const _q = this.searchService.query(); // suscripción reactiva
      this.reset();
      // Espera un tick para que el reset se aplique antes de pedir datos
      setTimeout(() => {
        this.loadMore();
        this.setupObserver();
      }, 50);
    });
  }

  ngAfterViewInit() {
    this.setupObserver();
  }

  private setupObserver() {
    const sentinelEl = this.sentinel();
    if (!sentinelEl) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !this.loading() && this.hasMore()) {
          this.loadMore();
        }
      },
      { rootMargin: '200px' }
    );
    observer.observe(sentinelEl.nativeElement);
  }

  selectCategory(cat: string) {
    if (this.loading()) return;
    this.currentCategory.set(cat);
    this.reset();
    setTimeout(() => {
      this.loadMore();
      this.setupObserver();
    }, 50);
  }

  private reset() {
    this.offset = 0;
    this.articles.set([]);
    this.hasMore.set(true);
  }

  private loadMore() {
    if (this.loading() || !this.hasMore()) return;
    this.loading.set(true);

    const params = new URLSearchParams();
    params.set('limit', String(this.pageSize));
    params.set('offset', String(this.offset));

    const cat = this.currentCategory();
    if (cat !== 'Todas') params.set('categoria', cat);

    const q = this.searchService.query();
    if (q) params.set('q', q);  // ← el backend RAG ya tiene GET /api/rag/search?q=

    this.http.get<NewsResponse>(`/api/news?${params}`).subscribe({
      next: (data) => {
        const enriched = data.items.map((item) => ({
          ...item,
          reactions: randomReactions(),
          timeAgo: timeAgo(item.fecha_publicacion),
          sourceLabel: SOURCE_LABELS[item.slug_fuente] || item.fuente_nombre || item.slug_fuente,
        }));
        this.articles.update((prev) => [...prev, ...enriched]);
        this.total.set(data.total);
        this.offset += data.items.length;
        this.hasMore.set(this.offset < data.total);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }
}