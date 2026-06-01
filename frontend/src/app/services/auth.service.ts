import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs';

export interface User {
  id: number;
  nombre_usuario: string;
  correo: string;
  rol: string;
  estado: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiUrl = '/api/auth';
  private readonly tokenKey = 'notibot_token';
  private readonly userKey = 'notibot_user';

  currentUser = signal<User | null>(this.getStoredUser());
  isAdmin = signal(this.currentUser()?.rol === 'admin');

  constructor(private http: HttpClient, private router: Router) {}

  login(correo: string, password: string) {
    return this.http
      .post<LoginResponse>(`${this.apiUrl}/login`, { correo, password })
      .pipe(
        tap((res) => {
          localStorage.setItem(this.tokenKey, res.access_token);
          localStorage.setItem(this.userKey, JSON.stringify(res.user));
          this.currentUser.set(res.user);
          this.isAdmin.set(res.user.rol === 'admin');
        }),
      );
  }

  logout() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    this.currentUser.set(null);
    this.isAdmin.set(false);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  private getStoredUser(): User | null {
    const raw = localStorage.getItem(this.userKey);
    return raw ? JSON.parse(raw) : null;
  }
}
