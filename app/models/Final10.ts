this.http.get<any>('/api/token')
  .subscribe(res => {
    const data = res.data;

    // Le front POST vers l’IdP
    this.http.post<any>('https://idp/token', new HttpParams({fromObject: data}).toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }).subscribe(res2 => {
      this.auth.setToken(res2.access_token);
      this.router.navigate(['/chat']);
    });
  });
