import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, map, of, tap } from 'rxjs';

export interface AuthUser { id: string; name: string; email: string }
interface AuthResponse { user: AuthUser; csrf_token: string }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  readonly user = signal<AuthUser | null>(null);
  readonly csrfToken = signal<string | null>(null);

  check(): Observable<boolean> {
    if (this.user()) return of(true);
    return this.http.get<AuthResponse>('/api/v1/auth/me').pipe(
      tap(response => this.accept(response)),
      map(() => true),
      catchError(() => { this.clear(); return of(false); }),
    );
  }

  login(email: string, password: string): Observable<AuthUser> {
    return this.http.post<AuthResponse>('/api/v1/auth/login', { email, password }).pipe(
      tap(response => this.accept(response)), map(response => response.user),
    );
  }

  register(name: string, email: string, password: string, invitationCode: string): Observable<AuthUser> {
    return this.http.post<AuthResponse>('/api/v1/auth/register',
      { name, email, password, invitation_code: invitationCode }).pipe(
      tap(response => this.accept(response)), map(response => response.user),
    );
  }

  logout(): void {
    this.http.post<void>('/api/v1/auth/logout', null, { headers: this.csrfHeaders() }).subscribe({
      next: () => { this.clear(); void this.router.navigateByUrl('/login'); },
      error: (error: HttpErrorResponse) => {
        if (error.status === 401) { this.clear(); void this.router.navigateByUrl('/login'); }
      },
    });
  }

  csrfHeaders(): HttpHeaders {
    const token = this.csrfToken();
    return token ? new HttpHeaders({ 'X-CSRF-Token': token }) : new HttpHeaders();
  }

  private accept(response: AuthResponse): void {
    this.user.set(response.user);
    this.csrfToken.set(response.csrf_token);
  }

  private clear(): void {
    this.user.set(null);
    this.csrfToken.set(null);
  }
}
