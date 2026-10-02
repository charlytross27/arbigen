import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IconComponent } from '../../shared/icon.component';

@Component({
  selector: 'app-placeholder', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './placeholder.component.html', styleUrl: './placeholder.component.scss',
})
export class PlaceholderComponent {
}
