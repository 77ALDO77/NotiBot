import { Component, signal, Input as RouteInput } from '@angular/core';
import { RouterLink } from '@angular/router';

interface Comment {
  id: string;
  author: string;
  timeAgo: string;
  content: string;
  replies: Comment[];
}

@Component({
  selector: 'app-article-detail',
  imports: [RouterLink],
  templateUrl: './article-detail.html',
  styleUrl: './article-detail.scss',
})
export class ArticleDetail {
  @RouteInput() id?: string;

  protected readonly article = signal({
    category: 'Política',
    headline: 'Congreso debate reforma del sistema de transporte público en Lima Metropolitana',
    source: 'La República',
    timeAgo: '2h',
    author: 'Carlos Méndez',
    body: `La Comisión de Transportes y Comunicaciones del Congreso de la República inició hoy el debate del proyecto de ley que busca reformar integralmente el sistema de transporte público en Lima Metropolitana y Callao.

La iniciativa, presentada por un grupo multipartidario, propone la creación de una Autoridad Única de Transporte que centralice las decisiones sobre rutas, tarifas y fiscalización de las unidades de transporte.

"Es fundamental ordenar el caos vehicular que afecta a millones de limeños todos los días", señaló el presidente de la comisión durante la sesión matutina.

El proyecto contempla además la implementación de un sistema de pago electrónico unificado, la renovación progresiva de la flota de buses por unidades eléctricas y la ampliación de las ciclovías en toda el área metropolitana.

Representantes de los transportistas expresaron su preocupación por los plazos de implementación, mientras que las organizaciones de usuarios respaldaron la propuesta como "un paso necesario para mejorar la calidad de vida en la capital".

Se espera que el debate continúe la próxima semana con la participación de expertos en movilidad urbana y representantes de municipalidades distritales.`,
    reactions: { likes: 245, sleep: 12, sad: 8, surprise: 34, interested: 89 },
  });

  protected readonly comments = signal<Comment[]>([
    {
      id: 'c1',
      author: 'María Gutiérrez',
      timeAgo: '1h',
      content: 'Ojalá esta vez sea en serio. Llevamos años esperando una reforma real del transporte.',
      replies: [
        {
          id: 'c1r1',
          author: 'Pedro Castillo',
          timeAgo: '45m',
          content: 'Totalmente de acuerdo. La ATU actual no tiene verdaderas facultades.',
          replies: [],
        },
      ],
    },
    {
      id: 'c2',
      author: 'Luis Ramírez',
      timeAgo: '30m',
      content: 'Lo importante es que incluyan a los transportistas en el debate. Sin ellos, ninguna reforma funciona.',
      replies: [],
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
