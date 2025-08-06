const routeData = this.$router.resolve({ name: 'nomDeLaRoute', params: { id: 123 } });
window.open(routeData.href, '_blank');
