export class StatusRendererComponent implements ICellRendererAngularComp {
  params: any;
  isExtract = false;      // true si cette colonne est la colonne "extract"
  isDisabled = false;

  agInit(params: any): void {
    this.params = params;
    // Détecte si on est sur la colonne extract (ou utilise params.colDef.field)
    this.isExtract = params.colDef && params.colDef.field === 'extract_selected';
    this.checkBoxDisabled(); // initialisation
  }

  // Calcul propre de l'état disabled (n'écrase pas plusieurs fois)
  checkBoxDisabled(): void {
    // cas regroupé (noeud parent)
    if (this.params.node && this.params.node.allLeafChildrenCount != null) {
      if (this.isExtract) {
        // si n'importe quel enfant a replicat_selected => disable la colonne extract ici
        this.isDisabled = this.params.node.allLeafChildren.some((el: any) => !!el.data.replicat_selected);
      } else {
        this.isDisabled = this.params.node.allLeafChildren.some((el: any) => !!el.data.extract_selected);
      }
    } else {
      // ligne simple : disable si l'autre champ de cette même ligne est coché
      this.isDisabled = this.isExtract
        ? !!this.params.data.replicat_selected
        : !!this.params.data.extract_selected;
    }
  }

  onCheckboxChange(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;

    // met à jour les données (sur les enfants si group)
    if (this.params.node && this.params.node.allLeafChildrenCount != null) {
      this.params.node.allLeafChildren.forEach((el: any) => {
        el.data[this.params.colDef.field] = checked;
      });
    } else {
      this.params.data[this.params.colDef.field] = checked;
    }

    // Recalcule l'état disabled pour CE renderer
    this.checkBoxDisabled();

    // Rafraichit les cellules concernées (ligne/group) pour que les autres cases prennent en compte la nouvelle valeur
    // -> refresh de la ligne (cible) (plus simple et sûr)
    if (this.params.api && this.params.node) {
      this.params.api.refreshCells({ rowNodes: [this.params.node] });
    }
  }

  // ag-Grid lifecycle
  refresh(params: any): boolean { return false; }
}
