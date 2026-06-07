import { Component, OnInit, signal, computed } from '@angular/core';
import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';

interface AdminStats {
  total_noticias: number;
  validadas: number;
  chunks: number;
  fuentes_activas: number;
  by_scope: Record<string, number>;
  by_day: { fecha: string; total: number }[];
  pipeline: Record<string, number>;
}

interface Fuente {
  id: number;
  nombre: string;
  slug: string;
  activa: boolean;
  seeds_count: number;
  noticias_count: number;
  confiabilidad: number;
}

interface NoticiaAdmin {
  id: number;
  titulo: string;
  scope_geografico: string;
  distrito: string | null;
  fecha_publicacion: string | null;
  estado_procesamiento: string;
  categoria_principal: string | null;
}

interface ChunkDetail {
  id: number;
  chunk_index: number;
  texto_preview: string;
  texto_completo: string;
  tokens_estimados: number;
}

interface ScrapingSummary {
  id: number;
  fecha: string;
  urls_totales: number;
  filtradas_geo: number;
  insertadas: number;
  errores: number;
  duplicadas: number;
  created_at: string;
}

interface LiveLog {
  id: number;
  nivel: string;
  mensaje: string;
  fecha: string;
  tipo: string;
  created_at: string;
}

interface ScraperStatus {
  running: boolean;
  current_day: string | null;
  lines_count: number;
  started_at: string | null;
  command: string;
}

interface GraphNode {
  id: number;
  noticia_id: number;
  chunk_index: number;
  tokens: number;
  titulo: string;
  categoria: string;
  scope: string;
  preview: string;
}

interface GraphEdge {
  source: number;
  target: number;
  similarity: number;
}

interface Vector3DPoint {
  id: number;
  x: number;
  y: number;
  z: number;
  noticia_id: number;
  titulo: string;
  scope_geografico: string;
  distrito: string | null;
  provincia: string | null;
  seccion_fuente: string | null;
  categoria_principal: string | null;
  chunk_index: number;
  tokens: number;
  preview: string;
}

type Tab = 'dashboard' | 'noticias' | 'vectores' | 'scraping' | 'fuentes';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [FormsModule, DatePipe],
  template: `
    <div class="admin">
      <header class="admin__header">
        <div class="admin__brand">
          <h1>NotiBot Admin</h1>
          <span class="admin__badge">{{ auth.currentUser()?.nombre_usuario }}</span>
        </div>
        <a routerLink="/" class="admin__back">← Sitio</a>
      </header>

      <nav class="admin__nav">
        @for (tab of tabs; track tab.id) {
          <button
            class="admin__tab"
            [class.admin__tab--active]="activeTab() === tab.id"
            (click)="onTabChange(tab.id)"
          >
            {{ tab.label }}
            @if (tab.id === 'dashboard') {
              <span class="admin__tab-count">{{ stats().total_noticias }}</span>
            }
          </button>
        }
      </nav>

      @switch (activeTab()) {
        @case ('dashboard') {
          <section class="dashboard">
            <div class="stats-grid">
              <div class="stat-card">
                <span class="stat-card__value">{{ stats().total_noticias }}</span>
                <span class="stat-card__label">Noticias</span>
              </div>
              <div class="stat-card">
                <span class="stat-card__value">{{ stats().chunks }}</span>
                <span class="stat-card__label">Chunks</span>
              </div>
              <div class="stat-card">
                <span class="stat-card__value">{{ stats().fuentes_activas }}</span>
                <span class="stat-card__label">Fuentes</span>
              </div>
              <div class="stat-card">
                <span class="stat-card__value">{{ stats().validadas }}</span>
                <span class="stat-card__label">Validadas</span>
              </div>
            </div>

            <div class="dashboard__row">
              <div class="card card--half">
                <h3>Pipeline</h3>
                <div class="pipe-stats">
                  <div class="pipe-stat">
                    <span class="pipe-stat__val">{{ stats().chunks }}</span>
                    <span class="pipe-stat__lbl">Chunks</span>
                  </div>
                  <div class="pipe-stat">
                    <span class="pipe-stat__val">{{ stats().pipeline['completado'] || 0 }}</span>
                    <span class="pipe-stat__lbl">Completados</span>
                  </div>
                  <div class="pipe-stat">
                    <span class="pipe-stat__val">{{ stats().pipeline['pendiente'] || 0 }}</span>
                    <span class="pipe-stat__lbl">Pendientes</span>
                  </div>
                </div>
                <div class="pipe-actions">
                  <button class="btn" (click)="triggerPipeline()" [disabled]="pipelineLoading()">
                    {{ pipelineLoading() ? 'Procesando...' : 'Procesar pendientes' }}
                  </button>
                  <button class="btn-sm" (click)="clearPipelineErrors()">Limpiar errores</button>
                </div>
                @if (pipelineError()) { <span class="msg-error">{{ pipelineError() }}</span> }
                @if (pipelineMsg()) { <span class="msg-ok">{{ pipelineMsg() }}</span> }
              </div>

              <div class="card card--half">
                <h3>Por alcance</h3>
                @for (entry of scopeEntries(); track entry[0]) {
                  <div class="scope-row">
                    <span class="scope-row__label">{{ entry[0] }}</span>
                    <div class="scope-row__bar" [style.width.%]="scopePercent(entry[1])"></div>
                    <span class="scope-row__count">{{ entry[1] }}</span>
                  </div>
                }
              </div>
            </div>

            <div class="card">
              <h3>Actividad (30 días)</h3>
              @for (day of stats().by_day; track day.fecha) {
                <div class="day-row">
                  <span class="day-row__date">{{ day.fecha }}</span>
                  <div class="day-row__bar">
                    <div [style.width.%]="dayPercent(day.total)" class="day-row__fill"></div>
                  </div>
                  <span class="day-row__count">{{ day.total }}</span>
                </div>
              }
            </div>
          </section>
        }

        @case ('noticias') {
          <section class="noticias">
            <div class="card">
              <div class="filters">
                <select [ngModel]="newsFilterScope()" (ngModelChange)="newsFilterScope.set($event); loadNoticias()" class="select">
                  <option value="">Todos los alcances</option>
                  <option value="lima_metropolitana">Lima Metropolitana</option>
                  <option value="callao">Callao</option>
                </select>
                <select [ngModel]="newsFilterEstado()" (ngModelChange)="newsFilterEstado.set($event); loadNoticias()" class="select">
                  <option value="">Todos los estados</option>
                  <option value="pendiente">Pendiente</option>
                  <option value="scrapeado">Scrapeado</option>
                  <option value="procesado_llm">Procesado LLM</option>
                  <option value="vectorizado">Vectorizado</option>
                  <option value="publicado">Publicado</option>
                  <option value="error">Error</option>
                </select>
                <span class="filters__total">{{ newsTotal() }} noticias</span>
              </div>
            </div>

            <div class="card">
              <table class="table">
                <thead>
                  <tr>
                    <th></th>
                    <th>Titulo</th>
                    <th>Alcance</th>
                    <th>Estado</th>
                    <th>Categoria</th>
                    <th>Fecha</th>
                    <th>Chunks</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  @for (n of noticias(); track n.id) {
                    <tr (click)="toggleChunks(n.id)" class="news-row">
                      <td class="td-id">{{ n.id }}</td>
                      <td class="td-title">{{ n.titulo }}</td>
                      <td>
                        <span class="tag" [class]="'tag--' + n.scope_geografico">{{ n.scope_geografico === 'lima_metropolitana' ? 'Lima' : 'Callao' }}</span>
                      </td>
                      <td>
                        <span class="tag" [class]="'tag--' + n.estado_procesamiento">{{ n.estado_procesamiento }}</span>
                      </td>
                      <td class="td-cat">{{ n.categoria_principal || '-' }}</td>
                      <td class="td-date">{{ n.fecha_publicacion | date:'dd/MM' }}</td>
                      <td>
                        <a class="chunk-link">{{ chunksForArticle(n.id).length || '-' }}</a>
                      </td>
                      <td>
                        <button class="btn-sm" (click)="$event.stopPropagation(); triggerChunking(n.id)">+Chunk</button>
                      </td>
                    </tr>
                    @if (expandedNoticiaId() === n.id) {
                      <tr class="chunk-rows">
                        <td colspan="7">
                          @if (chunksLoading()) {
                            <span class="chunks-loading">Cargando chunks...</span>
                          } @else if (chunks().length === 0) {
                            <span class="chunks-empty">Sin chunks — click en +Chunk para generarlos</span>
                          } @else {
                            <div class="chunks-list">
                              @for (c of chunks(); track c.chunk_index) {
                                <div class="chunk-item">
                                  <div class="chunk-item__header">
                                    <span class="chunk-item__idx">Chunk {{ c.chunk_index }}</span>
                                    <span class="chunk-item__tokens">{{ c.tokens_estimados }} tokens</span>
                                  </div>
                                  <p class="chunk-item__text">{{ c.texto_completo }}</p>
                                </div>
                              }
                            </div>
                          }
                        </td>
                      </tr>
                    }
                  }
                </tbody>
              </table>

              <div class="pagination">
                <button class="btn-sm" [disabled]="newsOffset() === 0" (click)="newsOffset.set(newsOffset() - 20); loadNoticias()">← Anterior</button>
                <span>Pág {{ newsPage() }} de {{ newsTotalPages() }}</span>
                <button class="btn-sm" [disabled]="newsOffset() + 20 >= newsTotal()" (click)="newsOffset.set(newsOffset() + 20); loadNoticias()">Siguiente →</button>
              </div>
            </div>
          </section>
        }

        @case ('vectores') {
          <section class="vectores">
            <div class="card">
              <div class="filters">
                <div class="view-toggle">
                  <button class="btn-sm" [class.btn]="vectorView() === '3d'" (click)="switchToView('3d')">Gráfico 3D</button>
                  <button class="btn-sm" [class.btn]="vectorView() === 'grafo'" (click)="switchToView('grafo')">Grafo Force</button>
                </div>
                @if (vectorView() === '3d') {
                  <select [ngModel]="vectorColorBy()" (ngModelChange)="vectorColorBy.set($event); renderPlot()" class="select">
                    <option value="seccion">Colorear: Sección</option>
                    <option value="scope">Colorear: Alcance</option>
                    <option value="distrito">Colorear: Distrito</option>
                    <option value="categoria">Colorear: Categoría</option>
                    <option value="provincia">Colorear: Provincia</option>
                  </select>
                  <select [ngModel]="vectorScope()" (ngModelChange)="vectorScope.set($event); loadVectores()" class="select">
                    <option value="">Filtro: Todos</option>
                    <option value="lima_metropolitana">Solo Lima</option>
                    <option value="callao">Solo Callao</option>
                  </select>
                }
                <span class="filters__total">{{ vectorView() === '3d' ? vectorTotal() + ' puntos' : graphNodes().length + ' nodos' }}</span>
                <button class="btn" (click)="generateVectors()" [disabled]="vectorLoading()">
                  {{ vectorLoading() ? 'Generando...' : 'Generar embeddings' }}
                </button>
              </div>
              @if (vectorView() === '3d') {
                <p class="legend-note">Tamaño = tokens · Hover = detalles · Leyenda interactiva</p>
              }
            </div>
            <div class="card">
              @if (vectorView() === '3d') {
                <div id="plot3d" style="width:100%;min-height:500px"></div>
              } @else {
                <div id="force-graph" style="width:100%;min-height:550px;background:#f8fafc;border-radius:8px"></div>
              }
            </div>
          </section>
        }

        @case ('scraping') {
          <section class="scraping">
            <div class="card">
              <div class="filters">
                <input type="date" [ngModel]="scrapingDate()" (ngModelChange)="scrapingDate.set($event)" class="select" />
                <button class="btn" (click)="triggerDailyScrape()" [disabled]="scrapingRunning()">
                  {{ scrapingRunning() ? '⏳ Ejecutando...' : 'Scrapear fecha' }}
                </button>
                <button class="btn" (click)="triggerTodayScrape()" [disabled]="scrapingRunning()">
                  Scrapear hoy
                </button>
                @if (scrapingRunning()) {
                  <button class="btn btn--stop" (click)="stopPolling()">Detener</button>
                }
                @if (scraperStatus().running) {
                  <span class="live-badge">{{ scraperStatus().lines_count }} líneas</span>
                }
              </div>
            </div>

            <div class="terminal">
              <div class="terminal__header">
                <span class="terminal__dots"><i></i><i></i><i></i></span>
                <span class="terminal__title">
                  @if (scraperStatus().running) {
                    notibot-scraper — {{ scraperStatus().current_day || 'iniciando...' }} — {{ scraperStatus().lines_count }} líneas
                  } @else {
                    notibot-scraper — {{ liveLogs().length ? 'ultima ejecucion' : 'sin actividad' }}
                  }
                </span>
                @if (scraperStatus().running) {
                  <span class="terminal__pulse">●</span>
                }
              </div>
              <div class="terminal__body" id="terminal-body">
                @for (log of liveLogs(); track log.id) {
                  <div class="term-line" [class]="'term--' + log.nivel">
                    <span class="term-time">{{ log.created_at | date:'HH:mm:ss' }}</span>
                    @if (log.mensaje.includes('✓')) {
                      <span class="term-ok">✓</span><span>{{ log.mensaje.replace('✓', '') }}</span>
                    } @else if (log.mensaje.includes('✗')) {
                      <span class="term-err">✗</span><span>{{ log.mensaje.replace('✗', '') }}</span>
                    } @else if (log.mensaje.includes('─') || log.mensaje.includes('DIA:')) {
                      <span class="term-hr">{{ log.mensaje }}</span>
                    } @else if (log.mensaje.includes('Progress:')) {
                      <span class="term-progress">{{ log.mensaje }}</span>
                    } @else {
                      <span>{{ log.mensaje }}</span>
                    }
                  </div>
                }
                @if (!liveLogs().length) {
                  <div class="term-line term--info">
                    <span class="term-prompt">$</span>
                    <span class="term-cursor">_</span>
                  </div>
                }
              </div>
            </div>

            <div class="card" style="margin-top:16px">
              <h3>Resumen diario</h3>
              <table class="table">
                <thead>
                  <tr><th>Fecha</th><th>URLs</th><th>Filtradas</th><th>Insertadas</th><th>Errores</th></tr>
                </thead>
                <tbody>
                  @for (s of dailySummaries(); track s.id) {
                    <tr>
                      <td>{{ s.fecha }}</td><td>{{ s.urls_totales }}</td>
                      <td>{{ s.filtradas_geo }}</td>
                      <td class="td-green">{{ s.insertadas }}</td>
                      <td class="td-red">{{ s.errores }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </section>
        }

        @case ('fuentes') {
          <section class="fuentes">
            <div class="card">
              <table class="table">
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Slug</th>
                    <th>Seeds</th>
                    <th>Noticias</th>
                    <th>Confiabilidad</th>
                    <th>Activa</th>
                  </tr>
                </thead>
                <tbody>
                  @for (f of fuentes(); track f.id) {
                    <tr>
                      <td>{{ f.nombre }}</td>
                      <td class="td-mono">{{ f.slug }}</td>
                      <td>{{ f.seeds_count }}</td>
                      <td>{{ f.noticias_count }}</td>
                      <td>{{ f.confiabilidad }}</td>
                      <td>{{ f.activa ? '✓' : '✗' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </section>
        }
      }
    </div>
  `,
  styles: [`
    :host { --brand: #1E1B4B; --cta: #84CC16; --bg: #f5f5f7; --card: #fff; --border: #e5e7eb; --text: #1f2937; --text2: #6b7280; display: block; min-height: 100vh; background: var(--bg); font-family: 'Manrope', sans-serif; color: var(--text); }

    .admin { max-width: 1120px; margin: 0 auto; padding: 0 20px 40px; }
    .admin__header { display: flex; align-items: center; justify-content: space-between; padding: 20px 0 12px; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
    .admin__brand { display: flex; align-items: center; gap: 12px; }
    .admin__brand h1 { margin: 0; font-family: 'Newsreader', serif; font-size: 22px; color: var(--brand); }
    .admin__badge { background: var(--brand); color: #fff; padding: 2px 10px; border-radius: 10px; font-size: 12px; }
    .admin__back { color: var(--text2); text-decoration: none; font-size: 14px; }
    .admin__back:hover { color: var(--brand); }

    .admin__nav { display: flex; gap: 0; margin-bottom: 24px; border-bottom: 2px solid var(--border); }
    .admin__tab { background: none; border: none; padding: 10px 24px; font-size: 14px; font-weight: 500; color: var(--text2); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all .15s; display: flex; align-items: center; gap: 8px; }
    .admin__tab:hover { color: var(--brand); }
    .admin__tab--active { color: var(--brand); border-bottom-color: var(--brand); }
    .admin__tab-count { background: var(--cta); color: var(--brand); padding: 0 6px; border-radius: 6px; font-size: 11px; font-weight: 700; }

    .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
    .stat-card { background: var(--card); padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
    .stat-card__value { display: block; font-size: 34px; font-weight: 700; color: var(--brand); }
    .stat-card__label { font-size: 13px; color: var(--text2); margin-top: 4px; }

    .dashboard__row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }

    .card { background: var(--card); padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.04); margin-bottom: 16px; }
    .card h3 { margin: 0 0 12px; font-size: 15px; font-weight: 600; }
    .card--half { margin-bottom: 0; }

    .pipeline-grid { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
    .pipeline-badge { background: #eef2ff; padding: 10px 16px; border-radius: 8px; text-align: center; min-width: 80px; }
    .pipeline-badge__count { display: block; font-size: 22px; font-weight: 600; color: var(--brand); }
    .pipeline-badge__label { font-size: 11px; color: var(--text2); }
    .pipe-stats { display: flex; gap: 16px; margin-bottom: 16px; }
    .pipe-stat { text-align: center; min-width: 70px; }
    .pipe-stat__val { display: block; font-size: 26px; font-weight: 700; color: var(--brand); }
    .pipe-stat__lbl { font-size: 11px; color: var(--text2); }
    .pipe-actions { display: flex; gap: 8px; align-items: center; }
    .msg-ok { color: #16a34a; font-size: 12px; margin-left: 8px; }

    .btn { background: var(--cta); color: var(--brand); border: none; padding: 8px 20px; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; transition: opacity .15s; }
    .btn:hover { opacity: .85; }
    .btn-sm { background: #f3f4f6; border: 1px solid var(--border); padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; color: var(--text); }
    .btn-sm:hover { background: #e5e7eb; }
    .btn-sm:disabled { opacity: .4; cursor: default; }
    .msg-error { color: #dc2626; font-size: 12px; margin-left: 8px; }
    .empty { color: var(--text2); font-size: 13px; }

    .scope-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .scope-row__label { width: 110px; font-size: 13px; text-transform: capitalize; }
    .scope-row__bar { height: 8px; background: var(--cta); border-radius: 4px; transition: width .3s; }
    .scope-row__count { font-size: 13px; font-weight: 600; width: 30px; text-align: right; }

    .day-row { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
    .day-row__date { width: 85px; font-size: 12px; color: var(--text2); }
    .day-row__bar { flex: 1; height: 16px; background: #f3f4f6; border-radius: 3px; }
    .day-row__fill { height: 100%; background: var(--brand); border-radius: 3px; min-width: 2px; transition: width .3s; }
    .day-row__count { font-size: 12px; font-weight: 600; width: 24px; }

    .filters { display: flex; align-items: center; gap: 12px; }
    .select { padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; font-family: inherit; background: #fff; }
    .filters__total { font-size: 13px; color: var(--text2); margin-left: auto; }

    .table { width: 100%; border-collapse: collapse; }
    .table th { text-align: left; padding: 10px 8px; font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text2); border-bottom: 1px solid var(--border); }
    .table td { padding: 8px; font-size: 13px; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
    .td-id { width: 40px; color: var(--text2); font-size: 12px !important; }
    .td-title { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .td-date { white-space: nowrap; color: var(--text2); font-size: 12px !important; }
    .td-cat { font-size: 12px; color: var(--brand); }
    .td-mono { font-family: monospace; font-size: 12px; color: var(--text2); }

    .tag { display: inline-block; padding: 1px 8px; border-radius: 8px; font-size: 11px; font-weight: 500; }
    .tag--lima_metropolitana { background: #dbeafe; color: #1e40af; }
    .tag--callao { background: #fce7f3; color: #9d174d; }
    .tag--pendiente { background: #fef3c7; color: #92400e; }
    .tag--scrapeado { background: #e0e7ff; color: #3730a3; }
    .tag--procesado_llm { background: #d1fae5; color: #065f46; }
    .tag--vectorizado { background: #cffafe; color: #155e75; }
    .tag--publicado { background: #dcfce7; color: #166534; }
    .tag--error { background: #fee2e2; color: #991b1b; }

    .pagination { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 16px; font-size: 13px; color: var(--text2); }

    .legend { display: flex; align-items: center; gap: 16px; margin-top: 8px; font-size: 12px; color: var(--text2); }
    .legend-item { display: flex; align-items: center; gap: 6px; }
    .legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    .legend-note { margin-left: auto; font-style: italic; }

    .scraping { }
    .vectores { }
    .view-toggle { display: flex; gap: 4px; margin-right: 12px; }
    .view-toggle .btn { font-size: 12px; padding: 6px 14px; }
    .btn--stop { background: #fecaca !important; color: #991b1b !important; }
    .td-green { color: #16a34a; font-weight: 600; }
    .td-red { color: #dc2626; font-weight: 600; }
    .live-badge { font-size: 12px; color: var(--cta); font-weight: 600; margin-left: auto; }

    .terminal { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,.2); margin-bottom: 16px; }
    .terminal__header { display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: #2d2d3f; }
    .terminal__dots { display: flex; gap: 6px; }
    .terminal__dots i { width: 10px; height: 10px; border-radius: 50%; display: block; background: #ff5f56; }
    .terminal__dots i:nth-child(2) { background: #ffbd2e; }
    .terminal__dots i:nth-child(3) { background: #27ca40; }
    .terminal__title { flex: 1; font-size: 11px; color: #a0a0b0; font-family: monospace; }
    .terminal__pulse { color: #27ca40; font-size: 10px; animation: pulse 1s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
    .terminal__body { background: #1a1a2e; padding: 14px; min-height: 400px; max-height: 550px; overflow-y: auto; font-family: 'Fira Code', 'Cascadia Code', 'Consolas', monospace; font-size: 12px; line-height: 1.7; }
    .term-line { display: flex; gap: 8px; align-items: baseline; color: #c0c0d0; }
    .term-time { color: #555; font-size: 11px; min-width: 65px; }
    .term-ok { color: #4ade80; font-weight: 600; }
    .term-err { color: #f87171; font-weight: 600; }
    .term-hr { color: #6366f1; font-weight: 600; }
    .term-progress { color: #fbbf24; font-weight: 600; }
    .term-prompt { color: #4ade80; margin-right: 6px; }
    .term-cursor { display: inline-block; width: 8px; height: 15px; background: #4ade80; animation: blink 1s step-end infinite; }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
    .term--info { color: #a0a0c0; }
    .term--warning { color: #fbbf24; }
    .term--error { color: #f87171; }

    .news-row { cursor: pointer; transition: background .1s; }
    .news-row:hover { background: #f9fafb; }
    .chunk-link { color: var(--brand); font-size: 13px; font-weight: 600; text-decoration: underline; cursor: pointer; }
    .chunk-rows td { padding: 0 !important; background: #fafbff; border-bottom: 2px solid var(--brand); }
    .chunks-list { padding: 16px 20px; }
    .chunks-loading, .chunks-empty { display: block; padding: 16px 20px; font-size: 13px; color: var(--text2); }
    .chunk-item { margin-bottom: 16px; }
    .chunk-item:last-child { margin-bottom: 0; }
    .chunk-item__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
    .chunk-item__idx { font-size: 12px; font-weight: 600; color: var(--brand); }
    .chunk-item__tokens { font-size: 11px; color: var(--text2); }
    .chunk-item__text { margin: 0; font-size: 13px; color: var(--text); line-height: 1.6; white-space: pre-wrap; }
  `],
})
export class AdminComponent implements OnInit {
  private readonly apiUrl = '/api/admin';

  readonly tabs: { id: Tab; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'noticias', label: 'Noticias' },
    { id: 'vectores', label: 'Vectores 3D' },
    { id: 'scraping', label: 'Scraping' },
    { id: 'fuentes', label: 'Fuentes' },
  ];

  activeTab = signal<Tab>('dashboard');

  stats = signal<AdminStats>({
    total_noticias: 0, validadas: 0, chunks: 0, fuentes_activas: 0,
    by_scope: {}, by_day: [], pipeline: {},
  });
  fuentes = signal<Fuente[]>([]);
  pipelineError = signal('');
  pipelineLoading = signal(false);
  pipelineMsg = signal('');

  vectorPoints = signal<Vector3DPoint[]>([]);
  vectorTotal = signal(0);
  vectorLoading = signal(false);
  vectorScope = signal('');
  vectorColorBy = signal<'scope' | 'distrito' | 'seccion' | 'categoria' | 'provincia'>('seccion');
  vectorView = signal<'3d' | 'grafo'>('3d');

  graphNodes = signal<GraphNode[]>([]);
  graphEdges = signal<GraphEdge[]>([]);
  graphLoading = signal(false);

  dailySummaries = signal<ScrapingSummary[]>([]);
  liveLogs = signal<LiveLog[]>([]);
  scraperStatus = signal<ScraperStatus>({ running: false, current_day: null, lines_count: 0, started_at: null, command: '' });
  scrapingRunning = signal(false);
  scrapingDate = signal(new Date().toISOString().slice(0, 10));
  pollingInterval: any = null;
  private consoleEl: HTMLElement | null = null;

  noticias = signal<NoticiaAdmin[]>([]);
  newsTotal = signal(0);
  newsOffset = signal(0);
  newsFilterScope = signal('');
  newsFilterEstado = signal('');
  newsPage = computed(() => Math.floor(this.newsOffset() / 20) + 1);
  newsTotalPages = computed(() => Math.max(Math.ceil(this.newsTotal() / 20), 1));
  expandedNoticiaId = signal<number | null>(null);
  chunks = signal<ChunkDetail[]>([]);
  chunksLoading = signal(false);

  maxDayTotal = signal(1);

  constructor(private http: HttpClient, public auth: AuthService) {}

  ngOnInit() {
    this.loadStats();
    this.loadFuentes();
    this.loadNoticias();
  }

  pipelineEntries() { return Object.entries(this.stats().pipeline); }
  scopeEntries() { return Object.entries(this.stats().by_scope); }

  scopePercent(count: number): number {
    const total = this.stats().total_noticias || 1;
    return Math.round((count / total) * 100);
  }

  dayPercent(count: number): number {
    const max = this.maxDayTotal() || 1;
    return Math.round((count / max) * 100);
  }

  loadStats() {
    this.http.get<AdminStats>(`${this.apiUrl}/stats`).subscribe((data) => {
      this.stats.set(data);
      this.maxDayTotal.set(Math.max(...data.by_day.map((d) => d.total), 1));
    });
  }

  loadFuentes() {
    this.http.get<Fuente[]>(`${this.apiUrl}/fuentes`).subscribe((data) => this.fuentes.set(data));
  }

  loadNoticias() {
    const params = new URLSearchParams();
    if (this.newsFilterScope()) params.set('scope', this.newsFilterScope());
    if (this.newsFilterEstado()) params.set('estado_procesamiento', this.newsFilterEstado());
    params.set('limit', '20');
    params.set('offset', String(this.newsOffset()));

    this.http.get<{ items: NoticiaAdmin[]; total: number }>(`${this.apiUrl}/noticias?${params}`)
      .subscribe((data) => {
        this.noticias.set(data.items);
        this.newsTotal.set(data.total);
      });
  }

  triggerPipeline() {
    this.pipelineLoading.set(true);
    this.pipelineError.set('');
    this.pipelineMsg.set('');
    this.http.post<{ processed: number }>(`${this.apiUrl}/pipeline/process`, {}).subscribe({
      next: (res) => {
        this.pipelineLoading.set(false);
        this.pipelineMsg.set(`${res.processed} procesados`);
        this.loadStats();
      },
      error: () => {
        this.pipelineLoading.set(false);
        this.pipelineError.set('Error al procesar');
      },
    });
  }

  clearPipelineErrors() {
    this.http.delete<{ deleted: number }>(`${this.apiUrl}/pipeline/errors`).subscribe({
      next: (res) => {
        this.pipelineMsg.set(`${res.deleted} errores limpiados`);
        this.loadStats();
      },
    });
  }

  triggerChunking(noticiaId: number) {
    this.http.post(`${this.apiUrl}/pipeline/chunking/${noticiaId}`, {}).subscribe({
      next: () => {
        this.loadStats();
        this.loadNoticias();
      },
      error: () => {},
    });
  }

  chunksForArticle(noticiaId: number): ChunkDetail[] {
    if (this.expandedNoticiaId() !== noticiaId) return [];
    return this.chunks();
  }

  toggleChunks(noticiaId: number) {
    if (this.expandedNoticiaId() === noticiaId) {
      this.expandedNoticiaId.set(null);
      this.chunks.set([]);
      return;
    }
    this.expandedNoticiaId.set(noticiaId);
    this.chunksLoading.set(true);
    this.http.get<ChunkDetail[]>(`${this.apiUrl}/noticias/${noticiaId}/chunks`).subscribe({
      next: (data) => {
        this.chunks.set(data);
        this.chunksLoading.set(false);
      },
      error: () => this.chunksLoading.set(false),
    });
  }

  switchToView(view: '3d' | 'grafo') {
    this.vectorView.set(view);
    if (view === '3d' && this.vectorPoints().length > 0) {
      setTimeout(() => this.renderPlot(), 100);
    }
    if (view === 'grafo') {
      this.loadGraph();
    }
  }

  loadVectores() {
    this.vectorLoading.set(true);
    const params = new URLSearchParams();
    if (this.vectorScope()) params.set('scope', this.vectorScope());
    this.http.get<{ total: number; points: Vector3DPoint[] }>(
      `${this.apiUrl}/vectores/3d?${params}`
    ).subscribe({
      next: (data) => {
        this.vectorPoints.set(data.points);
        this.vectorTotal.set(data.total);
        this.vectorLoading.set(false);
        setTimeout(() => this.renderPlot(), 100);
      },
      error: () => this.vectorLoading.set(false),
    });
  }

  renderPlot() {
    const points = this.vectorPoints();
    if (!points.length) return;

    const colorBy = this.vectorColorBy();
    const groups = new Map<string, Vector3DPoint[]>();

    for (const p of points) {
      let key = 'Sin dato';
      if (colorBy === 'scope') key = p.scope_geografico === 'callao' ? 'Callao' : 'Lima Metropolitana';
      else if (colorBy === 'distrito') key = p.distrito || 'Sin distrito';
      else if (colorBy === 'seccion') key = p.seccion_fuente || 'Sin sección';
      else if (colorBy === 'categoria') key = p.categoria_principal || 'Sin categoría';
      else if (colorBy === 'provincia') key = p.provincia || 'Sin provincia';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(p);
    }

    const palette = [
      '#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899',
      '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#14b8a6', '#d946ef',
      '#0ea5e9', '#e11d48', '#10b981', '#64748b',
    ];

    const traces: any[] = [];
    const groupNames = Array.from(groups.keys()).sort();
    groupNames.forEach((name, i) => {
      const g = groups.get(name)!;
      traces.push({
        x: g.map(p => p.x),
        y: g.map(p => p.y),
        z: g.map(p => p.z),
        mode: 'markers',
        type: 'scatter3d',
        name,
        marker: {
          size: g.map(p => Math.max(4, Math.min(p.tokens / 50, 14))),
          color: palette[i % palette.length],
          opacity: 0.8,
          line: { width: 0 },
        },
        text: g.map(p =>
          `<b>${p.titulo}</b><br>Chunk #${p.chunk_index} · ${p.tokens} tokens<br><i>${p.preview}</i><br>${p.distrito || ''} · ${p.seccion_fuente || ''}`
        ),
        hoverinfo: 'text',
      });
    });

    const layout: any = {
      title: `Espacio Vectorial 3D — ${this.vectorTotal()} chunks · Coloreado por ${colorBy}`,
      scene: {
        xaxis: { title: '', showticklabels: false, showgrid: true, zeroline: false },
        yaxis: { title: '', showticklabels: false, showgrid: true, zeroline: false },
        zaxis: { title: '', showticklabels: false, showgrid: true, zeroline: false },
        bgcolor: '#f8fafc',
      },
      paper_bgcolor: '#fff',
      margin: { l: 0, r: 0, t: 40, b: 0 },
      height: 600,
      showlegend: true,
      legend: { x: 0, y: 1, font: { size: 11 } },
    };

    if (!(window as any).Plotly) return;

    (window as any).Plotly.newPlot('plot3d', traces, layout, { responsive: true });
  }

  loadDailySummaries() {
    this.http.get<{ items: ScrapingSummary[] }>(`${this.apiUrl}/scraping/logs/daily`)
      .subscribe(data => this.dailySummaries.set(data.items));
  }

  loadLiveLogs() {
    this.http.get<{ items: LiveLog[] }>(`${this.apiUrl}/scraping/logs/live?limit=100`)
      .subscribe(data => this.liveLogs.set(data.items));
  }

  loadScraperStatus() {
    this.http.get<ScraperStatus>(`${this.apiUrl}/scraping/status`)
      .subscribe(data => {
        this.scraperStatus.set(data);
        const wasRunning = this.scrapingRunning();
        this.scrapingRunning.set(data.running);
        if (data.running && !wasRunning) this.startPolling();
        if (!data.running && wasRunning) this.stopPolling();
      });
  }

  triggerDailyScrape() {
    const date = this.scrapingDate();
    this.http.post(`${this.apiUrl}/scraping/run?date=${date}&daily=true`, {})
      .subscribe(() => { this.startPolling(); });
  }

  triggerTodayScrape() {
    this.http.post(`${this.apiUrl}/scraping/run?today=true&daily=true`, {})
      .subscribe(() => { this.startPolling(); });
  }

  startPolling() {
    this.scrapingRunning.set(true);
    this.loadLiveLogs();
    this.loadScraperStatus();
    this.loadDailySummaries();

    this.pollingInterval = setInterval(() => {
      this.loadLiveLogs();
      this.loadScraperStatus();
      if (!this.scrapingRunning()) {
        this.loadDailySummaries();
      }
    }, 1500);

    setTimeout(() => {
      this.stopPolling();
      this.loadDailySummaries();
    }, 300000);
  }

  stopPolling() {
    if (this.pollingInterval) { clearInterval(this.pollingInterval); this.pollingInterval = null; }
    this.scrapingRunning.set(false);
    this.loadScraperStatus();
    this.loadLiveLogs();
    this.loadDailySummaries();
  }

  onTabChange(tab: Tab) {
    this.activeTab.set(tab);
    if (tab === 'scraping') {
      this.loadDailySummaries();
      this.loadLiveLogs();
      this.loadScraperStatus();
    }
    if (tab === 'vectores') this.loadVectores();
  }

  async loadGraph() {
    this.graphLoading.set(true);
    this.http.get<{ nodes: GraphNode[]; edges: GraphEdge[] }>(`${this.apiUrl}/vectores/graph?max_nodes=200&similarity=0.82`)
      .subscribe({
        next: (data) => {
          const connectedIds = new Set<number>();
          for (const e of data.edges) {
            connectedIds.add(e.source);
            connectedIds.add(e.target);
          }
          data.nodes = data.nodes.filter(n => connectedIds.has(n.id));
          this.graphNodes.set(data.nodes);
          this.graphEdges.set(data.edges);
          this.graphLoading.set(false);
          setTimeout(() => this.renderForceGraph(), 50);
        },
        error: () => this.graphLoading.set(false),
      });
  }

  async renderForceGraph() {
    const nodes = this.graphNodes();
    if (!nodes.length) return;

    const d3 = await import('d3');
    const el = document.getElementById('force-graph');
    if (!el) return;
    el.innerHTML = '';

    const width = el.clientWidth || 900;
    const height = 550;

    const catColors: Record<string, string> = {
      'Sociedad': '#3b82f6', 'Política': '#ef4444', 'Deportes': '#22c55e',
      'Espectáculos': '#f59e0b', 'Opinión': '#8b5cf6', 'Economía': '#06b6d4',
      'Mundo': '#ec4899', 'Ciencia': '#84cc16', 'Datos': '#6366f1',
      'Lima': '#f97316', 'Nacional': '#d946ef', 'Cultura': '#14b8a6',
      'Historia': '#e11d48',
    };

    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const links = this.graphEdges()
      .filter(e => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map(e => ({ source: e.source, target: e.target, similarity: e.similarity }));

    const svg = d3.select('#force-graph')
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .call(d3.zoom().scaleExtent([0.3, 4]).on('zoom', (event) => {
        g.attr('transform', event.transform);
      }) as any)
      .append('g');

    const g = svg.append('g');

    const color = (d: any) => catColors[d.categoria] || '#94a3b8';
    const radius = (d: any) => Math.max(4, Math.min(d.tokens / 50, 18));

    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links).id((d: any) => d.id).distance(60).strength(0.4))
      .force('charge', d3.forceManyBody().strength(-100))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((d: any) => radius(d) + 3));

    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#cbd5e1')
      .attr('stroke-width', d => Math.max(0.5, d.similarity * 3))
      .attr('stroke-opacity', 0.6);

    const node = g.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d: any) => radius(d))
      .attr('fill', (d: any) => color(d))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1)
      .attr('opacity', 0.85)
      .call(d3.drag()
        .on('start', (event: any, d: any) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event: any, d: any) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event: any, d: any) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        }) as any);

    const tooltip = d3.select('body').append('div')
      .attr('class', 'graph-tooltip')
      .style('position', 'absolute')
      .style('background', '#1a1a2e')
      .style('color', '#e2e8f0')
      .style('padding', '8px 12px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('font-family', 'Manrope, sans-serif')
      .style('max-width', '320px')
      .style('pointer-events', 'none')
      .style('opacity', '0')
      .style('z-index', '9999');

    node.on('mouseover', (event: any, d: any) => {
        tooltip.style('opacity', '1')
          .html(`<b>${d.titulo}</b><br><span style="color:#94a3b8">Chunk #${d.chunk_index} · ${d.tokens} tokens</span><br><i style="color:#cbd5e1">${d.preview}</i>`);
        d3.select(event.target).attr('stroke', '#333').attr('stroke-width', 2);
      })
      .on('mousemove', (event: any) => {
        tooltip.style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 30) + 'px');
      })
      .on('mouseout', (event: any) => {
        tooltip.style('opacity', '0');
        d3.select(event.target).attr('stroke', '#fff').attr('stroke-width', 1);
      });

    simulation.on('tick', () => {
      link.attr('x1', (d: any) => d.source.x).attr('y1', (d: any) => d.source.y)
          .attr('x2', (d: any) => d.target.x).attr('y2', (d: any) => d.target.y);
      node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);
    });
  }

  generateVectors() {
    this.vectorLoading.set(true);
    this.http.post(`${this.apiUrl}/vectores/generate`, {}).subscribe({
      next: (res: any) => {
        this.vectorLoading.set(false);
        if ((res as any).generated > 0) this.loadVectores();
      },
      error: () => this.vectorLoading.set(false),
    });
  }
}
