import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-login',
  imports: [FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly showPassword = signal(false);
  protected readonly isLoading = signal(false);

  protected handleSubmit(): void {
    if (!this.email().trim() || !this.password().trim()) return;
    this.isLoading.set(true);
    setTimeout(() => {
      this.isLoading.set(false);
    }, 1500);
  }

  protected togglePassword(): void {
    this.showPassword.update(v => !v);
  }
}
