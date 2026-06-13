import { Component, signal, Input as RouteInput, inject, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';

interface ArticleData {
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
  seccion_fuente: string | null;
  categoria_principal: string | null;
  contenido_limpio: string | null;
  contenido_html: string | null;
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

@Component({
  selector: 'app-article-detail',
  imports: [RouterLink],
  templateUrl: './article-detail.html',
  styleUrl: './article-detail.scss',
})
export class ArticleDetail {
  @RouteInput() id?: string;
  private http = inject(HttpClient);

  protected readonly article = signal<ArticleData | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal('');

  protected readonly sourceLabel = computed(() => {
    const a = this.article();
    if (!a) return '';
    return SOURCE_LABELS[a.slug_fuente] || a.slug_fuente;
  });

  protected readonly paragraphs = computed(() => {
    const a = this.article();
    if (!a?.contenido_limpio) return [];
    return a.contenido_limpio.split('\n').filter((p) => p.trim().length > 20);
  });

  protected readonly displayDate = computed(() => {
    const d = this.article()?.fecha_publicacion;
    if (!d) return '';
    return new Date(d).toLocaleDateString('es-PE', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  });

  ngOnInit() {
    if (this.id) {
      this.http.get<ArticleData>(`/api/news/${this.id}`).subscribe({
        next: (data) => {
          this.article.set(data);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('No se pudo cargar la noticia.');
          this.loading.set(false);
        },
      });
    }
  }

  protected readonly reactions = { likes: 42, sleep: 3, sad: 8, surprise: 15, interested: 22 };
}
