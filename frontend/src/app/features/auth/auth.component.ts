import { Component, DestroyRef, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AuthService } from '../../core/services/auth.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-auth', standalone: true,
  imports: [RouterLink],
  templateUrl: './auth.component.html', styleUrl: './auth.component.scss',
})
export class AuthComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  readonly registering = this.route.snapshot.routeConfig?.path === 'register';
  readonly isDevelopment = !environment.production;
  readonly busy = signal(false);
  readonly error = signal<string | null>(null);

  submit(event: Event): void {
    event.preventDefault();
    if (this.busy()) return;
    const form = event.currentTarget as HTMLFormElement;
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const email = String(data.get('email') ?? '').trim();
    const password = String(data.get('password') ?? '');
    const action = this.registering
      ? this.auth.register(String(data.get('name') ?? '').trim(), email, password, String(data.get('invitation_code') ?? '').trim())
      : this.auth.login(email, password);
    this.busy.set(true);
    this.error.set(null);
    action.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        const next = this.route.snapshot.queryParamMap.get('next');
        void this.router.navigateByUrl(next?.startsWith('/') && !next.startsWith('//') ? next : '/');
      },
      error: (error: HttpErrorResponse) => {
        this.busy.set(false);
        this.error.set(error.error?.error?.message ?? 'No se pudo completar la solicitud. Inténtalo de nuevo.');
      },
    });
  }
}
