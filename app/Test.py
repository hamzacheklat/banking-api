<div class="status-cell" style="display: flex; align-items: center; gap: 8px;">
  <input
    type="checkbox"
    [checked]="isExtract ? params.data.extract_selected : params.data.replicat_selected"
    [disabled]="isExtract
      ? params.data.replicat_selected
      : params.data.extract_selected"
    (change)="onCheckboxChange($event)"
  />

  <span>{{ dataStatus }}</span>
</div>



import { Component } from '@angular/core';
import { ICellRendererAngularComp } from 'ag-grid-angular';

@Component({
  selector: 'app-status-renderer',
  templateUrl: './status-renderer.component.html',
})
export class StatusRendererComponent implements ICellRendererAngularComp {
  params: any;
  dataStatus: string = '';
  isExtract = false;

  agInit(params: any): void {
    this.params = params;
    this.isExtract = params.colDef.field === 'extract';
    this.dataStatus = params.data.status;
  }

  refresh(): boolean {
    return false;
  }

  onCheckboxChange(event: Event) {
    const checked = (event.target as HTMLInputElement).checked;

    if (this.isExtract) {
      this.params.data.extract_selected = checked;

      // 🔸 Si Extract est activé, on désactive Replicat
      if (checked) this.params.data.replicat_selected = false;
    } else {
      this.params.data.replicat_selected = checked;

      // 🔸 Si Replicat est activé, on désactive Extract
      if (checked) this.params.data.extract_selected = false;
    }

    // 🔁 Redessine la ligne pour mettre à jour les états "disabled"
    this.params.api.refreshCells({
      rowNodes: [this.params.node],
      force: true,
    });

    // (optionnel) Notifie le parent
    this.params.api.dispatchEvent({
      type: this.isExtract ? 'extractCheckboxChanged' : 'replicatCheckboxChanged',
      data: this.params.data,
      checked,
    });
  }
}
