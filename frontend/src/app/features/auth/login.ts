import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  imports: [FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly showPassword = signal(false);
  protected readonly isLoading = signal(false);
  protected readonly errorMsg = signal('');

  protected handleSubmit(): void {
    if (!this.email().trim() || !this.password().trim()) return;
    this.isLoading.set(true);
    this.errorMsg.set('');

    this.auth.login(this.email(), this.password()).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/admin']);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMsg.set(err.error?.detail || 'Error al iniciar sesión');
      },
    });
  }

  protected togglePassword(): void {
    this.showPassword.update(v => !v);
  }
}
