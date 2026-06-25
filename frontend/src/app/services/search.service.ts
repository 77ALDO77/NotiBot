import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class SearchService {
  readonly query = signal('');

  setQuery(q: string) {
    this.query.set(q.trim());
  }
}
