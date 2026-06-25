import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { SearchService } from './services/search.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private searchService = inject(SearchService);

  /** Vuelve al tope de la página suavemente */
  scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /** Propaga el texto del buscador al servicio (con debounce simple) */
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;

  onSearch(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.searchService.setQuery(value);
    }, 350);
  }
}