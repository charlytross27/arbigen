import { Routes } from '@angular/router';
import { ShellComponent } from './layout/shell.component';
import { authGuard } from './core/services/auth.guard';

const placeholder = () => import('./features/placeholder/placeholder.component').then(m => m.PlaceholderComponent);

export const routes: Routes = [
  { path: 'login', title: 'Iniciar sesión · Arbigen', loadComponent: () => import('./features/auth/auth.component').then(m => m.AuthComponent) },
  { path: 'register', title: 'Crear cuenta · Arbigen', loadComponent: () => import('./features/auth/auth.component').then(m => m.AuthComponent) },
  {
  path: '',
  component: ShellComponent,
  canActivate: [authGuard],
  canActivateChild: [authGuard],
  children: [
    { path: '', pathMatch: 'full', title: 'Inicio · Arbigen', loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent) },
    { path: 'explore', title: 'Explorar oportunidades · Arbigen', loadComponent: () => import('./features/explore/explore.component').then(m => m.ExploreComponent) },
    { path: 'analyses', title: 'Mis análisis · Arbigen', loadComponent: () => import('./features/analyses/analyses.component').then(m => m.AnalysesComponent) },
    { path: 'analysis/:id', title: 'Resultado del análisis · Arbigen', loadComponent: () => import('./features/analysis/analysis.component').then(m => m.AnalysisComponent) },
    { path: 'opportunity/saved/:id', title: 'Oportunidad guardada · Arbigen', loadComponent: () => import('./features/opportunity/saved-opportunity.component').then(m => m.SavedOpportunityComponent) },
    { path: 'studio', title: 'Estudio IA · Arbigen', loadComponent: () => import('./features/studio/studio.component').then(m => m.StudioComponent) },
    { path: 'catalogs', title: 'Mis catálogos · Arbigen', loadComponent: () => import('./features/catalogs/catalogs.component').then(m => m.CatalogsComponent) },
    { path: 'catalogs/:id', title: 'Detalle de catálogo · Arbigen', loadComponent: () => import('./features/catalogs/catalogs.component').then(m => m.CatalogsComponent) },
    { path: 'profile', title: 'Mi perfil · Arbigen', loadComponent: () => import('./features/profile/profile.component').then(m => m.ProfileComponent) },
    { path: '**', title: 'Página no encontrada · Arbigen', loadComponent: placeholder },
  ],
  },
];
