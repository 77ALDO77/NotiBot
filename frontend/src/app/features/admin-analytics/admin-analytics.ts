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

interface LengthsData {
  title_len: number;
  title_words: number;
  subtitle_len: number | null;
  content_len: number | null;
  seccion: string | null;
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

type TabId = 'overview' | 'lengths' | 'words' | 'by-section' | 'wordcloud';

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

            <div class="charts-row--three">
              <div class="card">
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

              <div class="card">
                <h3 class="card__title">Por Provincia</h3>
                <div class="bar-chart" id="chart-provincia"></div>
              </div>

              <div class="card">
                <h3 class="card__title">Únicos vs Duplicados</h3>
                <div class="pie-chart" id="chart-uniques-pie"></div>
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

            @if (lengthsLoading()) {
              <div style="text-align: center; padding: 40px; color: var(--text2); font-size: 14px;">Cargando gráficos estadísticos de longitudes...</div>
            }

            <div [style.display]="lengthsLoading() ? 'none' : 'block'">
              <div class="charts-row--three">
                <div class="card">
                  <h3 class="card__title">Distribución de Longitud de Títulos</h3>
                  <div class="bar-chart" id="chart-hist-title-char"></div>
                </div>
                <div class="card">
                  <h3 class="card__title">Distribución de Longitud de Subtítulos</h3>
                  <div class="bar-chart" id="chart-hist-subtitle-char"></div>
                </div>
                <div class="card">
                  <h3 class="card__title">Palabras por Título</h3>
                  <div class="bar-chart" id="chart-hist-title-words"></div>
                </div>
              </div>

              <div class="charts-row">
                <div class="card card--half">
                  <h3 class="card__title">Box Plot de Longitudes (Caracteres)</h3>
                  <div class="bar-chart bar-chart--tall" id="chart-box-lengths"></div>
                </div>
                <div class="card card--half">
                  <h3 class="card__title">Palabras por Título (Top 5 Secciones)</h3>
                  <div class="bar-chart bar-chart--tall" id="chart-box-sections"></div>
                </div>
              </div>

              <div class="card">
                <h3 class="card__title">Relación: Palabras vs Caracteres (Títulos)</h3>
                <div class="bar-chart bar-chart--tall" id="chart-scatter-title"></div>
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

            <div class="charts-row">
              <div class="card card--half">
                <h3 class="card__title">Top {{ wordFreq().top }} palabras</h3>
                <div class="bar-chart bar-chart--tall" id="chart-words"></div>
              </div>
              <div class="card card--half">
                <h3 class="card__title">Distribución de Frecuencias (Log-Log)</h3>
                <div class="bar-chart bar-chart--tall" id="chart-words-loglog"></div>
              </div>
            </div>

            <div class="card">
              <h3 class="card__title">Listado de palabras más comunes</h3>
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

        @case ('wordcloud') {
          <section class="analytics__section">
            <div class="card">
              <div class="filters">
                <select [value]="wordcloudScope()" (change)="onWordcloudScopeChange($any($event.target).value)" class="select">
                  <option value="all">Títulos + Subtítulos</option>
                  <option value="titulos">Solo Títulos</option>
                  <option value="subtitulos">Solo Subtítulos</option>
                  <option value="seccion">Por Sección</option>
                </select>
                <select [value]="wordcloudTop()" (change)="onWordcloudTopChange(+$any($event.target).value)" class="select">
                  <option value="30">30 palabras</option>
                  <option value="50">50 palabras</option>
                  <option value="80">80 palabras</option>
                  <option value="120">120 palabras</option>
                </select>
                @if (wordcloudScope() === 'seccion') {
                  <select [value]="wordcloudSection()" (change)="onWordcloudSectionChange($any($event.target).value)" class="select">
                    @for (s of bySection().sections; track s.seccion) {
                      <option [value]="s.seccion">{{ s.seccion || 'Sin sección' }}</option>
                    }
                  </select>
                }
                @if (wordcloudLoading()) {
                  <span style="font-size: 13px; color: var(--text2); margin-left: 12px;">Cargando palabras...</span>
                }
              </div>
            </div>

            <div class="card" style="text-align: center;">
              <h3 class="card__title">Nube de Palabras — {{ wordcloudTitle() }}</h3>
              <div id="chart-wordcloud" style="min-height: 450px; background: #fff; border-radius: 8px;"></div>
            </div>
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

    .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
    .stat-card {
      background: var(--card); padding: 20px; border-radius: 12px; text-align: center;
      box-shadow: 0 1px 3px rgba(0,0,0,.04);
    }
    .stat-card__value { display: block; font-size: 34px; font-weight: 700; color: var(--brand); }
    .stat-card__label { font-size: 13px; color: var(--text2); margin-top: 4px; }

    .charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
    .charts-row--three { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }

    .card {
      background: var(--card); padding: 20px; border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,.04); margin-bottom: 16px;
    }
    .card--half { margin-bottom: 0; }
    .card__title { margin: 0 0 12px; font-size: 15px; font-weight: 600; color: var(--text); }

    .bar-chart { min-height: 160px; }
    .bar-chart--tall { min-height: 300px; }
    .bar-chart svg { display: block; }
    .pie-chart { min-height: 180px; display: flex; align-items: center; justify-content: center; }

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

    @media (max-width: 768px) {
      .stats-grid { grid-template-columns: 1fr 1fr; }
      .charts-row, .charts-row--three { grid-template-columns: 1fr; }
      .lengths-grid { grid-template-columns: 1fr; }
    }
  `],
})
export class AdminAnalyticsComponent implements OnInit {
  private readonly apiUrl = '/api/admin/analytics';

  readonly tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'lengths', label: 'Longitudes' },
    { id: 'words', label: 'Palabras' },
    { id: 'by-section', label: 'Por Sección' },
    { id: 'wordcloud', label: 'Nube de Palabras' },
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

  lengthsData = signal<LengthsData[]>([]);
  lengthsLoading = signal(false);

  wordScope = signal('all');
  wordTop = signal(50);
  wordFreq = signal<WordFrequencyResponse>({ scope: 'all', top: 50, total_articles: 0, words: [] });

  bySection = signal<SectionWordFrequencyResponse>({ scope: 'by_section', top: 50, sections: [] });
  sectionScope = signal('');
  sectionTop = signal(50);
  sectionLoading = signal(false);

  selectedSection = signal<SectionWordFreq | null>(null);

  wordcloudScope = signal('all');
  wordcloudTop = signal(50);
  wordcloudSection = signal('');
  wordcloudData = signal<WordFreqItem[]>([]);
  wordcloudLoading = signal(false);

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
    if (tab === 'overview') {
      if (!this.overview().total_articles) {
        this.loadOverview();
      } else {
        setTimeout(() => this.renderOverviewCharts(), 50);
      }
    }
    if (tab === 'lengths') {
      if (!this.lengths().titulo.total_rows) {
        this.loadLengths();
      } else {
        setTimeout(() => this.renderLengthsCharts(), 50);
      }
    }
    if (tab === 'words') {
      if (!this.wordFreq().words.length) {
        this.loadWordFreq();
      } else {
        setTimeout(() => {
          this.renderHorizontalBars('chart-words', this.wordFreq().words, '#84CC16');
          this.renderLogLogChart('chart-words-loglog', this.wordFreq().words);
        }, 50);
      }
    }
    if (tab === 'by-section') {
      if (!this.bySection().sections.length) {
        this.loadBySection();
      } else {
        setTimeout(() => this.updateSelectedSection(), 50);
      }
    }
    if (tab === 'wordcloud') {
      if (!this.bySection().sections.length) {
        this.http.get<SectionWordFrequencyResponse>(
          `${this.apiUrl}/word-frequency/by-section?top=${this.wordcloudTop()}`
        ).subscribe(data => {
          this.bySection.set(data);
          if (data.sections.length && !this.wordcloudSection()) {
            this.wordcloudSection.set(data.sections[0].seccion || '');
          }
          this.loadWordcloudData();
        });
      } else {
        if (this.bySection().sections.length && !this.wordcloudSection()) {
          this.wordcloudSection.set(this.bySection().sections[0].seccion || '');
        }
        this.loadWordcloudData();
      }
    }
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
      setTimeout(() => this.renderOverviewCharts(), 50);
    });
  }

  private renderOverviewCharts() {
    const data = this.overview();
    if (!data.total_articles) return;

    this.renderHorizontalBars('chart-scope', data.by_scope.map(s => ({ word: s.scope, count: s.count, pct: 0 })), '#0EA5E9');
    this.renderHorizontalBars('chart-provincia', data.by_provincia.map(p => ({ word: p.provincia || 'Sin provincia', count: p.count, pct: 0 })), '#8b5cf6');
    this.renderHorizontalBars('chart-seccion', data.by_seccion.slice(0, 15).map(s => ({ word: s.seccion || 'Sin sección', count: s.count, pct: 0 })), '#3b82f6');
    this.renderHorizontalBars('chart-categoria', data.by_categoria.map(c => ({ word: c.categoria || 'Sin categoría', count: c.count, pct: 0 })), '#f59e0b');
    this.renderHorizontalBars('chart-distrito', data.by_distrito_top15.map(d => ({ word: d.distrito || 'Sin distrito', count: d.count, pct: 0 })), '#22c55e');
    this.renderUniquesPie('chart-uniques-pie', data.total_unique, data.total_duplicates);
  }

  loadLengths() {
    this.lengthsLoading.set(true);
    this.http.get<LengthsResponse>(`${this.apiUrl}/lengths`).subscribe(data => {
      this.lengths.set(data);
    });
    this.http.get<LengthsData[]>(`${this.apiUrl}/lengths-data`).subscribe({
      next: (data) => {
        this.lengthsData.set(data);
        this.lengthsLoading.set(false);
        setTimeout(() => this.renderLengthsCharts(), 50);
      },
      error: () => {
        this.lengthsLoading.set(false);
      }
    });
  }

  private renderLengthsCharts() {
    const stats = this.lengths();
    const raw = this.lengthsData();
    if (!raw.length) return;

    // 1. Histogram of title lengths (characters)
    const titleChars = raw.map(d => d.title_len);
    this.renderHistogram('chart-hist-title-char', titleChars, '#0EA5E9', 'Caracteres de Título', stats.titulo.mean || 0);

    // 2. Histogram of subtitle lengths (characters)
    const subtitleChars = raw.filter(d => d.subtitle_len !== null && d.subtitle_len > 0).map(d => d.subtitle_len as number);
    this.renderHistogram('chart-hist-subtitle-char', subtitleChars, '#f59e0b', 'Caracteres de Subtítulo', stats.subtitulo.mean || 0);

    // 3. Histogram of title word counts
    const titleWords = raw.map(d => d.title_words);
    this.renderHistogram('chart-hist-title-words', titleWords, '#22c55e', 'Palabras por Título', stats.titulo.mean_words || 0);

    // 4. Box Plot comparing Title, Subtitle, and Content lengths
    const subtitleLens = raw.filter(d => d.subtitle_len !== null && d.subtitle_len > 0).map(d => d.subtitle_len as number);
    const contentLens = raw.filter(d => d.content_len !== null && d.content_len > 0).map(d => d.content_len as number);
    this.renderBoxPlot('chart-box-lengths', [
      { label: 'Títulos', values: titleChars },
      { label: 'Subtítulos', values: subtitleLens },
      { label: 'Contenido', values: contentLens }
    ], '#8b5cf6', 'Caracteres');

    // 5. Box Plot of Words per Title grouped by Top 5 Sections
    const sectionCounts = raw.reduce((acc, curr) => {
      const sec = curr.seccion || 'Sin sección';
      acc[sec] = (acc[sec] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const top5Sections = Object.entries(sectionCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(entry => entry[0]);

    const boxPlotSections = top5Sections.map(sec => {
      const values = raw.filter(d => (d.seccion || 'Sin sección') === sec).map(d => d.title_words);
      return { label: sec, values };
    });
    this.renderBoxPlot('chart-box-sections', boxPlotSections, '#84CC16', 'Palabras por Título');

    // 6. Scatter Plot of Words vs Characters in Titles
    const scatterData = raw.map(d => ({ x: d.title_words, y: d.title_len }));
    this.renderScatterPlot('chart-scatter-title', scatterData, '#3b82f6', 'Número de palabras', 'Caracteres');
  }

  loadWordFreq() {
    this.http.get<WordFrequencyResponse>(
      `${this.apiUrl}/word-frequency?scope=${this.wordScope()}&top=${this.wordTop()}`
    ).subscribe(data => {
      this.wordFreq.set(data);
      setTimeout(() => {
        this.renderHorizontalBars('chart-words', data.words, '#84CC16');
        this.renderLogLogChart('chart-words-loglog', data.words);
      }, 50);
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

  onWordcloudScopeChange(scope: string) {
    this.wordcloudScope.set(scope);
    this.loadWordcloudData();
  }

  onWordcloudTopChange(top: number) {
    this.wordcloudTop.set(top);
    this.loadWordcloudData();
  }

  onWordcloudSectionChange(section: string) {
    this.wordcloudSection.set(section);
    this.loadWordcloudData();
  }

  wordcloudTitle(): string {
    const scope = this.wordcloudScope();
    const top = this.wordcloudTop();
    if (scope === 'titulos') return `Top ${top} Palabras en Títulos`;
    if (scope === 'subtitulos') return `Top ${top} Palabras en Subtítulos`;
    if (scope === 'seccion') return `Top ${top} Palabras en Sección: ${this.wordcloudSection() || 'Selecciona una sección'}`;
    return `Top ${top} Palabras (Títulos + Subtítulos)`;
  }

  loadWordcloudData() {
    const scope = this.wordcloudScope();
    const top = this.wordcloudTop();

    this.wordcloudLoading.set(true);

    if (scope === 'seccion') {
      const sec = this.wordcloudSection();
      const found = this.bySection().sections.find(s => s.seccion === sec);
      if (found) {
        this.wordcloudData.set(found.words.slice(0, top));
        this.wordcloudLoading.set(false);
        setTimeout(() => this.renderWordcloud(), 50);
      } else {
        this.http.get<SectionWordFrequencyResponse>(
          `${this.apiUrl}/word-frequency/by-section?top=${top}`
        ).subscribe({
          next: (data) => {
            this.bySection.set(data);
            const found2 = data.sections.find(s => s.seccion === sec);
            this.wordcloudData.set(found2 ? found2.words.slice(0, top) : []);
            this.wordcloudLoading.set(false);
            setTimeout(() => this.renderWordcloud(), 50);
          },
          error: () => {
            this.wordcloudLoading.set(false);
          }
        });
      }
    } else {
      this.http.get<WordFrequencyResponse>(
        `${this.apiUrl}/word-frequency?scope=${scope}&top=${top}`
      ).subscribe({
        next: (data) => {
          this.wordcloudData.set(data.words);
          this.wordcloudLoading.set(false);
          setTimeout(() => this.renderWordcloud(), 50);
        },
        error: () => {
          this.wordcloudLoading.set(false);
        }
      });
    }
  }


  private async renderUniquesPie(containerId: string, unique: number, duplicate: number) {
    const el = document.getElementById(containerId);
    if (!el) return;

    try {
      const d3 = await import('d3');
      el.innerHTML = '';

      const width = el.clientWidth || 300;
      const height = 180;
      const radius = Math.min(width, height) / 2 - 10;

      const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width / 2},${height / 2})`);

      const data = [
        { label: 'Únicos', value: unique, color: '#2ecc71' },
        { label: 'Duplicados', value: duplicate, color: '#e74c3c' }
      ];

      const pie = d3.pie<{ label: string; value: number; color: string }>()
        .value(d => d.value)
        .sort(null);

      const arc = d3.arc<d3.PieArcDatum<{ label: string; value: number; color: string }>>()
        .innerRadius(0)
        .outerRadius(radius);

      const arcs = svg.selectAll('.arc')
        .data(pie(data))
        .enter()
        .append('g')
        .attr('class', 'arc');

      arcs.append('path')
        .attr('d', arc)
        .attr('fill', d => d.data.color)
        .attr('stroke', '#fff')
        .style('stroke-width', '2px')
        .style('opacity', 0.85);

      arcs.append('text')
        .attr('transform', d => `translate(${arc.centroid(d)})`)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .attr('fill', '#fff')
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
        .text(d => {
          const total = unique + duplicate;
          const pct = total > 0 ? (d.data.value / total) * 100 : 0;
          return pct > 10 ? `${pct.toFixed(1)}%` : '';
        });

    } catch (e) {
      console.error('[Analytics] Pie chart render error:', e);
    }
  }

  private async renderHistogram(containerId: string, values: number[], color: string, titleX: string, meanVal: number) {
    const el = document.getElementById(containerId);
    if (!el || !values.length) return;

    try {
      const d3 = await import('d3');
      el.innerHTML = '';

      const margin = { top: 20, right: 10, bottom: 35, left: 40 };
      const width = el.clientWidth || 300;
      const height = 180;
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      const x = d3.scaleLinear()
        .domain([0, d3.max(values) || 100])
        .range([0, innerWidth]);

      const histogram = d3.bin()
        .domain(x.domain() as [number, number])
        .thresholds(x.ticks(20));

      const bins = histogram(values);

      const y = d3.scaleLinear()
        .domain([0, d3.max(bins, d => d.length) || 10])
        .range([innerHeight, 0]);

      g.selectAll('rect')
        .data(bins)
        .enter()
        .append('rect')
        .attr('x', d => x(d.x0 ?? 0) + 1)
        .attr('y', d => y(d.length))
        .attr('width', d => Math.max(0, x(d.x1 ?? 0) - x(d.x0 ?? 0) - 1))
        .attr('height', d => innerHeight - y(d.length))
        .style('fill', color)
        .style('opacity', 0.7);

      g.append('line')
        .attr('x1', x(meanVal))
        .attr('x2', x(meanVal))
        .attr('y1', 0)
        .attr('y2', innerHeight)
        .attr('stroke', '#e74c3c')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '4,4');

      g.append('text')
        .attr('x', x(meanVal) + 5)
        .attr('y', 10)
        .attr('fill', '#e74c3c')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .text(`Media: ${meanVal.toFixed(1)}`);

      g.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(5))
        .attr('font-size', '10px')
        .attr('font-family', 'Manrope, sans-serif');

      g.append('g')
        .call(d3.axisLeft(y).ticks(5))
        .attr('font-size', '10px')
        .attr('font-family', 'Manrope, sans-serif');

      g.append('text')
        .attr('x', innerWidth / 2)
        .attr('y', innerHeight + margin.bottom - 4)
        .attr('text-anchor', 'middle')
        .attr('fill', '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Manrope, sans-serif')
        .text(titleX);

    } catch (e) {
      console.error('[Analytics] Histogram render error:', e);
    }
  }

  private async renderBoxPlot(containerId: string, datasets: { label: string; values: number[] }[], color: string, titleY: string) {
    const el = document.getElementById(containerId);
    if (!el || !datasets.length) return;

    try {
      const d3 = await import('d3');
      el.innerHTML = '';

      const margin = { top: 20, right: 20, bottom: 40, left: 50 };
      const width = el.clientWidth || 500;
      const height = 300;
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      const x = d3.scaleBand()
        .range([0, innerWidth])
        .domain(datasets.map(d => d.label))
        .padding(0.4);

      g.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x))
        .attr('font-size', '11px')
        .attr('font-family', 'Manrope, sans-serif')
        .selectAll('text')
        .style('text-anchor', datasets.length > 3 ? 'end' : 'middle')
        .attr('transform', datasets.length > 3 ? 'rotate(-25)' : '');

      const allValues = datasets.flatMap(d => d.values);
      const yMax = d3.max(allValues) || 100;
      const y = d3.scaleLinear()
        .domain([0, yMax])
        .range([innerHeight, 0]);

      g.append('g')
        .call(d3.axisLeft(y).ticks(5))
        .attr('font-size', '10px')
        .attr('font-family', 'Manrope, sans-serif');

      datasets.forEach(d => {
        const sorted = [...d.values].sort(d3.ascending);
        if (sorted.length < 4) return;

        const q1 = d3.quantile(sorted, 0.25) || 0;
        const median = d3.quantile(sorted, 0.5) || 0;
        const q3 = d3.quantile(sorted, 0.75) || 0;
        const interQuantileRange = q3 - q1;
        const minVal = Math.max(sorted[0], q1 - 1.5 * interQuantileRange);
        const maxVal = Math.min(sorted[sorted.length - 1], q3 + 1.5 * interQuantileRange);

        const xCenter = (x(d.label) || 0) + x.bandwidth() / 2;
        const boxWidth = x.bandwidth();

        g.append('line')
          .attr('x1', xCenter)
          .attr('x2', xCenter)
          .attr('y1', y(minVal))
          .attr('y2', y(maxVal))
          .attr('stroke', '#374151')
          .attr('stroke-width', 1.5);

        g.append('rect')
          .attr('x', x(d.label) || 0)
          .attr('y', y(q3))
          .attr('height', y(q1) - y(q3))
          .attr('width', boxWidth)
          .attr('stroke', '#374151')
          .attr('stroke-width', 1.5)
          .style('fill', color)
          .style('opacity', 0.6);

        g.append('line')
          .attr('x1', x(d.label) || 0)
          .attr('x2', (x(d.label) || 0) + boxWidth)
          .attr('y1', y(median))
          .attr('y2', y(median))
          .attr('stroke', '#1e1b4b')
          .attr('stroke-width', 2);

        g.append('line')
          .attr('x1', xCenter - boxWidth / 4)
          .attr('x2', xCenter + boxWidth / 4)
          .attr('y1', y(minVal))
          .attr('y2', y(minVal))
          .attr('stroke', '#374151');

        g.append('line')
          .attr('x1', xCenter - boxWidth / 4)
          .attr('x2', xCenter + boxWidth / 4)
          .attr('y1', y(maxVal))
          .attr('y2', y(maxVal))
          .attr('stroke', '#374151');
      });

      g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -innerHeight / 2)
        .attr('y', -35)
        .attr('text-anchor', 'middle')
        .attr('fill', '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Manrope, sans-serif')
        .text(titleY);

    } catch (e) {
      console.error('[Analytics] Box plot render error:', e);
    }
  }

  private async renderScatterPlot(containerId: string, data: { x: number; y: number }[], color: string, titleX: string, titleY: string) {
    const el = document.getElementById(containerId);
    if (!el || !data.length) return;

    try {
      const d3 = await import('d3');
      el.innerHTML = '';

      const margin = { top: 20, right: 20, bottom: 40, left: 50 };
      const width = el.clientWidth || 500;
      const height = 300;
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      const xMax = d3.max(data, d => d.x) || 100;
      const yMax = d3.max(data, d => d.y) || 100;

      const x = d3.scaleLinear().domain([0, xMax]).range([0, innerWidth]);
      const y = d3.scaleLinear().domain([0, yMax]).range([innerHeight, 0]);

      g.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x))
        .attr('font-size', '10px')
        .attr('font-family', 'Manrope, sans-serif');

      g.append('g')
        .call(d3.axisLeft(y))
        .attr('font-size', '10px')
        .attr('font-family', 'Manrope, sans-serif');

      g.selectAll('circle')
        .data(data)
        .enter()
        .append('circle')
        .attr('cx', d => x(d.x))
        .attr('cy', d => y(d.y))
        .attr('r', 3)
        .style('fill', color)
        .style('opacity', 0.4);

      g.append('text')
        .attr('x', innerWidth / 2)
        .attr('y', innerHeight + margin.bottom - 4)
        .attr('text-anchor', 'middle')
        .attr('fill', '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Manrope, sans-serif')
        .text(titleX);

      g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -innerHeight / 2)
        .attr('y', -35)
        .attr('text-anchor', 'middle')
        .attr('fill', '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Manrope, sans-serif')
        .text(titleY);

    } catch (e) {
      console.error('[Analytics] Scatter plot render error:', e);
    }
  }

  private async renderLogLogChart(containerId: string, data: { word: string; count: number }[]) {
    const el = document.getElementById(containerId);
    if (!el || !data.length) return;

    try {
      const d3 = await import('d3');
      el.innerHTML = '';

      const margin = { top: 20, right: 20, bottom: 40, left: 50 };
      const width = el.clientWidth || 500;
      const height = 300;
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      const plotData = data.map((d, i) => ({
        rank: i + 1,
        count: d.count,
        word: d.word
      }));

      const x = d3.scaleLog()
        .domain([1, plotData.length])
        .range([0, innerWidth]);

      const y = d3.scaleLog()
        .domain([d3.min(plotData, d => d.count) || 1, d3.max(plotData, d => d.count) || 100])
        .range([innerHeight, 0]);

      g.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(5, ',d'))
        .attr('font-size', '10px')
        .attr('font-family', 'Manrope, sans-serif');

      g.append('g')
        .call(d3.axisLeft(y).ticks(5, ',d'))
        .attr('font-size', '10px')
        .attr('font-family', 'Manrope, sans-serif');

      const line = d3.line<{ rank: number; count: number }>()
        .x(d => x(d.rank))
        .y(d => y(d.count));

      g.append('path')
        .datum(plotData)
        .attr('fill', 'none')
        .attr('stroke', '#0EA5E9')
        .attr('stroke-width', 2)
        .attr('d', line);

      g.selectAll('circle')
        .data(plotData)
        .enter()
        .append('circle')
        .attr('cx', d => x(d.rank))
        .attr('cy', d => y(d.count))
        .attr('r', 4)
        .style('fill', '#1e1b4b')
        .style('stroke', '#0EA5E9')
        .style('stroke-width', 1.5)
        .style('cursor', 'pointer')
        .append('title')
        .text(d => `Palabra: "${d.word}"\nRango: ${d.rank}\nFrecuencia: ${d.count}`);

      g.append('text')
        .attr('x', innerWidth / 2)
        .attr('y', innerHeight + margin.bottom - 4)
        .attr('text-anchor', 'middle')
        .attr('fill', '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Manrope, sans-serif')
        .text('Rango de palabra (Log)');

      g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -innerHeight / 2)
        .attr('y', -35)
        .attr('text-anchor', 'middle')
        .attr('fill', '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Manrope, sans-serif')
        .text('Frecuencia (Log)');

    } catch (e) {
      console.error('[Analytics] Log-log render error:', e);
    }
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

  private async renderWordcloud() {
    const containerId = 'chart-wordcloud';
    const el = document.getElementById(containerId);
    const words = this.wordcloudData();
    if (!el || !words.length) return;

    try {
      const d3 = await import('d3');
      el.innerHTML = '';

      const width = el.clientWidth || 800;
      const height = 450;

      const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

      const g = svg.append('g').attr('transform', `translate(${width / 2},${height / 2})`);

      const maxCount = d3.max(words, d => d.count) || 1;
      const minCount = d3.min(words, d => d.count) || 1;

      const fontScale = d3.scaleSqrt()
        .domain([minCount, maxCount])
        .range([12, 54]);

      const colors = ['#1E1B4B', '#84CC16', '#0EA5E9', '#8b5cf6', '#f59e0b', '#3b82f6', '#22c55e', '#ec4899'];
      const colorScale = d3.scaleOrdinal(colors);

      const nodes = words.map((w, i) => {
        const size = fontScale(w.count);
        const wWidth = w.word.length * size * 0.6 + 8;
        const wHeight = size + 6;
        const r = Math.max(wWidth, wHeight) / 2;
        return {
          word: w.word,
          count: w.count,
          size,
          r,
          x: (Math.random() - 0.5) * 100,
          y: (Math.random() - 0.5) * 100
        };
      });

      const simulation = d3.forceSimulation<any>(nodes)
        .force('x', d3.forceX(0).strength(0.12))
        .force('y', d3.forceY(0).strength(0.12))
        .force('collide', d3.forceCollide<any>(d => d.r).iterations(4))
        .stop();

      for (let i = 0; i < 200; ++i) simulation.tick();

      g.selectAll('text')
        .data(nodes)
        .enter()
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('x', d => d.x)
        .attr('y', d => d.y)
        .style('font-family', 'Manrope, sans-serif')
        .style('font-weight', 'bold')
        .style('font-size', d => `${d.size}px`)
        .style('fill', (d, i) => colorScale(i.toString()))
        .style('opacity', 0.9)
        .style('cursor', 'pointer')
        .style('transition', 'transform 0.15s, opacity 0.15s')
        .text(d => d.word)
        .on('mouseover', function(event, d) {
          d3.select(this)
            .style('transform', 'scale(1.1)')
            .style('opacity', 1.0);
        })
        .on('mouseout', function(event, d) {
          d3.select(this)
            .style('transform', 'scale(1)')
            .style('opacity', 0.9);
        })
        .append('title')
        .text(d => `Palabra: "${d.word}"\nFrecuencia: ${d.count} veces`);

    } catch (e) {
      console.error('[Analytics] Wordcloud render error:', e);
    }
  }
}

