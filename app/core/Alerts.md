Voici comment **configurer l’envoi d’emails SMTP dans Grafana sur Kubernetes**, selon les 2 cas les plus courants :

1. Grafana installé avec **Helm**
2. Grafana avec un **ConfigMap manuel**

---

# 1) Configuration SMTP avec Helm (méthode recommandée)

Si tu as installé Grafana via le chart officiel :

```bash
helm install grafana grafana/grafana
```

Tu dois modifier le fichier `values.yaml`.

---

## Exemple de configuration SMTP

Dans `values.yaml` :

```yaml
grafana:
  grafana.ini:
    smtp:
      enabled: true
      host: smtp.yourprovider.com:587
      user: alerts@yourcompany.com
      password: "yourpassword"
      from_address: alerts@yourcompany.com
      from_name: Grafana
      skip_verify: true
      startTLS_policy: OpportunisticStartTLS
```

---

## Exemple complet avec Gmail

```yaml
grafana:
  grafana.ini:
    smtp:
      enabled: true
      host: smtp.gmail.com:587
      user: your@gmail.com
      password: your_app_password
      from_address: your@gmail.com
      from_name: Grafana Alerts
      skip_verify: true
```

⚠️ Avec Gmail, il faut un **App Password**, pas ton mot de passe normal.

---

## Appliquer la configuration

```bash
helm upgrade grafana grafana/grafana -f values.yaml
```

---

# 2) Configuration avec ConfigMap (déploiement manuel)

Si Grafana est déployé sans Helm, tu dois modifier le `grafana.ini`.

---

## Exemple de ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
data:
  grafana.ini: |
    [smtp]
    enabled = true
    host = smtp.yourprovider.com:587
    user = alerts@yourcompany.com
    password = yourpassword
    from_address = alerts@yourcompany.com
    from_name = Grafana
    skip_verify = true
```

---

## Monter la config dans le pod

Dans ton Deployment Grafana :

```yaml
volumeMounts:
  - name: grafana-config
    mountPath: /etc/grafana/grafana.ini
    subPath: grafana.ini

volumes:
  - name: grafana-config
    configMap:
      name: grafana-config
```

Puis redémarrer :

```bash
kubectl rollout restart deployment grafana
```

---

# 3) Créer le contact point email dans Grafana

Dans l’interface Grafana :

1. Alerting
2. Contact points
3. New contact point
4. Type : **Email**
5. Ajouter l’adresse email
6. Test

---

# 4) Vérifier que le SMTP fonctionne

Dans les logs Grafana :

```bash
kubectl logs deployment/grafana
```

Tu dois voir :

```
SMTP enabled
```

Et lors d’un test :

```
Sending alert notification
```

---

# 5) Bonne pratique (secret Kubernetes)

Ne mets jamais le mot de passe SMTP en clair.

## Secret :

```bash
kubectl create secret generic grafana-smtp \
  --from-literal=password='yourpassword'
```

Puis dans `values.yaml` :

```yaml
grafana:
  extraEnv:
    - name: GF_SMTP_PASSWORD
      valueFrom:
        secretKeyRef:
          name: grafana-smtp
          key: password

  grafana.ini:
    smtp:
      enabled: true
      host: smtp.yourprovider.com:587
      user: alerts@yourcompany.com
      password: $__env{GF_SMTP_PASSWORD}
      from_address: alerts@yourcompany.com
```

---

Si tu veux, je peux :

* te donner un **values.yaml complet prêt pour prod**
* configurer **Grafana + Prometheus + Alertmanager** dans un seul Helm
* t’aider à brancher **Slack, Teams ou PagerDuty** pour les alertes.

