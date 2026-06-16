import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { DecimalPipe, TitleCasePipe } from '@angular/common';

interface ScopeItem { scope: string; count: number }
interface SectionItem { seccion: string | null; count: number }
interface ProvinciaItem { provincia: string | null; count: number }
interface CategoriaItem { categoria: string | null; count: number }
interface DistritoItem { distrito: string | null; count: number }

interface OverviewResponse {
  total_articles: number;
  total_unique: number;
  total_duplicates: number;
  duplicate_pct: number;
  by_scope: ScopeItem[];
  by_seccion: SectionItem[];
  by_provincia: ProvinciaItem[];
  by_categoria: CategoriaItem[];
  by_distrito_top15: DistritoItem[];
}

interface LengthStat {
  mean: number | null;
  min: number | null;
  max: number | null;
  std: number | null;
  median: number | null;
  mean_words: number | null;
  total_rows: number;
}

interface LengthsResponse {
  titulo: LengthStat;
  subtitulo: LengthStat;
  contenido: LengthStat;
}

interface WordFreqItem { word: string; count: number; pct: number }
interface WordFrequencyResponse {
  scope: string;
  top: number;
  total_articles: number;
  words: WordFreqItem[];
}

interface SectionWordFreq {
  seccion: string | null;
  total_articles: number;
  words: WordFreqItem[];
}

interface SectionWordFrequencyResponse {
  scope: string;
  top: number;
  sections: SectionWordFreq[];
}

type TabId = 'overview' | 'lengths' | 'words' | 'by-section';

@Component({
  selector: 'app-admin-analytics',
  standalone: true,
  imports: [RouterLink, DecimalPipe, TitleCasePipe],
  template: `
    <div class="analytics">
      <header class="analytics__header">
        <div class="analytics__brand">
          <a routerLink="/admin" class="analytics__back">&larr; Admin</a>
          <h1>Analytics</h1>
        </div>
      </header>

      <nav class="analytics__nav">
        @for (tab of tabs; track tab.id) {
          <button
            class="analytics__tab"
            [class.analytics__tab--active]="activeTab() === tab.id"
            (click)="onTabChange(tab.id)"
          >{{ tab.label }}</button>
        }
      </nav>

      @switch (activeTab()) {
        @case ('overview') {
          <section class="analytics__section">
            <div class="stats-grid">
              <div class="stat-card">
                <span class="stat-card__value">{{ overview().total_articles | number }}</span>
                <span class="stat-card__label">Total</span>
              </div>
              <div class="stat-card">
                <span class="stat-card__value">{{ overview().total_unique | number }}</span>
                <span class="stat-card__label">Únicos</span>
              </div>
              <div class="stat-card">
                <span class="stat-card__value">{{ overview().total_duplicates | number }}</span>
                <span class="stat-card__label">Duplicados</span>
              </div>
              <div class="stat-card">
                <span class="stat-card__value">{{ overview().duplicate_pct }}%</span>
                <span class="stat-card__label">% Duplicados</span>
              </div>
            </div>

            <div class="charts-row">
              <div class="card card--half">
                <h3 class="card__title">Por Alcance</h3>
                <div class="bar-chart" id="chart-scope"></div>
                <div class="bar-chart-legend">
                  @for (item of overview().by_scope; track item.scope) {
                    <div class="bar-chart-legend__item">
                      <span class="bar-chart-legend__label">{{ item.scope | titlecase }}</span>
                      <span class="bar-chart-legend__count">{{ item.count | number }}</span>
                    </div>
                  }
                </div>
              </div>

              <div class="card card--half">
                <h3 class="card__title">Por Provincia</h3>
                <div class="bar-chart" id="chart-provincia"></div>
              </div>
            </div>

            <div class="charts-row">
              <div class="card card--half">
                <h3 class="card__title">Por Sección (top 15)</h3>
                <div class="bar-chart" id="chart-seccion"></div>
              </div>

              <div class="card card--half">
                <h3 class="card__title">Por Categoría</h3>
                <div class="bar-chart" id="chart-categoria"></div>
              </div>
            </div>

            <div class="card">
              <h3 class="card__title">Top 15 Distritos</h3>
              <div class="bar-chart bar-chart--tall" id="chart-distrito"></div>
            </div>
          </section>
        }

        @case ('lengths') {
          <section class="analytics__section">
            <div class="lengths-grid">
              <div class="card">
                <h3 class="card__title">Títulos</h3>
                <div class="length-stats">
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().titulo.mean) }}</span><span class="length-stat__lbl">Media (chars)</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().titulo.median) }}</span><span class="length-stat__lbl">Mediana (chars)</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().titulo.min) }}</span><span class="length-stat__lbl">Mín</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().titulo.max) }}</span><span class="length-stat__lbl">Máx</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().titulo.std) }}</span><span class="length-stat__lbl">Desv Est</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().titulo.mean_words) }}</span><span class="length-stat__lbl">Palabras (media)</span></div>
                </div>
                <span class="length-total">{{ lengths().titulo.total_rows | number }} artículos</span>
              </div>

              <div class="card">
                <h3 class="card__title">Subtítulos</h3>
                <div class="length-stats">
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().subtitulo.mean) }}</span><span class="length-stat__lbl">Media (chars)</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().subtitulo.median) }}</span><span class="length-stat__lbl">Mediana (chars)</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().subtitulo.min) }}</span><span class="length-stat__lbl">Mín</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().subtitulo.max) }}</span><span class="length-stat__lbl">Máx</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().subtitulo.std) }}</span><span class="length-stat__lbl">Desv Est</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().subtitulo.mean_words) }}</span><span class="length-stat__lbl">Palabras (media)</span></div>
                </div>
                <span class="length-total">{{ lengths().subtitulo.total_rows | number }} artículos</span>
              </div>

              <div class="card">
                <h3 class="card__title">Contenido</h3>
                <div class="length-stats">
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().contenido.mean) }}</span><span class="length-stat__lbl">Media (chars)</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().contenido.median) }}</span><span class="length-stat__lbl">Mediana (chars)</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().contenido.min) }}</span><span class="length-stat__lbl">Mín</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().contenido.max) }}</span><span class="length-stat__lbl">Máx</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().contenido.std) }}</span><span class="length-stat__lbl">Desv Est</span></div>
                  <div class="length-stat"><span class="length-stat__val">{{ fmtNum(lengths().contenido.mean_words) }}</span><span class="length-stat__lbl">Palabras (media)</span></div>
                </div>
                <span class="length-total">{{ lengths().contenido.total_rows | number }} artículos</span>
              </div>
            </div>
          </section>
        }

        @case ('words') {
          <section class="analytics__section">
            <div class="card">
              <div class="filters">
                <select [value]="wordScope()" (change)="onWordScopeChange($any($event.target).value)" class="select">
                  <option value="all">Títulos + Subtítulos</option>
                  <option value="titulos">Solo Títulos</option>
                  <option value="subtitulos">Solo Subtítulos</option>
                </select>
                <select [value]="wordTop()" (change)="onWordTopChange(+$any($event.target).value)" class="select">
                  <option value="10">Top 10</option>
                  <option value="20">Top 20</option>
                  <option value="50">Top 50</option>
                  <option value="100">Top 100</option>
                </select>
                <span class="filters__total">{{ wordFreq().total_articles | number }} artículos</span>
              </div>
            </div>

            <div class="card">
              <div class="bar-chart bar-chart--tall" id="chart-words"></div>
            </div>

            <div class="card">
              <h3 class="card__title">Top {{ wordFreq().top }} palabras</h3>
              <div class="word-grid">
                @for (w of wordFreq().words; track w.word) {
                  <div class="word-item">
                    <span class="word-item__rank">{{ $index + 1 }}</span>
                    <span class="word-item__word">{{ w.word }}</span>
                    <span class="word-item__count">{{ w.count | number }}</span>
                    <span class="word-item__pct">{{ w.pct }}%</span>
                  </div>
                }
              </div>
            </div>
          </section>
        }

        @case ('by-section') {
          <section class="analytics__section">
            <div class="card">
              <div class="filters">
                <select [value]="sectionScope()" (change)="onSectionChange($any($event.target).value)" class="select">
                  @for (s of bySection().sections; track s.seccion) {
                    <option [value]="s.seccion">{{ s.seccion || 'Sin sección' }} ({{ s.total_articles | number }})</option>
                  }
                </select>
                <select [value]="sectionTop()" (change)="onSectionTopChange(+$any($event.target).value)" class="select">
                  <option value="10">Top 10</option>
                  <option value="20">Top 20</option>
                  <option value="50">Top 50</option>
                </select>
                @if (selectedSection()) {
                  <span class="filters__total">{{ selectedSection()!.total_articles | number }} artículos</span>
                }
              </div>
            </div>

            @if (selectedSection()) {
              <div class="card">
                <div class="bar-chart bar-chart--tall" id="chart-section-words"></div>
              </div>

              <div class="card">
                <h3 class="card__title">{{ selectedSection()!.seccion || 'Sin sección' }} — Top {{ sectionTop() }} palabras</h3>
                <div class="word-grid">
                  @for (w of selectedSection()!.words; track w.word) {
                    <div class="word-item">
                      <span class="word-item__rank">{{ $index + 1 }}</span>
                      <span class="word-item__word">{{ w.word }}</span>
                      <span class="word-item__count">{{ w.count | number }}</span>
                      <span class="word-item__pct">{{ w.pct }}%</span>
                    </div>
                  }
                </div>
              </div>
            }
          </section>
        }
      }
    </div>
  `,
  styles: [`
    :host {
      --brand: #1E1B4B;
      --cta: #84CC16;
      --ai: #0EA5E9;
      --bg: #f5f5f7;
      --card: #fff;
      --border: #e5e7eb;
      --text: #1f2937;
      --text2: #6b7280;
      display: block;
      min-height: 100vh;
      background: var(--bg);
      font-family: 'Manrope', sans-serif;
      color: var(--text);
    }

    .analytics { max-width: 1120px; margin: 0 auto; padding: 0 20px 40px; }

    .analytics__header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 20px 0 12px; border-bottom: 1px solid var(--border); margin-bottom: 16px;
    }
    .analytics__brand { display: flex; align-items: center; gap: 16px; }
    .analytics__brand h1 { margin: 0; font-family: 'Newsreader', serif; font-size: 22px; color: var(--brand); }
    .analytics__back {
      color: var(--text2); text-decoration: none; font-size: 14px; padding: 4px 12px;
      border: 1px solid var(--border); border-radius: 6px; transition: all .15s;
    }
    .analytics__back:hover { color: var(--brand); border-color: var(--brand); }

    .analytics__nav { display: flex; gap: 0; margin-bottom: 24px; border-bottom: 2px solid var(--border); }
    .analytics__tab {
      background: none; border: none; padding: 10px 24px; font-size: 14px; font-weight: 500;
      color: var(--text2); cursor: pointer; border-bottom: 2px solid transparent;
      margin-bottom: -2px; transition: all .15s;
    }
    .analytics__tab:hover { color: var(--brand); }
    .analytics__tab--active { color: var(--brand); border-bottom-color: var(--brand); }

    .analytics__section { }

    .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
    .stat-card {
      background: var(--card); padding: 20px; border-radius: 12px; text-align: center;
      box-shadow: 0 1px 3px rgba(0,0,0,.04);
    }
    .stat-card__value { display: block; font-size: 34px; font-weight: 700; color: var(--brand); }
    .stat-card__label { font-size: 13px; color: var(--text2); margin-top: 4px; }

    .charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }

    .card {
      background: var(--card); padding: 20px; border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,.04); margin-bottom: 16px;
    }
    .card--half { margin-bottom: 0; }
    .card__title { margin: 0 0 12px; font-size: 15px; font-weight: 600; color: var(--text); }

    .bar-chart { min-height: 160px; }
    .bar-chart--tall { min-height: 300px; }
    .bar-chart svg { display: block; }

    .bar-chart-legend { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px 16px; }
    .bar-chart-legend__item { display: flex; align-items: center; gap: 6px; font-size: 12px; }
    .bar-chart-legend__label { color: var(--text2); text-transform: capitalize; }
    .bar-chart-legend__count { font-weight: 600; color: var(--text); }

    .lengths-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
    .length-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }
    .length-stat { text-align: center; }
    .length-stat__val { display: block; font-size: 22px; font-weight: 700; color: var(--brand); }
    .length-stat__lbl { font-size: 11px; color: var(--text2); margin-top: 2px; }
    .length-total { font-size: 12px; color: var(--text2); font-weight: 500; }

    .filters { display: flex; align-items: center; gap: 12px; }
    .select {
      padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px;
      font-size: 13px; font-family: inherit; background: #fff; color: var(--text);
    }
    .filters__total { font-size: 13px; color: var(--text2); margin-left: auto; }

    .word-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 4px; }
    .word-item {
      display: flex; align-items: center; gap: 10px; padding: 6px 10px;
      border-radius: 6px; transition: background .1s;
    }
    .word-item:hover { background: #f3f4f6; }
    .word-item__rank { font-size: 11px; color: var(--text2); font-weight: 600; width: 22px; text-align: right; }
    .word-item__word { font-size: 13px; font-weight: 500; flex: 1; }
    .word-item__count { font-size: 12px; color: var(--brand); font-weight: 600; min-width: 40px; text-align: right; }
    .word-item__pct { font-size: 11px; color: var(--text2); min-width: 45px; text-align: right; }
  `],
})
export class AdminAnalyticsComponent implements OnInit {
  private readonly apiUrl = '/api/admin/analytics';

  readonly tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'lengths', label: 'Longitudes' },
    { id: 'words', label: 'Palabras' },
    { id: 'by-section', label: 'Por Sección' },
  ];

  activeTab = signal<TabId>('overview');

  overview = signal<OverviewResponse>({
    total_articles: 0, total_unique: 0, total_duplicates: 0, duplicate_pct: 0,
    by_scope: [], by_seccion: [], by_provincia: [], by_categoria: [], by_distrito_top15: [],
  });

  lengths = signal<LengthsResponse>({
    titulo: { mean: 0, min: 0, max: 0, std: 0, median: 0, mean_words: 0, total_rows: 0 },
    subtitulo: { mean: 0, min: 0, max: 0, std: 0, median: 0, mean_words: 0, total_rows: 0 },
    contenido: { mean: 0, min: 0, max: 0, std: 0, median: 0, mean_words: 0, total_rows: 0 },
  });

  wordScope = signal('all');
  wordTop = signal(50);
  wordFreq = signal<WordFrequencyResponse>({ scope: 'all', top: 50, total_articles: 0, words: [] });

  bySection = signal<SectionWordFrequencyResponse>({ scope: 'by_section', top: 50, sections: [] });
  sectionScope = signal('');
  sectionTop = signal(50);
  sectionLoading = signal(false);

  selectedSection = signal<SectionWordFreq | null>(null);

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadOverview();
  }

  fmtNum(v: number | null | undefined): string {
    if (v == null) return '-';
    return v % 1 === 0 ? String(v) : v.toFixed(1);
  }

  onTabChange(tab: TabId) {
    this.activeTab.set(tab);
    if (tab === 'overview' && !this.overview().total_articles) this.loadOverview();
    if (tab === 'lengths' && !this.lengths().titulo.total_rows) this.loadLengths();
    if (tab === 'words' && !this.wordFreq().words.length) this.loadWordFreq();
    if (tab === 'by-section' && !this.bySection().sections.length) this.loadBySection();
  }

  onWordScopeChange(scope: string) {
    this.wordScope.set(scope);
    this.loadWordFreq();
  }

  onWordTopChange(top: number) {
    this.wordTop.set(top);
    this.loadWordFreq();
  }

  onSectionChange(seccion: string) {
    this.sectionScope.set(seccion);
    this.updateSelectedSection();
  }

  onSectionTopChange(top: number) {
    this.sectionTop.set(top);
    this.loadBySection();
  }

  private updateSelectedSection() {
    const sec = this.sectionScope();
    const found = this.bySection().sections.find(s => s.seccion === sec) || null;
    this.selectedSection.set(found);
    if (found) setTimeout(() => this.renderHorizontalBars('chart-section-words', found.words, '#84CC16'), 50);
  }

  loadOverview() {
    this.http.get<OverviewResponse>(`${this.apiUrl}/overview`).subscribe(data => {
      this.overview.set(data);
      setTimeout(() => {
        this.renderHorizontalBars('chart-scope', data.by_scope.map(s => ({ word: s.scope, count: s.count, pct: 0 })), '#0EA5E9');
        this.renderHorizontalBars('chart-provincia', data.by_provincia.map(p => ({ word: p.provincia || 'Sin provincia', count: p.count, pct: 0 })), '#8b5cf6');
        this.renderHorizontalBars('chart-seccion', data.by_seccion.slice(0, 15).map(s => ({ word: s.seccion || 'Sin sección', count: s.count, pct: 0 })), '#3b82f6');
        this.renderHorizontalBars('chart-categoria', data.by_categoria.map(c => ({ word: c.categoria || 'Sin categoría', count: c.count, pct: 0 })), '#f59e0b');
        this.renderHorizontalBars('chart-distrito', data.by_distrito_top15.map(d => ({ word: d.distrito || 'Sin distrito', count: d.count, pct: 0 })), '#22c55e');
      }, 50);
    });
  }

  loadLengths() {
    this.http.get<LengthsResponse>(`${this.apiUrl}/lengths`).subscribe(data => this.lengths.set(data));
  }

  loadWordFreq() {
    this.http.get<WordFrequencyResponse>(
      `${this.apiUrl}/word-frequency?scope=${this.wordScope()}&top=${this.wordTop()}`
    ).subscribe(data => {
      this.wordFreq.set(data);
      setTimeout(() => this.renderHorizontalBars('chart-words', data.words, '#84CC16'), 50);
    });
  }

  loadBySection() {
    this.http.get<SectionWordFrequencyResponse>(
      `${this.apiUrl}/word-frequency/by-section?top=${this.sectionTop()}`
    ).subscribe(data => {
      this.bySection.set(data);
      if (data.sections.length && !this.sectionScope()) {
        this.sectionScope.set(data.sections[0].seccion || '');
      }
      this.updateSelectedSection();
    });
  }

  private async renderHorizontalBars(containerId: string, data: { word: string; count: number }[], color: string) {
    const el = document.getElementById(containerId);
    if (!el || !data.length) return;

    try {
      const d3 = await import('d3');
      el.innerHTML = '';

      const margin = { top: 0, right: 20, bottom: 0, left: 120 };
      const barHeight = containerId === 'chart-words' || containerId === 'chart-section-words' ? 24 : 26;
      const height = Math.max(data.length * barHeight + 4, 160);
      const width = el.clientWidth || 500;
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      const maxVal = d3.max(data, d => d.count) || 1;
      const x = d3.scaleLinear().domain([0, maxVal]).range([0, innerWidth]);
      const y = d3.scaleBand().domain(data.map(d => d.word)).range([0, innerHeight]).padding(0.15);

      g.selectAll('rect')
        .data(data)
        .join('rect')
        .attr('y', d => y(d.word)!)
        .attr('height', y.bandwidth())
        .attr('x', 0)
        .attr('width', d => x(d.count))
        .attr('rx', 3)
        .attr('fill', color)
        .attr('opacity', 0.85);

      g.selectAll('text.label')
        .data(data)
        .join('text')
        .attr('class', 'label')
        .attr('y', d => y(d.word)! + y.bandwidth() / 2)
        .attr('x', -6)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .attr('font-size', '12px')
        .attr('font-family', 'Manrope, sans-serif')
        .attr('fill', '#374151')
        .text(d => d.word.length > 20 ? d.word.slice(0, 18) + '…' : d.word);

      g.selectAll('text.value')
        .data(data)
        .join('text')
        .attr('class', 'value')
        .attr('y', d => y(d.word)! + y.bandwidth() / 2)
        .attr('x', d => x(d.count) + 6)
        .attr('dy', '0.35em')
        .attr('font-size', '11px')
        .attr('font-family', 'Manrope, sans-serif')
        .attr('fill', '#6b7280')
        .attr('font-weight', '500')
        .text(d => d.count.toLocaleString());

    } catch (e) {
      console.error('[Analytics] D3 render error:', e);
    }
  }
}
