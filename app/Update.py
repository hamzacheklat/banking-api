public onRowSelected(event: any): void {
  const columnToDisable = event.node?.columnToDisable;
  const columnChecked = event.node?.columnChecked;

  if (columnToDisable) {
    this.handleCheckboxDisable(event, columnToDisable, columnChecked);
  }

  this.updateStartStopButtons(event);
}

/**
 * Gère l’activation/désactivation des cases à cocher selon la sélection.
 */
private handleCheckboxDisable(event: any, columnToDisable: string, columnChecked: string): void {
  const checked = event.api.getSelectedNodes().some(
    (el: any) => !el.data[columnChecked]
  );

  const column = this.columnApi.getColumn(columnToDisable);
  const def = column.getColDef();

  let params: any = def.cellRendererParams || {};

  if (def.cellRenderer === 'agGroupCellRenderer') {
    params.innerRendererParams = params.innerRendererParams || {};
    params.innerRendererParams.disableCheckbox = checked ? true : false;
  } else {
    params.disableCheckbox = checked ? true : false;
  }

  def.cellRendererParams = params;

  this.gridApi.refreshCells({
    force: true,
    columns: [columnToDisable]
  });
}

/**
 * Met à jour l’état des boutons Start / Stop selon le statut des lignes sélectionnées.
 */
private updateStartStopButtons(event: any): void {
  const status = event.node?.status;
  let isStart = true;
  let isStop = true;

  const selectedNodes = event.api.getSelectedNodes();

  if (status && selectedNodes.length > 0) {
    selectedNodes.forEach(node => {
      if (node.data[status] === 'RUNNING') {
        isStop = false;
      } else {
        isStart = false;
      }
    });
  } else {
    isStart = true;
    isStop = true;
  }

  this.startButtonIsDisabled = isStart;
  this.stopButtonIsDisabled = isStop;
}
