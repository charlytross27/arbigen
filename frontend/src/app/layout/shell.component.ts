import { Component, DestroyRef, ElementRef, HostListener, ViewChild, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs';
import { IconComponent, IconName } from '../shared/icon.component';
import { AuthService } from '../core/services/auth.service';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-shell', standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, IconComponent],
  templateUrl: './shell.component.html', styleUrl: './shell.component.scss',
})
export class ShellComponent {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly auth = inject(AuthService);
  readonly isDevelopment = !environment.production;
  readonly menuOpen = signal(false);
  readonly currentSection = signal('Inicio');
  @ViewChild('menuToggle') private menuToggle?: ElementRef<HTMLButtonElement>;
  @ViewChild('primaryNavigation') private primaryNavigation?: ElementRef<HTMLElement>;
  @ViewChild('mainContent') private mainContent?: ElementRef<HTMLElement>;

  readonly navigation: readonly { label: string; route: string; icon: IconName; exact: boolean }[] = [
    { label: 'Inicio', route: '/', icon: 'home', exact: true },
    { label: 'Explorar oportunidades', route: '/explore', icon: 'search', exact: false },
    { label: 'Mis análisis', route: '/analyses', icon: 'chart', exact: false },
    { label: 'Estudio IA', route: '/studio', icon: 'sparkles', exact: false },
    { label: 'Mis catálogos', route: '/catalogs', icon: 'catalog', exact: false },
  ];

  constructor() {
    this.updateSection(this.router.url);
    this.router.events.pipe(filter(event => event instanceof NavigationEnd), takeUntilDestroyed(this.destroyRef)).subscribe(event => {
      this.menuOpen.set(false);
      this.updateSection(event.urlAfterRedirects);
      this.mainContent?.nativeElement.focus({ preventScroll: true });
    });
  }

  toggleMenu(): void {
    if (this.menuOpen()) {
      this.closeMenu();
      return;
    }
    this.menuOpen.set(true);
    requestAnimationFrame(() => {
      if (this.menuOpen()) this.primaryNavigation?.nativeElement.querySelector('a')?.focus();
    });
  }

  @HostListener('document:keydown.escape')
  closeMenu(): void {
    if (this.menuOpen()) {
      this.menuOpen.set(false);
      this.menuToggle?.nativeElement.focus();
    }
  }

  private updateSection(url: string): void {
    const path = url.split('?')[0];
    const nav = this.navigation.find(item => item.route === path);
    this.currentSection.set(nav?.label ?? (path.startsWith('/analysis/') ? 'Resultado del análisis' : path.startsWith('/opportunity/saved/') ? 'Rentabilidad' : path.startsWith('/opportunity/') ? 'Detalle de oportunidad' : path.startsWith('/catalogs/') ? 'Detalle de catálogo' : path === '/profile' ? 'Mi perfil' : 'Página no encontrada'));
  }
}
