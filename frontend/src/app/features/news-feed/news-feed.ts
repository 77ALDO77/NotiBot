import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

interface NewsItem {
  id: string;
  category: string;
  headline: string;
  excerpt: string;
  source: string;
  timeAgo: string;
  imageUrl: string;
  reactions: {
    likes: number;
    sleep: number;
    sad: number;
    surprise: number;
    interested: number;
  };
}

@Component({
  selector: 'app-news-feed',
  imports: [RouterLink],
  templateUrl: './news-feed.html',
  styleUrl: './news-feed.scss',
})
export class NewsFeed {
  protected readonly articles = signal<NewsItem[]>([
    {
      id: '1',
      category: 'Política',
      headline: 'Congreso debate reforma del sistema de transporte público en Lima Metropolitana',
      excerpt: 'La Comisión de Transportes evalúa nuevas medidas para descongestionar las principales vías de la capital. Se espera un dictamen en las próximas semanas.',
      source: 'La República',
      timeAgo: '2h',
      imageUrl: '',
      reactions: { likes: 245, sleep: 12, sad: 8, surprise: 34, interested: 89 },
    },
    {
      id: '2',
      category: 'Callao',
      headline: 'Inician obras de ampliación del Aeropuerto Jorge Chávez',
      excerpt: 'El MTC anunció el inicio de la segunda fase de ampliación que duplicará la capacidad operativa del principal terminal aéreo del país.',
      source: 'El Comercio',
      timeAgo: '4h',
      imageUrl: '',
      reactions: { likes: 512, sleep: 3, sad: 5, surprise: 67, interested: 203 },
    },
    {
      id: '3',
      category: 'Seguridad',
      headline: 'Serenazgo de Lima incorpora 200 nuevas unidades de patrullaje',
      excerpt: 'La Municipalidad Metropolitana presentó los nuevos vehículos equipados con tecnología de videovigilancia y conexión directa al centro de control.',
      source: 'Andina',
      timeAgo: '6h',
      imageUrl: '',
      reactions: { likes: 189, sleep: 22, sad: 15, surprise: 41, interested: 56 },
    },
    {
      id: '4',
      category: 'Cultura',
      headline: 'Festival de la Gastronomía Limeña reúne a más de 10,000 visitantes',
      excerpt: 'El Parque de la Exposición se convirtió en el epicentro de la cocina criolla con más de 50 restaurantes participantes y shows en vivo.',
      source: 'RPP',
      timeAgo: '8h',
      imageUrl: '',
      reactions: { likes: 320, sleep: 5, sad: 1, surprise: 28, interested: 145 },
    },
    {
      id: '5',
      category: 'Deportes',
      headline: 'Universitario vs Alianza Lima: clásico del fútbol peruano termina en empate',
      excerpt: 'El Monumental fue el escenario de un partido intenso que mantuvo a los hinchas al borde de sus asientos hasta el pitazo final.',
      source: 'Depor',
      timeAgo: '10h',
      imageUrl: '',
      reactions: { likes: 890, sleep: 2, sad: 45, surprise: 112, interested: 67 },
    },
  ]);

  protected readonly reactions = [
    { key: 'likes' as const, icon: '👍', label: 'Me gusta' },
    { key: 'sleep' as const, icon: '💤', label: 'Aburrido' },
    { key: 'sad' as const, icon: '😢', label: 'Triste' },
    { key: 'surprise' as const, icon: '😲', label: 'Sorprendente' },
    { key: 'interested' as const, icon: '🔔', label: 'Interesado' },
  ];
}
